#!/usr/bin/env python3
"""Recover, or faithfully rerun, the four November 2021 prefrontal-seed group fits.

Run from the Linux1 analysis checkout. All new FEAT files, local provenance, and
logs are private. Only allowlisted group results or aggregate workflow status
are published. --check does not run FEAT or publish. --status reads local state.
"""
import argparse
import collections
import fcntl
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import tempfile
import time

import publish_jneurosci_revision as pub
import recover_jneurosci_revision as hist

LOWER_COUNTS = {
    "configured_groups",
    "cached_groups",
    "archived_participant_contrasts",
    "required_run_fits",
    "launchable_run_fits",
    "launchable_participant_fits",
    "required_participant_fits",
    "reused_run_models",
    "completed_run_fits",
    "completed_participant_fits",
    "completed_groups",
    "raw_runs_required",
    "preprocessed_bold_verified",
    "confounds_verified",
    "timing_runs_verified",
    "usable_bold_and_confounds",
    "missing_preprocessed_bold",
    "missing_confounds",
    "conflicting_source_runs",
    "different_preprocessing_version_found",
}
LOWER_REASONS = {
    "missing_original_bold",
    "missing_original_confounds",
    "preprocessed_version_unverified",
    "conflicting_inputs",
    "fsl_unavailable",
    "lower_fit_failed",
    "bold_grid_or_length_mismatch",
    "invalid_original_confounds",
    "source_design_unverified",
}
GROUPS = tuple((seed, cope) for seed in hist.SEEDS for cope in hist.COPES)
SUBDIR = "derivatives/jneurosci_cortical_reproduction"
RESULT = "derivatives/jneurosci_revision/cortical_reproduction.json"
PROGRESS = "derivatives/jneurosci_revision/cortical_reproduction_status.json"
FIGURE = "derivatives/jneurosci_revision/cortical_figure.json"
SOURCE_INVENTORY = "derivatives/jneurosci_revision/cortical_source_inventory.json"
LAUNCH = "logs/rerunL3_date-2021-11-22T2250.log"
LAUNCH_SHA = "629080f3f7ff11e75bc72f9bf7a394cec369cd915ed50c22b15c696f79a1a397"
VS = {
    "left": "5552fd891b198941581d50a33d503722dd573f468503f4652e6c9237c337c738",
    "right": pub.SEEDS["right VS"][2],
}
require = hist.require


def write_json(path, value):
    with tempfile.NamedTemporaryFile(mode="w", dir=str(path.parent), delete=False) as f:
        json.dump(value, f, indent=2, sort_keys=True, allow_nan=False)
        f.write("\n")
    os.replace(f.name, str(path))


def archive_roots(project, extras):
    """Probe named projects, exact FEAT directories, and representative mounted snapshots only."""
    projects = [project]
    for base in [project.parent, Path("/data/projects"), Path("/ZPOOL/data/projects")]:
        projects += [base / "r21-cardgame", base / "ds.tacsCardGame", base / "ds.tacsCardGame/bids"]
    projects.append(Path.home() / "work/r21-cardgame")
    roots = list(extras)
    for p in projects:
        d = p / "derivatives"
        if not d.is_dir():
            continue
        if (d / "fmriprep").is_dir():
            roots.append(d / "fsl")
        roots.extend(sorted(d.glob("fsl*")))
        for base in [d / "fsl", d, p, p.parent, p.parent.parent]:
            snapshots = base / ".zfs/snapshot"
            if not snapshots.is_dir():
                continue
            # The 2021 snapshots cover the original fit period. Also check the
            # oldest and newest retained snapshots for pre-cleanup derivatives.
            try:
                entries = sorted(v for v in snapshots.iterdir() if v.is_dir())
            except PermissionError:
                print("Snapshot names unavailable at " + str(snapshots), flush=True)
                continue
            chosen = [v for v in entries if re.search(r"2021[-_]?(?:11|12)", v.name)]
            for v in entries[:1] + chosen + entries[-1:]:
                roots.append(v / (d / "fsl").relative_to(base))
    unique = {}
    for r in roots:
        actual = r if r.is_dir() else r.parent / "fmriprep"
        if actual.is_dir():
            st = actual.stat()
            unique.setdefault((st.st_dev, st.st_ino), r.resolve())
    require((project / "derivatives/fsl").is_dir(), "Missing derivatives/fsl in this checkout")
    return list(unique.values())


