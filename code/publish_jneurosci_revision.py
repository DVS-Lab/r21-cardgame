"""Build a public, aggregate-only result from a private CardGame FEAT retrieval report."""
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import struct
import os
import subprocess
import tempfile

# SHA256 of the sorted, newline-terminated 28-person roster in the submitted FEAT template.
COHORT = "d768be3b713b38c54473714cc4302105cc08172f6111c9dc5f6dc1d7dfa6f44d"
TEMPLATE = "L3_model-01_task-cardgame_n28_FLAME1+2"
GRID = (3., 0., 0., -96.5, 0., 3., 0., -132.5, 0., 0., 3., -78.5)
SEEDS = {
    "left VLPFC": ("seed-interactionC4.nii.gz", "singletrial-masks/act_lVLPFC.nii.gz",
                   "f4cce9ad78c775099af20e36d075a2a356c8d955d92208228af27ea8cd70d518"),
    "right VLPFC": ("seed-interactionC5.nii.gz", "singletrial-masks/act_rVLPFC.nii.gz",
                    "7e245335ebd3a38ac4bb40a649ada55fd6675f013c7ed6439b568f0106f7844e"),
    "right VS": ("seed-rightVS.nii.gz", None,
                 "4944d22d3a64bda57a02772d24589f42054127633d0fd04d0de4cca0efb17ddb"),
}
PPI = {16: "ppi_vlpfc-tpj", 17: "ppi_R_vlpfc-tpj", 18: "ppi_P_vlpfc-tpj", 19: "ppi_interaction"}
TYPES = {2: "B", 4: "h", 8: "i", 16: "f", 64: "d", 256: "b", 512: "H", 768: "I"}


def tsv(path):
    if not path.is_file():
        return []
    with path.open(encoding="utf-8-sig", newline="") as stream:
        return list(csv.DictReader(stream, delimiter="\t"))


def number(value):
    out = float(value)
    if not math.isfinite(out):
        raise ValueError("nonfinite numeric field")
    return out


def nifti(path):
    """Read only the small deposited 3-D group images; never read a participant image."""
    if not path.is_file():
        return None
    try:
        with gzip.open(str(path), "rb") as stream:
            header = stream.read(348)
            endian = "<" if header[:4] == struct.pack("<i", 348) else ">"
            field = lambda fmt, offset: struct.unpack_from(endian + fmt, header, offset)
            dims = field("8h", 40)
            if (field("i", 0)[0] != 348 or header[344:347] != b"n+1" or
                    dims[0] < 3 or dims[0] > 7 or any(n != 1 for n in dims[4:dims[0]+1])):
                raise ValueError("not a single 3-D NIfTI-1 image")
            shape = tuple(dims[1:4])
            count = shape[0] * shape[1] * shape[2]
            if min(shape) <= 0 or count > 10000000:
                raise ValueError("unsupported image size")
            fmt = endian + TYPES[field("h", 70)[0]]
            slope, intercept = field("2f", 112)
            if slope == 0 or math.isnan(slope):
                slope, intercept = 1., 0.
            stream.seek(int(field("f", 108)[0]))
            raw = stream.read(count * struct.calcsize(fmt))
            if len(raw) != count * struct.calcsize(fmt):
                raise ValueError("incomplete image")
            values = [v[0] * slope + intercept for v in struct.iter_unpack(fmt, raw)]
            if any(not math.isfinite(v) for v in values):
                raise ValueError("nonfinite image")
            return (values, shape, field("12f", 280) if field("h", 254)[0] else None)
    except (OSError, EOFError, KeyError, ZeroDivisionError, ValueError, struct.error):
        return None


def mask_summary(path, reference):
    img = nifti(path)
    if img is None:
        return {"available": path.is_file(), "matches_reference": None}
    values, shape, affine = img
    mask = bytes(value != 0 for value in values)
    match = (shape == (65, 77, 65) and affine == GRID and
             hashlib.sha256(mask).hexdigest() == reference)
    return {"available": True, "voxels": sum(mask), "matches_reference": match}


