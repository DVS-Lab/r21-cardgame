#!/usr/bin/env python3
"""Export Figure S5's signed C4 target voxels and descriptive four-condition bars.

Read the completed Linux1 FEAT fits. No fitting or public participant-level export.
Use --publish to send the single aggregate to the analysis repository.
"""
import argparse
import json
import math
from pathlib import Path
import re
import statistics
import subprocess
import sys

import reproduce_jneurosci_cortical as reproduction
import reproduce_jneurosci_cortical_inputs as lower

hist, pub, require = reproduction.hist, reproduction.pub, reproduction.require
EVIDENCE = "0514dd14bff56e33369a12603225dc99b153ea25"
SEED = "interactionC4"
CELLS = (
    (11, "reward", "VLPFC"),
    (12, "reward", "TPJ"),
    (13, "punishment", "VLPFC"),
    (14, "punishment", "TPJ"),
)
WEIGHTS = {16: (1, -1, 1, -1), 19: (1, -1, -1, 1)}
NAMES = {
    11: "ppi R_vlpfc",
    12: "ppi R_tpj",
    13: "ppi P_vlpfc",
    14: "ppi P_tpj",
    16: "ppi vlpfc>tpj",
    19: "ppi interaction",
}


def get_values(path, positions):
    image = pub.nifti(path)
    require(
        image and image[1:] == (lower.SHAPE, pub.GRID), "Missing or invalid study-space image: " + str(path)
    )
    return [image[0][p] for p in positions]