def name_for(seed, cope):
    return "L3_task-cardgame_type-ppi_seed-%s_cnum-%02d_cname-%s_onegroup" % (seed, cope, hist.COPES[cope])


def original_groups(roots, seed, cope):
    seen = set()
    for root in roots:
        for base in [root, root / "archive", root / "backup", root / "__older", root / "old"]:
            for parent in sorted(base.glob(hist.TARGET + "*")):
                if not parent.is_dir():
                    continue
                for g in sorted(parent.glob("*onegroup*.gfeat*")):
                    s = g.name.lower()
                    if not (seed.lower() in s or "vlpfc" in s):
                        continue
                    if not re.search(r"(?:cnum|copenum|cope)[-_]?0*%d(?:[^0-9]|$)" % cope, s):
                        continue
                    if g.is_dir() and g.resolve() not in seen:
                        seen.add(g.resolve())
                        yield g


def settings_match(raw, template):
    actual, expected = hist.configs(raw), hist.configs(template)
    # FEAT may add runtime settings. The stored analysis settings, including
    # all weights, inference and variance groups, must still agree.
    for key, expect in expected.items():
        if key == "outputdir":
            continue
        got = actual.get(key)
        if key == "regstandard":
            if got is None or Path(got).name != Path(expect).name:
                return False
        elif got != expect:
            try:
                if float(got) == float(expect):
                    continue
            except (TypeError, ValueError):
                pass
            return False
    return True


def matrix_at(path, expected):
    try:
        lines = path.read_text().split("/Matrix", 1)[1].strip().splitlines()
        return [[float(v) for v in row.split()] for row in lines if row.strip()] == expected
    except (OSError, IndexError, ValueError):
        return False


def expected_roster(template):
    return [re.search(r"/(sub-[^/]+)/L2_", path).group(1) for _, path in pub._inputs(template)]


def ordered_sources(raw, seed, cope, roster):
    pattern = (
        r"/(sub-[^/]+)/L2_task-cardgame_model-01_type-ppi_seed-"
        + seed
        + r"_sm-6\+*\.gfeat\+*/cope0*"
        + str(cope)
        + r"\.feat/stats/cope1\.nii\.gz$"
    )
    matches = []
    for ix, path in pub._inputs(raw):
        m = re.search(pattern, path)
        if not m or int(ix) != len(matches) + 1:
            return False
        matches.append(m.group(1))
    return matches == roster


def vs_positions(project):
    positions = {}
    for side, digest in VS.items():
        img = pub.nifti(project / "masks" / ("seed-%sVS.nii.gz" % side))
        if img and img[1:] == ((65, 77, 65), pub.GRID):
            mask = bytes(v != 0 for v in img[0])
            if hashlib.sha256(mask).hexdigest() == digest:
                positions[side] = [i for i, v in enumerate(mask) if v]
    return positions