def design_info(folder, inputs, cope):
    path = folder / "group-design.fsf"
    raw = path.read_text(errors="replace") if path.is_file() else ""
    settings = dict(re.findall(r'^set fmri\(([^)]+)\)\s+([^\n]*)', raw, re.M))
    def get(key):
        try:
            return number(settings[key].strip().strip('"'))
        except (KeyError, ValueError):
            return None
    ids = [row["participant_code"] for row in inputs]
    digest = hashlib.sha256(("\n".join(sorted(ids)) + "\n").encode()).hexdigest()
    cohort = (len(ids) == len(set(ids)) == 28 and digest == COHORT) if inputs else None
    matched_cope = all(r.get("input_cope", "").isdigit() and int(r["input_cope"]) == cope for r in inputs) if inputs else None
    con = folder / "cope-design.con"
    if not con.is_file():
        con = folder / "group-design.con"
    signs = [get("con_real1.1"), get("con_real2.1")]
    signed = signs == [1, -1] and get("evs_orig") == 1 if all(i is not None for i in signs) else None
    if con.is_file():
        txt = con.read_text(errors="replace")
        matrix = txt.split("/Matrix", 1)[-1].strip().splitlines()
        try:
            observed = [[number(v) for v in line.split()] for line in matrix if line.strip()]
            signed = observed == [[1.], [-1.]] and signed is not False
        except ValueError:
            signed = False
    z, p = get("z_thresh"), get("prob_thresh")
    whole = settings.get("threshmask", "").strip() == '""' if raw else None
    complete = (get("npts") == 28 and cohort is True and matched_cope is True and signed and
                get("mixed_yn") == 1 and get("thresh") == 3 and z == 3.1 and p == .05 and whole)
    return {"N_design": get("npts"), "N_group_inputs": len(inputs), "submitted_cohort_match": cohort,
            "input_cope_match": matched_cope, "FLAME_1_plus_2": get("mixed_yn") == 1 if raw else None,
            "whole_brain_cluster_correction": (get("thresh") == 3 and whole) if raw else None,
            "positive_negative_directions_verified": signed if raw or con.is_file() else None,
            "cluster_forming_Z": z, "cluster_corrected_alpha": p, "design_verified": bool(complete)}


def cluster_table(folder, sign):
    """Only whitelist aggregate columns. Native coordinate columns explicitly retain their units."""
    for name in ("cluster_zstat%d_std.txt" % sign, "cluster_zstat%d.txt" % sign):
        source = folder / name
        if not source.is_file():
            continue
        try:
            with source.open(encoding="utf-8-sig", newline="") as stream:
                reader = csv.DictReader(stream, delimiter="\t")
                header = set(reader.fieldnames or [])
                if not {"Cluster Index", "Voxels", "P", "Z-MAX"}.issubset(header):
                    continue
                rows = []
                for row in reader:
                    raw_p = row["P"].strip()
                    p = number(raw_p)
                    if not 0 <= p <= 1 or not re.fullmatch(r"(?:\d+\.?\d*|\.\d+)(?:[Ee][+-]?\d+)?", raw_p):
                        raise ValueError("invalid cluster p")
                    item = {"cluster_index": int(row["Cluster Index"]), "voxels": int(row["Voxels"]),
                            "cluster_corrected_p": p, "FSL_printed_p": raw_p, "peak_Z_magnitude": number(row["Z-MAX"])}
                    for unit, label in (("mm", "MNI_mm"), ("vox", "voxel_indices")):
                        cols = ["Z-MAX %s (%s)" % (axis, unit) for axis in "XYZ"]
                        if all(k in row for k in cols):
                            item["peak_" + label] = [number(row[k]) for k in cols]
                            break
                    if item["voxels"] <= 0 or item["cluster_index"] <= 0 or item["peak_Z_magnitude"] <= 0:
                        raise ValueError("invalid cluster extent, ID or peak")
                    rows.append(item)
                if len({r["cluster_index"] for r in rows}) != len(rows):
                    raise ValueError("duplicate clusters")
                return rows
        except (KeyError, TypeError, ValueError, UnicodeError):
            continue
    return None


