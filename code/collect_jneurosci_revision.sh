#!/usr/bin/env bash
# Read archived FEAT products for JN-RM-0845-26. No FSL model is run.
# Usage: bash code/collect_jneurosci_revision.sh PROJECT_DIR NEW_REPORT_DIR
set -euo pipefail
if [[ $# -ne 2 ]]; then
    echo "Usage: bash $0 PROJECT_DIR NEW_REPORT_DIR" >&2
    exit 2
fi
python3 - "$1" "$2" <<'PY'
import csv
import hashlib
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys

project = Path(sys.argv[1]).expanduser().resolve(strict=True)
fsl = project / "derivatives" / "fsl"
if not fsl.is_dir():
    raise SystemExit("Missing derivatives/fsl under " + str(project))
report = Path(sys.argv[2]).expanduser().resolve()
if project == report or project in report.parents:
    raise SystemExit("Choose a new report directory outside the analysis project.")
report.mkdir(mode=0o700, parents=False, exist_ok=False)

manifest = []
matrix = []
group_rows = []
summary = []
errors = []
fs = shutil.which("fslstats")
target = "L3_model-01_task-cardgame_n28_FLAME1+2"
strict_cortical = {"interactionC4", "interactionC5"}
historical = {"leftvlpfc", "rightvlpfc", "bilateralvlpfc", "vlpfc", "lvlpfc", "rvlpfc",
              "act_lvlpfc", "act_rvlpfc", "leftvlpfc-int", "rightvlpfc-int"}
main_contrasts = {("act", 5), ("act", 9), ("ppi_seed-rightVS", 19)}
cortical_contrasts = {16, 17, 18, 19}
expected = set(main_contrasts)
expected.update(("ppi_seed-" + seed, cope) for seed in strict_cortical for cope in (16, 19))

def tab(path, header, rows):
    with path.open("w", encoding="utf-8", newline="") as out:
        writer = csv.writer(out, delimiter="\t", lineterminator="\n")
        writer.writerow(header)
        writer.writerows(rows)

def copy_file(source, destination):
    if not source.is_file():
        return False
    destination.parent.mkdir(parents=True, exist_ok=True)
    # Different group-model paths always get separate output directories.
    shutil.copyfile(source, destination)
    digest = hashlib.sha256(destination.read_bytes()).hexdigest()
    manifest.append([str(source), str(destination.relative_to(report)), destination.stat().st_size, digest])
    return True

def valid_image(source):
    if not source.is_file():
        return "missing", "", ""
    if fs is None:
        return "present; fslstats unavailable", "", ""
    proc = subprocess.run([fs, str(source), "-R", "-V"], stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          universal_newlines=True)
    fields = proc.stdout.split()
    if proc.returncode or len(fields) != 4:
        errors.append(str(source) + ": " + (proc.stderr.strip() or "unexpected fslstats output"))
        return "unreadable", "", ""
    return "readable", ",".join(fields[:2]), fields[2]

def scan_groups(base):
    # FEAT can have millions of lower-level files. Prune .gfeat/.feat and sub-* at discovery.
    for dirname, dirs, _ in os.walk(base):
        current = Path(dirname)
        if len(current.relative_to(base).parts) > 3:
            dirs[:] = []
            continue
        for name in sorted(dirs):
            if not name.endswith(".gfeat"):
                continue
            match = re.match(r"L3_task-cardgame_type-(.+?)_cnum-(\d+)_cname-(.+?)_onegroup\.gfeat$", name)
            if match:
                yield current / name, match.group(1), int(match.group(2)), match.group(3)
        dirs[:] = [d for d in dirs if not (d.startswith(("sub-", ".")) or d.endswith((".feat", ".gfeat")))]

def focus(kind, cope):
    if (kind, cope) in main_contrasts:
        return True
    if not kind.startswith("ppi_seed-") or cope not in cortical_contrasts:
        return False
    seed = kind[len("ppi_seed-"):]
    return seed in strict_cortical or seed.lower() in historical

def copy_fsf_inputs(source, group_id):
    if not source.is_file():
        return
    text = source.read_text(errors="replace")
    inputs = re.findall(r'^set feat_files\((\d+)\)\s+"([^"]+)"', text, flags=re.M)
    for i, path in inputs:
        match = re.search(r"/(sub-[A-Za-z0-9]+?)/.*?/cope(\d+)\.feat", path)
        group_rows.append([group_id, i, match.group(1) if match else "", match.group(2) if match else "", path])
    relevant = [line for line in text.splitlines() if re.match(
        r'^set fmri\((npts|mixed_yn|evs_orig|threshmask|thresh|prob_thresh|z_thresh|conname_real\.\d+)\)', line)]
    summary.append(group_id + ": " + " | ".join(relevant))

found = set()
groups = sorted((g, k, c, nm) for g, k, c, nm in scan_groups(fsl) if focus(k, c))
for idx, (g, kind, cope, contrast_name) in enumerate(groups, 1):
    group_id = "%03d" % idx
    exact = g.parent.name == target
    if exact:
        found.add((kind, cope))
    dst = report / "models" / group_id
    feat = g / "cope1.feat"
    main_fsf = g / "design.fsf"
    if not main_fsf.is_file():
        # Adjacent FSFs are original command inputs when the FEAT directory omits the copy.
        main_fsf = g.parent / ("L3_task-cardgame_type-%s_copenum-%d_onegroup.fsf" % (kind, cope))
    if copy_file(main_fsf, dst / "group-design.fsf"):
        copy_fsf_inputs(main_fsf, group_id)
    for source, dest in [(g / "design.con", "group-design.con"), (g / "design.mat", "group-design.mat"),
                         (feat / "design.con", "cope-design.con"), (feat / "design.mat", "cope-design.mat"),
                         (feat / "stats" / "smoothness", "smoothness.txt"),
                         (feat / "mask.nii.gz", "search-mask.nii.gz")]:
        copy_file(source, dst / dest)
    for sign in (1, 2):
        # Standard-space file contains MNI mm; plain .txt can instead contain voxel indices.
        std = "cluster_zstat%d_std.txt" % sign
        plain = "cluster_zstat%d.txt" % sign
        std_present = copy_file(feat / std, dst / std)
        plain_present = copy_file(feat / plain, dst / plain)
        zstat = "thresh_zstat%d.nii.gz" % sign
        copied = copy_file(feat / zstat, dst / zstat)
        state, value_range, count = valid_image(feat / zstat)
        mask = "cluster_mask_zstat%d.nii.gz" % sign
        copied_mask = copy_file(feat / mask, dst / mask)
        matrix.append([group_id, str(g.relative_to(fsl)), exact, kind, cope, contrast_name,
                       sign, std_present, plain_present, copied, state, value_range, count, copied_mask])

# The tissue label is insufficient to distinguish January vs submitted-analysis-space seeds.
# Copy only the small group masks and a few small text files documenting seed/model provenance.
seed_names = {"seed-interactionC4.nii.gz", "seed-interactionC5.nii.gz", "act_lVLPFC.nii.gz",
              "act_rVLPFC.nii.gz", "bilateralVLPFC.nii.gz", "leftVLPFC.nii.gz", "rightVLPFC.nii.gz",
              "seed-rightVS.nii.gz"}
for folder in (project / "masks", project / "masks" / "singletrial-masks"):
    for filename in sorted(seed_names):
        copy_file(folder / filename, report / "sources" / folder.relative_to(project) / filename)
for rel in ("code/L1stats.sh", "code/L2stats.sh", "code/L3stats.sh", "templates/L3_template_n28.fsf",
            "templates/L1_template-m01_ppi.fsf", "logs/rerunL3_date-2021-11-22T2250.log",
            "logs/rerunL3_date-2021-12-04T1509.log"):
    copy_file(project / rel, report / "sources" / rel)

# Confirm run selection in the case that changed between January and November 2021.
sub_dir = fsl / "sub-232"
for kind in ("act", "ppi_seed-interactionC4", "ppi_seed-interactionC5", "ppi_seed-rightVS",
             "ppi_seed-leftVLPFC", "ppi_seed-rightVLPFC", "ppi_seed-bilateralVLPFC"):
    name = "L2_task-cardgame_model-01_%s_sm-6.gfeat" % kind
    lower = sub_dir / name / "design.fsf"
    if lower.is_file():
        copy_file(lower, report / "sources" / "L2_designs" / (kind + ".fsf"))
    # One run-level model documents seed time-series naming and the direction of COPE 19.
    first = sub_dir / ("L1_task-cardgame_model-01_%s_run-01_sm-6.feat" % kind)
    for fn in ("design.fsf", "design.con"):
        copy_file(first / fn, report / "sources" / "L1_designs" / kind / fn)

tab(report / "contrasts.tsv", ["id", "group_path", "expected_model_parent", "analysis", "cope", "name",
    "group_zstat", "table_MNI_mm", "table_native", "thresholded_map", "read_status", "range_min_max",
    "nonzero_voxels", "cluster_labels"], matrix)
tab(report / "group_inputs.tsv", ["id", "row", "participant_code", "input_cope", "input_path"], group_rows)
tab(report / "missing_expected.tsv", ["expected_model_parent", "analysis", "cope"],
    [[target, k, c] for k, c in sorted(expected - found)])
tab(report / "manifest.tsv", ["source", "report_file", "bytes", "sha256"], manifest)
(report / "design_summary.txt").write_text("\n".join(summary) + "\n")
(report / "read_errors.txt").write_text("\n".join(errors) + ("\n" if errors else ""))
print("Collected %d candidate models to %s." % (len(groups), report))
print("Review contrasts.tsv, missing_expected.tsv, group_inputs.tsv and read_errors.txt.")
print("A missing model or missing table does not establish a thresholded null.")
PY