def group_summary(g, seed, cope, template, source, vs):
    level = g / "cope1.feat"
    reports = [g / "report.html", level / "report.html"]
    require(all(pub.finished_report(p) for p in reports), "incomplete FEAT report")
    if source == "original":
        require(all(hist.dated_november_fit(p) for p in reports), "original group fit date unverified")
    fsf = g / "design.fsf"
    if not fsf.is_file():
        fsf = g.parent / ("L3_task-cardgame_type-ppi_seed-%s_copenum-%d_onegroup.fsf" % (seed, cope))
    raw = hist.fsf(fsf)
    require(
        settings_match(raw, template) and ordered_sources(raw, seed, cope, expected_roster(template)),
        "group model, input order, contrast, or seed provenance mismatch",
    )
    for location in [level, g]:
        require(
            matrix_at(location / "design.con", [[1], [-1]])
            and matrix_at(location / "design.mat", [[1]] * 28)
            and matrix_at(location / "design.grp", [[1]] * 28),
            "FEAT design matrices differ from original",
        )
    mask = pub.nifti(level / "mask.nii.gz")
    grid = ((65, 77, 65), pub.GRID)
    require(mask and mask[1:] == grid and any(mask[0]), "unverified group analysis mask")
    signs = []
    first_support = None
    for sign in (1, 2):
        threshold = level / ("thresh_zstat%d.nii.gz" % sign)
        labels = level / ("cluster_mask_zstat%d.nii.gz" % sign)
        require(
            hist.grid_agrees(threshold) and hist.grid_agrees(labels), "signed products have wrong MNI grid"
        )
        checked = pub.sign_info(level, sign, True, None)
        require(
            checked["status"] in hist.PUBLISHABLE and checked["cluster_labels_readable"],
            "incomplete or inconsistent signed maps and FSL cluster statistics",
        )
        zi, li = pub.nifti(threshold), pub.nifti(labels)
        require(
            zi and li and all(not z or m for z, m in zip(zi[0], mask[0])),
            "thresholded result extends beyond the group analysis mask",
        )
        support = bytearray(z > 0 for z in zi[0])
        require(all(z == 0 or z >= 3.095 for z in zi[0]), "thresholded map contains sub-threshold voxels")
        if first_support is None:
            first_support = support
        else:
            require(
                not any(a and b for a, b in zip(first_support, support)), "opposing signed maps overlap"
            )
        raw_z = level / "stats" / ("zstat%d.nii.gz" % sign)
        if raw_z.is_file():
            unthresholded = pub.nifti(raw_z)
            require(
                unthresholded
                and unthresholded[1:] == grid
                and any(unthresholded[0])
                and all(not z or abs(z - u) < 1e-3 for z, u in zip(zi[0], unthresholded[0])),
                "signed thresholded map conflicts with its unthresholded statistic",
            )
        # Preserve the FSL corrected p and extent. Derive MNI peak coordinates
        # from the signed cluster image when the FSL table reported only voxels.
        by_label = {r["cluster_index"]: r for r in pub.map_clusters(zi, li)}
        clusters = checked["clusters"] or []
        for c in clusters:
            reference = by_label[c["cluster_index"]]
            if "peak_MNI_mm" in c:
                xyz = c["peak_MNI_mm"]
                offsets = [pub.GRID[i] for i in (3, 7, 11)]
                ijk = [round((v - o) / 3) for v, o in zip(xyz, offsets)]
                require(
                    all(
                        0 <= vi < n and abs(x - (3 * vi + o)) <= 0.51
                        for vi, n, x, o in zip(ijk, zi[1], xyz, offsets)
                    ),
                    "reported MNI peak is outside the verified voxel grid",
                )
                pos = ijk[0] + zi[1][0] * (ijk[1] + zi[1][1] * ijk[2])
                require(
                    li[0][pos] == c["cluster_index"]
                    and abs(zi[0][pos] - reference["peak_Z_magnitude"]) <= 0.001,
                    "reported cluster peak location disagrees with the signed image",
                )
            else:
                c["peak_MNI_mm"] = reference["peak_MNI_mm"]
        overlap = {}
        for side in VS:
            if side in vs:
                ids = collections.Counter(int(li[0][i]) for i in vs[side] if li[0][i] > 0)
                overlap[side] = {
                    "reference_voxels": len(vs[side]),
                    "overlapping_voxels": sum(ids.values()),
                    "overlap_by_cluster": dict(sorted(ids.items())),
                }
            else:
                overlap[side] = {"status": "submitted_reference_mask_unavailable"}
        signs.append(
            {
                "direction": checked["direction"],
                "status": checked["status"],
                "surviving_voxels": checked["nonzero_voxels"],
                "clusters": clusters,
                "thresholded_map_sha256": pub.map_digest(threshold, submitted_grid=True),
                "submitted_block_VS_mask_overlap": overlap,
            }
        )
    return {
        "seed": seed,
        "seed_voxels": 35 if seed == "interactionC4" else 41,
        "cope": cope,
        "contrast": hist.COPES[cope],
        "source": source,
        "signed_results": signs,
    }


def recover_groups(roots, template, vs):
    recovered, blocked = {}, {}
    for key in GROUPS:
        candidates = {}
        for g in original_groups(roots, *key):
            try:
                summary = group_summary(g, *key, template, "original", vs)
            except hist.Prerequisite as exc:
                print("Excluded original candidate %s (%s)" % (g, exc), flush=True)
                continue
            fingerprint = json.dumps(summary["signed_results"], sort_keys=True)
            candidates[fingerprint] = summary
            print("Verified original %s" % g, flush=True)
        if len(candidates) == 1:
            recovered[key] = next(iter(candidates.values()))
        elif len(candidates) > 1:
            blocked[key] = "conflicting_verified_originals"
    return recovered, blocked