def find_group(project, work, model, template, vs):
    cope = model["cope"]
    signed = next(s for s in model["signed_results"] if s["direction"] == "negative")
    (cluster,) = signed["clusters"]
    pattern = "%s-cope%d-*/attempt-*/%s/%s.gfeat" % (
        SEED,
        cope,
        hist.TARGET,
        reproduction.name_for(SEED, cope),
    )
    matches = []
    for group in sorted((work / "groups").glob(pattern)):
        stat = group / "cope1.feat/thresh_zstat2.nii.gz"
        if pub.map_digest(stat, submitted_grid=True) == signed["thresholded_map_sha256"]:
            checked = reproduction.group_summary(group, SEED, cope, template, "reproduced", vs)
            require(
                checked["signed_results"] == model["signed_results"],
                "Group differs from the published result",
            )
            matches.append(group)
    require(matches, "Missing finished C4 group fit for published COPE %d" % cope)
    paths = [[Path(p) for _, p in pub._inputs(hist.fsf(g / "design.fsf"))] for g in matches]
    if len(matches) > 1:
        # Across retried groups, frozen directories can differ while their scientific inputs agree.
        fingerprints = {
            tuple((hist.digest(p), hist.digest(p.parent / "varcope1.nii.gz")) for p in ps) for ps in paths
        }
        require(len(fingerprints) == 1, "Different participant data in matching C4 group fits")
    group = matches[0]
    level = group / "cope1.feat"
    values = pub.nifti(level / "thresh_zstat2.nii.gz")[0]
    ids = [i for i, value in enumerate(values) if value > 0]
    require(len(ids) == cluster["voxels"] == signed["surviving_voxels"], "Unexpected cluster membership")
    nx, ny, _ = lower.SHAPE
    target = {k: cluster[k] for k in ("voxels", "peak_MNI_mm", "peak_Z_magnitude", "cluster_corrected_p")}
    target.update(
        cope=cope,
        thresholded_map_sha256=signed["thresholded_map_sha256"],
        voxels_ijk_signed_z=[[i % nx, (i // nx) % ny, i // (nx * ny), -values[i]] for i in ids],
    )
    return target, ids, paths[0]


def participant_runs(work, sub, runs, group_inputs):
    # L3 consumes frozen copies. Connect each one back to the original L2 job
    # via its byte-identical COPE/VARCOPE, then follow that job's actual L1 list.
    paths = []
    pattern = "%s/%s-*/attempt-*/%s" % (sub, SEED, lower.l2_name(SEED))
    for g in (work / "local_inputs/participant_jobs").glob(pattern):
        if all(
            (g / ("cope%d.feat/stats" % c) / f).is_file()
            and hist.digest(g / ("cope%d.feat/stats" % c) / f) == hist.digest(frozen.parent / f)
            for c, frozen in group_inputs.items()
            for f in ("cope1.nii.gz", "varcope1.nii.gz")
        ):
            paths.append(g)
    require(paths, "Missing L2 job supplying both published group contrasts for " + sub)
    sources = {
        tuple((int(i), Path(p).resolve()) for i, p in pub._inputs(hist.fsf(g / "design.fsf"))) for g in paths
    }
    require(len(sources) == 1, "Different run inputs in matching L2 jobs for " + sub)
    group = paths[0]
    fsf = hist.fsf(group / "design.fsf")
    require(
        hist.configs(fsf).get("mixed_yn") == "3"
        and reproduction.matrix_at(group / "design.mat", [[1]] * len(runs))
        and reproduction.matrix_at(group / "design.con", [[1]]),
        "L2 does not match fixed-effects run pooling for " + sub,
    )
    sources = [(int(index), Path(path)) for index, path in pub._inputs(fsf)]
    require(len(sources) == len(runs), "Unexpected number of run inputs for " + sub)
    for i, ((index, path), run) in enumerate(zip(sources, sorted(runs)), 1):
        require(
            index == i and sub in path.parts and path.name == lower.l1_name(SEED, run),
            "Run, participant, or cortical seed differs from the original roster: " + str(path),
        )
    return [path for _, path in sources]


def check_contrasts(run):
    text = (run / "design.con").read_text()
    names = {int(i): name.strip() for i, name in re.findall(r"^/ContrastName(\d+)[ \t]+([^\n]+)", text, re.M)}
    rows = [[float(v) for v in line.split()] for line in text.split("/Matrix", 1)[1].strip().splitlines()]
    for c, name in NAMES.items():
        require(
            names.get(c) == name and len(rows) >= c and len(rows[c - 1]) >= 9,
            "Unexpected C4 L1 contrast: " + str(run),
        )
        expected = [0.0] * len(rows[c - 1])
        expected[5:9] = WEIGHTS[c] if c in WEIGHTS else [int(k == c) for k in range(11, 15)]
        require(rows[c - 1] == expected, "Unexpected C4 L1 contrast weights: " + str(run))


def fixed_effects(runs, positions):
    """Match the intercept-only FEAT fixed effect at each voxel before spatial averaging."""
    effects, precisions = {}, {}
    for run in runs:
        check_contrasts(run)
        reg = run / "reg_standard"
        # The reproduction used an identity transform on MNI-grid inputs. Prefer the
        # images that FEAT passed to L2; if removed, the native study-grid images are
        # also eligible. Both paths are checked against published L2 COPEs below.
        matrix = (run / "reg/example_func2standard.mat").read_text()
        require(
            [[float(v) for v in l.split()] for l in matrix.splitlines() if l.strip()]
            == [[float(i == j) for j in range(4)] for i in range(4)],
            "Nonidentity L1 registration: " + str(run),
        )
        mask = reg / "mask.nii.gz" if (reg / "mask.nii.gz").is_file() else run / "mask.nii.gz"
        coverage = get_values(mask, positions)
        values = {}
        for c in NAMES:
            files = ["%s%d.nii.gz" % (kind, c) for kind in ("cope", "varcope")]
            base = reg if all((reg / "stats" / f).is_file() for f in files) else run
            y, var = [get_values(base / "stats" / f, positions) for f in files]
            values[c] = y
            weights = [1 / v if v > 0 and m > 0 else 0.0 for v, m in zip(var, coverage)]
            effects.setdefault(c, []).append([a * w for a, w in zip(y, weights)])
            precisions.setdefault(c, []).append(weights)
        # Condition COPEs must reconstruct each measured primary contrast in each run.
        for c, signs in WEIGHTS.items():
            for y, *cell in zip(values[c], *(values[k] for k in range(11, 15))):
                predicted = sum(w * v for w, v in zip(signs, cell))
                require(
                    abs(y - predicted) <= 1e-4 + 2e-5 * sum(map(abs, cell)),
                    "Four run conditions do not reconstruct COPE %d in %s" % (c, run),
                )
    # FLAME excludes a voxel if any input VARCOPE is nonpositive. Preserve missingness
    # for ROI extraction while verifying FEAT's zero-valued output for excluded voxels.
    return {
        c: [sum(e) / sum(w) if all(w) else None for e, w in zip(zip(*effects[c]), zip(*precisions[c]))]
        for c in NAMES
    }


def export(project):
    report = json.loads(
        subprocess.check_output(["git", "-C", str(project), "show", EVIDENCE + ":" + reproduction.RESULT])
    )
    cohort = hist.roster(project)
    hist.check_seed(project, SEED)
    template = hist.template(project)
    roster = reproduction.expected_roster(template)
    require(
        roster == sorted(cohort)
        and len(roster) == report["n_participants"] == 28
        and sum(map(len, cohort.values())) == report["n_runs"] == 79,
        "Group roster differs from published cohort",
    )
    work = project / reproduction.SUBDIR
    vs = reproduction.vs_positions(project)
    targets, membership, frozen = {}, {}, {}
    for model in report["models"]:
        if model["seed"] == SEED and model["cope"] in WEIGHTS:
            c = model["cope"]
            targets[c], membership[c], frozen[c] = find_group(project, work, model, template, vs)
    require(set(targets) == set(WEIGHTS), "Missing a published C4 target")
    positions = sorted(set(membership[16]) | set(membership[19]))
    index = {p: i for i, p in enumerate(positions)}
    participants = []
    for i, sub in enumerate(roster):
        inputs = {c: frozen[c][i] for c in WEIGHTS}
        runs = participant_runs(work, sub, cohort[sub], inputs)
        result = fixed_effects(runs, positions)
        for c in WEIGHTS:
            observed = get_values(inputs[c], positions)
            variance = get_values(inputs[c].parent / "varcope1.nii.gz", positions)
            require(
                all(
                    (a is not None) == (v > 0)
                    and math.isclose(0.0 if a is None else a, b, rel_tol=2e-5, abs_tol=1e-4)
                    for a, b, v in zip(result[c], observed, variance)
                ),
                "Voxelwise pooling disagrees with the verified L2 COPE %d for %s" % (c, sub),
            )
        participants.append(result)
        print("Verified participant %d/%d" % (i + 1, len(roster)), flush=True)
    for c, target in targets.items():
        # All four bars use identical voxels and all 28 participants.
        support = [
            index[p]
            for p in membership[c]
            if all(result[k][index[p]] is not None for result in participants for k, _, _ in CELLS)
        ]
        require(
            support, "No common estimable voxels for all conditions and participants in COPE %d target" % c
        )
        target["condition_support_voxels"] = len(support)
        target["conditions"] = []
        for k, block, site in CELLS:
            participant_means = [statistics.mean(result[k][j] for j in support) for result in participants]
            target["conditions"].append(
                {
                    "cope": k,
                    "block": block,
                    "site": site,
                    "mean": statistics.mean(participant_means),
                    "sem": statistics.stdev(participant_means) / math.sqrt(len(roster)),
                }
            )
    affine = [list(pub.GRID[i : i + 4]) for i in range(0, 12, 4)] + [[0, 0, 0, 1]]
    return {
        "evidence_commit": EVIDENCE,
        "seed": SEED,
        "n_participants": len(roster),
        "n_runs": report["n_runs"],
        "grid": {"shape": list(lower.SHAPE), "affine": affine},
        "estimates": "Condition-specific gPPI COPEs. Inverse-variance fixed effects across runs at each voxel, "
        "then mean across target voxels within participant. Bars are participant means and SEM.",
        "targets": [targets[c] for c in WEIGHTS],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument("--publish", action="store_true", help="push the verified aggregate to main")
    args = parser.parse_args()
    project = args.project.resolve()
    result = export(project)
    # git_publish uses a separate index. Keep this output under the private work
    # root so the next fast-forward pull can materialize the new tracked file.
    path = project / reproduction.SUBDIR / Path(reproduction.FIGURE).name
    reproduction.write_json(path, result)
    print(path, flush=True)
    if args.publish:
        reproduction.git_publish(project, reproduction.FIGURE, result)


if __name__ == "__main__":
    try:
        main()
    except (OSError, ValueError, KeyError, hist.Prerequisite, subprocess.CalledProcessError) as error:
        sys.exit("Cortical figure export stopped: " + str(error))