def map_clusters(stat, labels):
    if stat is None or labels is None or stat[1:] != labels[1:]:
        return None
    items = {}
    for pos, (z, label) in enumerate(zip(stat[0], labels[0])):
        if z == 0 and label == 0:
            continue
        if z <= 0 or label <= 0 or label != int(label):
            return None
        rec = items.setdefault(int(label), [0, -1., 0])
        rec[0] += 1
        if z > rec[1]:
            rec[1:] = [z, pos]
    rows = []
    for label, (extent, peak, pos) in sorted(items.items(), reverse=True):
        shape, affine = stat[1:]
        x = pos % shape[0]
        y = (pos // shape[0]) % shape[1]
        z = pos // (shape[0] * shape[1])
        row = {"cluster_index": label, "voxels": extent, "peak_Z_magnitude": peak, "cluster_corrected_p": None}
        if affine == GRID and shape == (65,77,65):
            row["peak_MNI_mm"] = [sum(w*v for w, v in zip(affine[i:i+4], (x,y,z,1))) for i in (0,4,8)]
        rows.append(row)
    return rows


def sign_info(folder, sign, eligible, recorded):
    table = cluster_table(folder, sign)
    threshold = folder / ("thresh_zstat%d.nii.gz" % sign)
    stat = nifti(threshold)
    labels_file = folder / ("cluster_mask_zstat%d.nii.gz" % sign)
    labels = nifti(labels_file)
    count = sum(v != 0 for v in stat[0]) if stat is not None else None
    derived = map_clusters(stat, labels)
    disagree = bool(count is not None and table is not None and sum(r["voxels"] for r in table) != count)
    if recorded and recorded.get("read_status") == "readable" and count is not None:
        try:
            disagree |= int(recorded["nonzero_voxels"]) != count
        except (TypeError, ValueError):
            disagree = True
    if labels is not None and stat is not None:
        disagree |= derived is None
    if derived is not None and table is not None:
        expected = {row["cluster_index"]: row for row in table}
        disagree |= len(derived) != len(expected)
        for row in derived:
            ref = expected.get(row["cluster_index"])
            if ref is None or ref["voxels"] != row["voxels"] or abs(ref["peak_Z_magnitude"]-row["peak_Z_magnitude"]) > .055:
                disagree = True
    if stat is not None and min(stat[0]) < 0:
        disagree = True
    if table and any(r["cluster_corrected_p"] > .05 or r["peak_Z_magnitude"] < 3.095 for r in table):
        disagree = True
    original_fsl = (recorded or {}).get("read_status")
    if original_fsl not in ("readable", "missing", "unreadable", "present; fslstats unavailable"):
        original_fsl = "not recorded"
    if disagree:
        status = "conflicting_outputs"
    elif not eligible:
        status = "unverified_model"
    elif count == 0:
        status = "no_surviving_clusters"
    elif table:
        status = "clusters_reported"
    elif count is not None and count > 0:
        status = "clusters_present_exact_p_unavailable"
    else:
        status = "incomplete_output"
    return {"zstat": sign, "direction": "positive" if sign == 1 else "negative", "status": status,
            "thresholded_map_present": threshold.is_file(), "local_NIfTI_readable": stat is not None,
            "thresholded_map_readable": stat is not None, "original_fslstats_status": original_fsl,
            "nonzero_voxels": count, "cluster_labels_readable": labels is not None,
            "cluster_table_readable": table is not None,
            "clusters": table if table is not None else derived}


def group_summary(report: Path) -> dict:
    report = Path(report)
    inventory = tsv(report / "contrasts.tsv")
    inputs = tsv(report / "group_inputs.tsv")
    models = []
    seeds = {}
    for seed, (named, fallback, identity) in SEEDS.items():
        base = report / "sources" / "masks"
        seeds[seed] = {"named_seed": mask_summary(base / named, identity)}
        if fallback:
            seeds[seed]["reference_cluster"] = mask_summary(base / fallback, identity)
    checks = [("act", 5, "R-P", "activation"), ("act", 9, "interaction", "activation"),
              ("ppi_seed-rightVS", 19, PPI[19], "right VS")]
    for alias, label in (("interactionC4","left VLPFC"), ("interactionC5","right VLPFC")):
        checks.extend(("ppi_seed-"+alias, c, PPI[c], label) for c in (16, 19, 17, 18))
    for kind, cope, contrast, label in checks:
        matched = [r for r in inventory if r.get("analysis") == kind and r.get("cope") == str(cope)
                   and r.get("name") == contrast and r.get("expected_model_parent") == "True"
                   and Path(r["group_path"]).parent.name == TEMPLATE and re.fullmatch(r"\d+", r["id"])]
        ids = {r["id"] for r in matched}
        model = {"analysis": label, "cope": cope, "contrast": contrast, "model_available": len(ids) == 1}
        models.append(model)
        if len(ids) != 1:
            why = "model_missing" if not ids else "ambiguous_model"
            model["signs"] = [{"zstat": i, "status": why} for i in (1, 2)]
            continue
        model_id = ids.pop()
        folder = report / "models" / model_id
        model["design"] = design_info(folder, [r for r in inputs if r["id"] == model_id], cope)
        eligible = model["design"]["design_verified"]
        if label in seeds:
            masks = seeds[label]
            # A present but unreadable/mismatched named seed cannot be rescued by a reference copy.
            if masks["named_seed"]["available"]:
                seed_ok = masks["named_seed"]["matches_reference"] is True
            else:
                seed_ok = masks.get("reference_cluster", {}).get("matches_reference") is True
            if masks.get("reference_cluster", {}).get("matches_reference") is False:
                seed_ok = False
            model["seed_reference_verified"] = seed_ok
            eligible = eligible and seed_ok
        model["signs"] = [sign_info(folder, sign, eligible, next(
            (r for r in matched if r["group_zstat"] == str(sign)), None)) for sign in (1, 2)]
    return {"seeds": seeds, "models": models}


PUBLIC_PATH = "derivatives/jneurosci_revision/group_results.json"
REPORT_FILES = ("contrasts.tsv", "missing_expected.tsv", "group_inputs.tsv",
                "manifest.tsv", "design_summary.txt", "read_errors.txt")


def complete(report):
    return all((report / name).is_file() for name in REPORT_FILES)


def latest_report():
    candidates = sorted(path for path in Path.home().glob("cardgame-revision-*")
                        if re.fullmatch(r"cardgame-revision-[0-9]{8}-[0-9]{6}", path.name)
                        and complete(path))
    if not candidates:
        raise ValueError("No completed cardgame-revision-YYYYMMDD-HHMMSS report found in your home directory.")
    return candidates[-1]


def publish(report, repo):
    if not complete(report):
        raise ValueError("Incomplete report in " + str(report))
    payload = json.dumps(group_summary(report), indent=2, sort_keys=True, allow_nan=False) + "\n"

    def git(*args, **kwargs):
        result = subprocess.run(["git", "-C", str(repo)] + list(args), check=True,
                                stdout=subprocess.PIPE, universal_newlines=True, **kwargs)
        return result.stdout.strip()

    # Build the commit on origin/main using a separate index. A scientist's
    # staged files, working tree and unpushed local commits stay out of it.
    with tempfile.TemporaryDirectory() as temp:
        index_env = dict(os.environ, GIT_INDEX_FILE=str(Path(temp) / "index"))
        git("fetch", "--no-tags", "origin", "refs/heads/main")
        parent = git("rev-parse", "FETCH_HEAD")
        git("read-tree", parent, env=index_env)
        blob = git("hash-object", "-w", "--stdin", input=payload)
        git("update-index", "--add", "--cacheinfo", "100644," + blob + "," + PUBLIC_PATH, env=index_env)
        tree = git("write-tree", env=index_env)
        if tree == git("rev-parse", parent + "^{tree}"):
            print("Already published on origin/main: " + PUBLIC_PATH)
            return
        ident = subprocess.run(["git", "-C", str(repo), "var", "GIT_AUTHOR_IDENT"],
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        defaults = [] if ident.returncode == 0 else [
            "-c", "user.name=CardGame results collector", "-c", "user.email=cardgame-collector@localhost"]
        commit = git(*defaults, "commit-tree", tree, "-p", parent, "-m", "Publish JNeurosci group imaging results")
        git("push", "origin", commit + ":refs/heads/main")
        print("Published " + PUBLIC_PATH + " to origin/main at " + commit[:12])


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Publish aggregate FEAT results from a completed local report.")
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--publish-latest", action="store_true")
    mode.add_argument("--publish-report", type=Path, metavar="DIRECTORY")
    args = parser.parse_args()
    try:
        report = latest_report() if args.publish_latest else args.publish_report.expanduser().resolve()
        print("Using " + str(report), flush=True)
        publish(report, Path(__file__).resolve().parent.parent)
    except subprocess.CalledProcessError as exc:
        parser.exit(1, "Git failed (exit %d). The report is still on Linux1. After resolving the Git error, "
                       "retry with --publish-latest or --publish-report DIRECTORY.\n" % exc.returncode)
    except (OSError, ValueError) as exc:
        parser.exit(1, str(exc) + "\n")


if __name__ == "__main__":
    main()