def frozen_sources(paths, seed, cope, template):
    roster = expected_roster(template)
    require(len(paths) == len(roster) == 28, "incomplete participant inputs")
    records = {}
    for sub, item in zip(roster, paths):
        p = Path(item)
        expected = (
            sub,
            "L2_task-cardgame_model-01_type-ppi_seed-%s_sm-6.gfeat" % seed,
            "cope%d.feat" % cope,
            "stats",
            "cope1.nii.gz",
        )
        require(p.is_absolute() and p.parts[-5:] == expected, "unexpected participant input or order")
        src = p.parent.parent
        files = hist.source_files(src)
        required = {
            "stats/cope1.nii.gz",
            "stats/varcope1.nii.gz",
            "stats/tdof_t1.nii.gz",
            "design.lev",
            "design.con",
            "mask.nii.gz",
        }
        require(
            required <= set(files)
            and any(k in files for k in ("bg_image.nii.gz", "example_func.nii.gz", "standard.nii.gz")),
            "missing fixed-effects input files",
        )
        require(
            all(hist.grid_agrees(src / k) for k in files if k.endswith(".nii.gz")),
            "fixed-effects input grid mismatch",
        )
        records[sub] = (src, [(k, hist.digest(src / k)) for k in files])
    return records


def stage_sources(records, dest):
    if (dest / "inputs").is_dir():
        for sub, (src, checksums) in records.items():
            private = dest / "inputs/derivatives/fsl" / sub / src.parent.name / src.name
            require(
                all((private / k).is_file() and hist.digest(private / k) == sha for k, sha in checksums),
                "private FEAT input changed",
            )
        return
    with tempfile.TemporaryDirectory(dir=str(dest)) as tmp:
        hist.copy_inputs({sub: v[0] for sub, v in records.items()}, Path(tmp))
        (Path(tmp) / "inputs").rename(dest / "inputs")


def fit_group(project, work, seed, cope, paths, base, feat, version, vs):
    inputs = frozen_sources(paths, seed, cope, base)
    sums = [[sub, v[1]] for sub, v in inputs.items()]
    signature = hashlib.sha256(
        json.dumps([hist.TEMPLATE_SHA, seed, cope, version, sums]).encode()
    ).hexdigest()
    dest = work / "groups" / ("%s-cope%d-%s" % (seed, cope, signature[:16]))
    dest.mkdir(parents=True, exist_ok=True)
    stage_sources(inputs, dest)
    attempts = sorted(dest.glob("attempt-[0-9][0-9][0-9]"))
    if not attempts or (attempts[-1] / "failed.json").is_file():
        attempt = dest / ("attempt-%03d" % (len(attempts) + 1))
        attempt.mkdir()
    else:
        attempt = attempts[-1]
    output = attempt / hist.TARGET / name_for(seed, cope)
    output.parent.mkdir(exist_ok=True)
    g = Path(str(output) + ".gfeat")
    design = attempt / "design.fsf"
    text = (
        base.replace("OUTPUT", str(output))
        .replace("COPENUM", str(cope))
        .replace("REPLACEME", "type-ppi_seed-" + seed)
        .replace("BASEDIR", str(dest / "inputs"))
    )
    # FEAT's standard background is identified by file and installation. If the
    # historical installation moved, resolve the same image under the active FSLDIR.
    native = hist.configs(base)["regstandard"]
    if not Path(native + ".nii.gz").is_file():
        path = Path(os.environ["FSLDIR"]) / "data/standard" / Path(native).name
        require(Path(str(path) + ".nii.gz").is_file(), "historical FSL standard background unavailable")
        text = text.replace('"' + native + '"', '"' + str(path) + '"')
    if not design.is_file():
        design.write_text(text)
    require(design.read_text() == text, "a prior private group design differs")
    started = attempt / "started.json"
    if not started.exists():
        require(not g.exists(), "prior unregistered group output at " + str(g))
        print("Launching %s COPE %d with FEAT; log %s" % (seed, cope, attempt / "feat.log"), flush=True)
        write_json(started, {"time": time.time(), "FSL_version": version})
        with (attempt / "feat.log").open("a") as log:
            proc = subprocess.run(
                [feat, str(design)], cwd=str(attempt), stdout=log, stderr=subprocess.STDOUT
            )
        if proc.returncode:
            write_json(attempt / "failed.json", {"FEAT_exit": proc.returncode})
            raise hist.Prerequisite("FEAT returned %d; see %s" % (proc.returncode, attempt / "feat.log"))
    # With a configured FSL queue, feat can return before post-stats. Rejoining
    # an active attempt never submits it twice. Keep every failed attempt.
    while True:
        if all(pub.finished_report(f / "report.html") for f in (g, g / "cope1.feat")):
            try:
                summary = group_summary(g, seed, cope, base, "reproduced", vs)
            except hist.Prerequisite as exc:
                write_json(attempt / "failed.json", {"error": str(exc)})
                raise
            summary["FSL_version"] = version
            return summary
        reports = [hist.fsf(f / "report.html") for f in (g, g / "cope1.feat")]
        if any(re.search(r"fatal error|errors? occurr?ed during the analysis", r, re.I) for r in reports):
            write_json(attempt / "failed.json", {"error": "FEAT report contains errors"})
            raise hist.Prerequisite("FEAT reported failure; see " + str(attempt))
        require(
            time.time() - started.stat().st_mtime < 72 * 3600,
            "Existing FEAT attempt timed out; inspect its queue and private log at " + str(attempt),
        )
        time.sleep(15)


def git_publish(project, path, data):
    """Use an isolated index; never stage working files or push the user's local HEAD."""
    labels = {RESULT: "results", PROGRESS: "status", SOURCE_INVENTORY: "source inventory", FIGURE: "figure data"}
    require(path in labels, "invalid aggregate export path")
    payload = json.dumps(data, indent=2, sort_keys=True, allow_nan=False) + "\n"

    def git(*args, **kwargs):
        return subprocess.run(
            ["git", "-C", str(project)] + list(args),
            check=True,
            universal_newlines=True,
            stdout=subprocess.PIPE,
            **kwargs,
        ).stdout.strip()

    with tempfile.TemporaryDirectory() as temp:
        env = dict(os.environ, GIT_INDEX_FILE=str(Path(temp) / "index"))
        for retry in range(3):
            git("fetch", "--no-tags", "origin", "refs/heads/main")
            parent = git("rev-parse", "FETCH_HEAD")
            git("read-tree", parent, env=env)
            blob = git("hash-object", "-w", "--stdin", input=payload)
            git("update-index", "--add", "--cacheinfo", "100644," + blob + "," + path, env=env)
            tree = git("write-tree", env=env)
            if tree == git("rev-parse", parent + "^{tree}"):
                return
            identity = subprocess.run(
                ["git", "-C", str(project), "var", "GIT_AUTHOR_IDENT"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            defaults = (
                []
                if identity.returncode == 0
                else [
                    "-c",
                    "user.name=CardGame results collector",
                    "-c",
                    "user.email=cardgame-collector@localhost",
                ]
            )
            commit = git(
                *defaults,
                "commit-tree",
                tree,
                "-p",
                parent,
                "-m",
                "Publish JNeurosci cortical connectivity " + labels[path],
            )
            try:
                git("push", "origin", commit + ":refs/heads/main")
                print("Published %s at %s" % (path, commit[:12]), flush=True)
                return
            except subprocess.CalledProcessError:
                if retry == 2:
                    raise


def run(project, work, args):
    import concurrent.futures
    from reproduce_jneurosci_cortical_inputs import prepare_inputs

    template = hist.template(project)
    runs = hist.roster(project)
    require(
        expected_roster(template) == sorted(runs), "historical group template and QC run ledger disagree"
    )
    launch = project / LAUNCH
    require(
        launch.is_file() and hist.digest(launch) == LAUNCH_SHA,
        "historical original group launch log unavailable",
    )
    original = hist.fsf(launch)
    for seed, cope in GROUPS:
        require(
            "/" + hist.TARGET + "/" + name_for(seed, cope) + "\n" in original,
            "group is absent from the original launch log",
        )
    for seed in hist.SEEDS:
        hist.check_seed(project, seed)
    roots = archive_roots(project, args.archive_fsl)
    print("Checking original named FEAT directories in %d distinct trees" % len(roots), flush=True)
    for root in roots:
        print("  " + str(root), flush=True)
    vs = vs_positions(project)
    results, blocked = recover_groups(roots, template, vs)
    needed = set(GROUPS) - set(results) - set(blocked)

    public_lower = {}

    def status(phase):
        data = {
            "phase": phase,
            "models": [
                {
                    "seed": seed,
                    "cope": cope,
                    "state": (
                        results[(seed, cope)]["source"]
                        if (seed, cope) in results
                        else blocked.get((seed, cope), "awaiting_verified_inputs")
                    ),
                }
                for seed, cope in GROUPS
            ],
        }
        if public_lower:
            data["lower_level"] = public_lower
        write_json(work / "status.json", data)
        return data

    status("checking_lower_inputs" if args.check else "resolving_lower_inputs")
    lower = {"seeds": {}}
    if needed:
        lower = prepare_inputs(
            project,
            work / "local_inputs",
            jobs=args.jobs,
            dry_run=args.check,
            needed=needed,
            source_roots=roots,
        )
        public_lower = {
            "counts": {
                k: v
                for k, v in lower.get("counts", {}).items()
                if k in LOWER_COUNTS and type(v) is int and 0 <= v <= 1000
            },
            "blocking_reasons": sorted(LOWER_REASONS.intersection(lower.get("blocking_reasons", []))),
            "FSL_verified": bool(lower.get("fsl_version")),
        }
        if lower.get("status") in {
            "ready",
            "preflight_ready",
            "missing_or_unverified_inputs",
            "execution_incomplete",
        }:
            public_lower["input_status"] = lower["status"]
        if not isinstance(lower.get("seeds"), dict):
            raise hist.Prerequisite("invalid lower-level inventory")
    if args.check:
        state = status("checked_only")
        print(json.dumps(state, indent=2), flush=True)
        print(
            "Lower-level readiness: %s. Private inventory in %s"
            % (lower.get("status", "all original groups recovered"), work / "local_inputs"),
            flush=True,
        )
        return 0 if not blocked and (not needed or lower.get("ready") is True) else 3
    pending = {}
    for seed, cope in sorted(needed):
        paths = lower["seeds"].get(seed, {}).get(str(cope))
        if paths:
            pending[(seed, cope)] = paths
        else:
            blocked[(seed, cope)] = "lower_inputs_or_fit_unavailable"
    if pending:
        feat, version = hist.fsl_runtime()
        status("group_FEAT")
        with concurrent.futures.ThreadPoolExecutor(max_workers=args.jobs) as executor:
            futures = {
                executor.submit(fit_group, project, work, *key, paths, template, feat, version, vs): key
                for key, paths in pending.items()
            }
            for future in concurrent.futures.as_completed(futures):
                key = futures[future]
                try:
                    result = future.result()
                    classes = lower.get("source_provenance", {}).get(key[0], {}).get(str(key[1]), [])
                    if len(classes) == 28 and all(v in {"archived", "reproduced"} for v in classes):
                        result["participant_inputs"] = {
                            k: classes.count(k) for k in ("archived", "reproduced")
                        }
                    results[key] = result
                except (hist.Prerequisite, OSError, ValueError, subprocess.CalledProcessError) as exc:
                    blocked[key] = "group_fit_or_verification_failed"
                    print("%s COPE %d: %s" % (*key, exc), file=sys.stderr, flush=True)
                status("group_FEAT")
    report = {
        "historical_design_commit": "33becdaa",
        "historical_group_template_sha256": hist.TEMPLATE_SHA,
        "n_participants": 28,
        "n_runs": 79,
        "analysis": "gPPI; one-sample FLAME 1+2",
        "whole_brain_cluster_forming_Z": 3.1,
        "cluster_corrected_alpha": 0.05,
        "models": [results[k] for k in GROUPS if k in results],
    }
    progress = status("complete" if len(results) == len(GROUPS) else "blocked")
    if results:
        write_json(work / "group-results.json", report)
    # A partial rerun cannot overwrite a previously complete export. A status
    # file can carry any verified subset plus allowlisted unresolved states.
    if len(results) == len(GROUPS):
        git_publish(project, RESULT, report)
    else:
        progress["verified_models"] = report["models"]
    git_publish(project, PROGRESS, progress)
    return 0 if len(results) == len(GROUPS) else 3


def activity(work):
    summary = {}
    for label, root, pattern, marker, failure in (
        ("run_FEAT", work / "local_inputs/run_jobs", "*/*", "submitted", "failed"),
        ("participant_FEAT", work / "local_inputs/participant_jobs", "*/*", "submitted", "failed"),
        ("group_FEAT", work / "groups", "*", "started.json", "failed.json"),
    ):
        counts = {"submitted": 0, "FEAT_reports_finished": 0, "failed": 0}
        for job in root.glob(pattern):
            attempts = sorted(job.glob("attempt-[0-9][0-9][0-9]"))
            if not attempts or not (attempts[-1] / marker).exists():
                continue
            current = attempts[-1]
            counts["submitted"] += 1
            if (current / failure).exists():
                counts["failed"] += 1
            elif any(
                pub.finished_report(p)
                for pattern in ("*.feat/report.html", "*.gfeat/report.html", "*/*.gfeat/report.html")
                for p in current.glob(pattern)
            ):
                counts["FEAT_reports_finished"] += 1
        summary[label] = counts
    return summary


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--archive-fsl",
        action="append",
        default=[],
        type=Path,
        help="additional known historical derivatives/fsl directory",
    )
    parser.add_argument(
        "--jobs",
        type=int,
        default=2,
        choices=range(1, 16),
        metavar="1..15",
        help="maximum concurrent FEAT launches (default 2)",
    )
    modes = parser.add_mutually_exclusive_group()
    modes.add_argument("--check", action="store_true", help="inventory without fitting or publishing")
    modes.add_argument("--status", action="store_true", help="read private current status")
    args = parser.parse_args()
    project = args.project.expanduser().resolve()
    work = project / SUBDIR
    if args.status:
        p = work / "status.json"
        if p.exists():
            summary = json.loads(p.read_text())
            summary["local_FEAT_jobs"] = activity(work)
            print(json.dumps(summary, indent=2))
        else:
            print("No local status yet.")
        return 0
    os.umask(0o077)
    require(
        not re.search(r"[^/A-Za-z0-9._+-]", str(work)), "FEAT working path contains unsupported characters"
    )
    work.mkdir(parents=True, exist_ok=True)
    with (work / "controller.lock").open("a") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Controller already active. Use --status or the launch log.")
            return 0
        try:
            return run(project, work, args)
        except (
            hist.Prerequisite,
            OSError,
            KeyError,
            ValueError,
            RuntimeError,
            subprocess.CalledProcessError,
        ) as exc:
            # Never publish private path strings, command lines or FEAT logs.
            write_json(work / "last_error.json", {"error": str(exc)})
            print(
                "Stopped: %s. Private record: %s" % (exc, work / "last_error.json"),
                file=sys.stderr,
                flush=True,
            )
            if not args.check:
                text = str(exc).lower()
                reason = "controller_or_prerequisite_failure"
                for token, code in (
                    ("fsl ", "fsl_unavailable"),
                    ("git object", "historical_git_asset_unavailable"),
                    ("template", "historical_template_unverified"),
                    ("roster", "cohort_unverified"),
                    ("cohort", "cohort_unverified"),
                    ("seed", "submitted_seed_unverified"),
                    ("launch", "historical_launch_unverified"),
                    ("derivatives/fsl", "project_fsl_directory_unavailable"),
                ):
                    if token in text:
                        reason = code
                        break
                if isinstance(exc, subprocess.CalledProcessError) and exc.cmd[0] == "git":
                    reason = "git_publication_failed"
                error = {"phase": "blocked", "reason": reason}
                previous = work / "status.json"
                if previous.is_file():
                    try:
                        prior = json.loads(previous.read_text())
                        if "lower_level" in prior:
                            error["lower_level"] = prior["lower_level"]
                    except (OSError, ValueError):
                        pass
                write_json(work / "status.json", error)
                try:
                    git_publish(project, PROGRESS, error)
                except (OSError, subprocess.CalledProcessError) as pub_error:
                    print("Aggregate status publication failed: %s" % pub_error, file=sys.stderr)
            return 2


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (hist.Prerequisite, OSError) as error:
        sys.exit(str(error))
