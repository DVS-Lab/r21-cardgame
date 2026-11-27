"""Prepare private, verified run and participant inputs for the original CardGame cortical gPPI."""

import csv
import fcntl
import gzip
import hashlib
import io
import itertools
from functools import lru_cache
import json
import math
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import tarfile
import tempfile
import time
from concurrent.futures import ThreadPoolExecutor

import recover_jneurosci_revision as historical

MODEL = "33becdaac3a1b2f64e464036215913fb45620921"
TIMINGS = "9ebb1fc9751904c78cea1d0c8d22ed67e6776e0f"
GRID = (3.0, 0.0, 0.0, -96.5, 0.0, 3.0, 0.0, -132.5, 0.0, 0.0, 3.0, -78.5)
SHAPE = (65, 77, 65)
CONDITIONS = ("reward_vlpfc", "reward_rtpj", "punish_vlpfc", "punish_rtpj")
SEEDS = ("interactionC4", "interactionC5")
COPES = (16, 19)
PRIOR_LAUNCH = "logs/rerunL1_date-2021-11-22T0204.log"


class InputError(RuntimeError):
    def __init__(self, detail, category="source_design_unverified"):
        super().__init__(detail)
        self.category = category


def insist(ok, detail):
    if not ok:
        raise InputError(detail)


def binary(project, commit, path):
    result = subprocess.run(
        ["git", "-C", str(project), "show", commit + ":" + path],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    insist(result.returncode == 0, "Missing Git object " + commit + ":" + path)
    return result.stdout


def sha(path):
    return historical.digest(path)


def save(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(dir=str(path.parent), delete=False) as f:
        f.write(data)
        name = f.name
    os.replace(name, str(path))


def json_save(path, data):
    save(path, (json.dumps(data, sort_keys=True, indent=2) + "\n").encode())


def load_json(path):
    try:
        return json.loads(path.read_text())
    except (OSError, ValueError):
        return {}


def key_for(parts):
    return hashlib.sha256(json.dumps(parts, sort_keys=True).encode()).hexdigest()


def grid(path, series=False):
    try:
        with gzip.open(str(path), "rb") as f:
            h = f.read(348)
        endian = "<" if h[:4] == struct.pack("<i", 348) else ">"
        dim = struct.unpack_from(endian + "8h", h, 40)
        affine = struct.unpack_from(endian + "12f", h, 280)
        if (
            h[344:347] != b"n+1"
            or dim[1:4] != SHAPE
            or affine != GRID
            or struct.unpack_from(endian + "h", h, 254)[0] <= 0
        ):
            return None
        kind, bits = struct.unpack_from(endian + "2h", h, 70)
        if {2: 8, 4: 16, 8: 32, 16: 32, 64: 64, 256: 8, 512: 16, 768: 32}.get(kind) != bits:
            return None
        if dim[0] not in (3, 4) or (dim[0] == 4 and dim[4] < 1):
            return None
        offset = struct.unpack_from(endian + "f", h, 108)[0]
        if not math.isfinite(offset) or offset < 352 or offset != int(offset):
            return None
        minimum = int(offset) + dim[1] * dim[2] * dim[3] * (dim[4] if dim[0] == 4 else 1) * (bits // 8)
        with path.open("rb") as raw:
            raw.seek(-4, 2)
            last_member = struct.unpack("<I", raw.read(4))[0]
        if last_member < minimum:
            # Concatenated gzip members have only the last member's size in the trailer.
            with gzip.open(str(path), "rb") as src:
                size = sum(len(chunk) for chunk in iter(lambda: src.read(8 * 1024 * 1024), b""))
            if size < minimum:
                return None
        if series:
            tr = struct.unpack_from(endian + "f", h, 92)[0]
            scale = {8: 1, 16: 0.001, 24: 0.000001}.get(h[123] & 56, 1.0)
            return dim[4] if dim[0] == 4 and dim[4] > 1 and abs(tr * scale - 2.0) < 0.001 else None
        return bool(dim[0] == 3 or (dim[0] == 4 and dim[4] == 1))
    except (OSError, EOFError, ValueError, struct.error):
        return None


def assets(project, work):
    folder = work / "specifications"
    base = binary(project, MODEL, "templates/L3_template_n28.fsf").decode()
    subjects = re.findall(r'^set feat_files\(\d+\) ".*?/(sub-\d+)/L2_', base, re.M)
    runs = historical.roster(project)
    insist(
        len(subjects) == 28 and set(subjects) == set(runs), "Template subject order differs from QC roster."
    )
    template = {
        n: binary(project, MODEL, "templates/" + n).decode()
        for n in ("L1_template-m01_ppi.fsf", "L2_copes-19_runs-2.fsf", "L2_copes-19_runs-3.fsf")
    }
    masks = {}
    for seed in SEEDS:
        path = folder / "masks" / ("seed-" + seed + ".nii.gz")
        save(path, binary(project, MODEL, "masks/" + path.name))
        expected = historical.pub.SEEDS[historical.SEEDS[seed]][2]
        insist(
            historical.pub.mask_summary(path, expected)["matches_reference"],
            "Wrong historic " + seed + " mask.",
        )
        masks[seed] = path
    result = subprocess.run(
        ["git", "-C", str(project), "archive", TIMINGS, "EVfiles"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    insist(result.returncode == 0, "Committed EV archive unavailable: " + TIMINGS)
    ev = {}
    with tarfile.open(fileobj=io.BytesIO(result.stdout)) as files:
        for member in files:
            m = re.fullmatch(r"EVfiles/(sub-\d+)/run-(\d+)_([a-z_]+)\.txt", member.name)
            if not member.isfile() or not m:
                continue
            sub, r, condition = m.groups()
            if int(r) not in runs.get(sub, set()) or condition not in CONDITIONS:
                continue
            raw = files.extractfile(member).read()
            target = folder / member.name
            save(target, raw)
            ev[(sub, int(r), condition)] = target
    insist(len(ev) == 79 * 4, "Incomplete archived run condition timings.")
    launches = binary(project, "6c5d0340", PRIOR_LAUNCH).decode()
    launched = {Path(name).parts[-2:] for name in re.findall(r"^running:\s+(\S+)", launches, re.M)}
    # This frozen MRIQC table contains the run-wise size_t and spacing_tr fields
    # from the individual BOLD JSON reports. The preprocessed run keeps every volume.
    mriqc = csv.DictReader(
        io.StringIO(binary(project, MODEL, "derivatives/mriqc/group_bold.tsv").decode()), delimiter="\t"
    )
    lengths = {}
    for row in mriqc:
        m = re.fullmatch(r"(sub-\d+)_task-cardgame_run-(\d+)_bold", row["bids_name"])
        if m and int(m.group(2)) in runs.get(m.group(1), set()):
            insist(float(row["spacing_tr"]) == 2.0, "Unexpected original TR.")
            lengths[(m.group(1), int(m.group(2)))] = int(row["size_t"])
    insist(len(lengths) == 79, "Cannot verify original volumes for each retained run.")
    for (sub, r, condition), path in ev.items():
        rows = numeric_rows(path)
        insist(
            len(rows) == 16
            and all(
                len(v) == 3
                and v[0] >= 0
                and v[1] > 0
                and v[2] == 1
                and v[0] + v[1] <= 2 * lengths[(sub, r)] + 0.001
                for v in rows
            ),
            "Invalid archived EV " + str(path),
        )
    return subjects, runs, template, masks, ev, launched, lengths


def numeric_rows(path):
    return [list(map(float, row.split())) for row in path.read_text().splitlines() if row.strip()]


def original_preprocessing(base, sub, bold, run, fsl):
    description = load_json(base / "dataset_description.json")
    entries = list(description.get("GeneratedBy", []) or [])
    if isinstance(description.get("PipelineDescription"), dict):
        entries.append(description["PipelineDescription"])
    versions = {
        str(row.get("Version", "")).lstrip("v")
        for row in entries
        if isinstance(row, dict) and "fmriprep" in str(row.get("Name", "")).lower() and row.get("Version")
    }
    if versions:
        return "verified" if versions == {"20.1.0"} else "different_version"
    report = base / (sub + ".html")
    if report.is_file():
        body = report.read_text(errors="replace")
        versions = set(
            re.findall(r"fMRIPrep(?:</?[^>]+>|[ \t,():-]|version|v){1,14}(\d+\.\d+\.\d+)", body, re.I)
        )
        if versions:
            return "verified" if versions == {"20.1.0"} else "different_version"
    # If version metadata was lost, bind the file itself to a completed November run.
    # Old timestamps or similarly named images in a different derivative are insufficient.
    old = fsl / sub / ("L1_task-cardgame_model-01_type-act_run-%02d_sm-6.feat" % run)
    if bold.stat().st_mtime <= 1637557440 and historical.dated_november_fit(old / "report.html"):
        design = historical.fsf(old / "design.fsf")
        inputs = re.findall(r'^set feat_files\(1\) "([^"]+)"', design, re.M)
        if len(inputs) == 1 and Path(inputs[0]).is_file() and os.path.samefile(inputs[0], str(bold)):
            return "verified"
    return "unknown"


def confounds(native, final, nvols):
    if final is not None:
        matrix = numeric_rows(final)
    else:
        with native.open(encoding="utf-8-sig", newline="") as f:
            reader = csv.DictReader(f, delimiter="\t")
            cols = reader.fieldnames or []
            use = [
                k
                for prefix in ("cosine", "non_steady_state", "aroma_motion_")
                for k in cols
                if k.startswith(prefix)
            ]
            insist(
                "csf" in cols and "white_matter" in cols,
                "Missing original fMRIPrep confound columns in " + str(native),
            )
            use.extend(("csf", "white_matter"))
            matrix = [[float(row[k]) for k in use] for row in reader]
    insist(
        len(matrix) == nvols
        and matrix
        and len(matrix[0]) >= 2
        and all(len(row) == len(matrix[0]) and all(math.isfinite(x) for x in row) for row in matrix),
        "Confounds and BOLD lengths or numeric fields disagree: " + str(final or native),
    )
    return ("\n".join("\t".join(format(x, ".17g") for x in row) for row in matrix) + "\n").encode()


def source_files(roots, sub, run, ev, expected_n, checks):
    matches = []
    seen = False
    version_rejected = False
    valid_version = False
    missing_nuisance = False
    for fsl in roots:
        deriv = fsl.parent / "fmriprep"
        func = deriv / sub / "func"
        for tag in dict.fromkeys((str(run), "%02d" % run)):
            stem = "%s_task-cardgame_run-%s_" % (sub, tag)
            bold = func / (stem + "space-MNI152NLin2009cAsym_desc-preproc_bold.nii.gz")
            if not bold.is_file():
                continue
            seen = True
            v = original_preprocessing(deriv, sub, bold, run, fsl)
            if v != "verified":
                version_rejected |= v == "different_version"
                continue
            valid_version = True
            n = grid(bold, True)
            if n != expected_n:
                continue
            checks["preprocessed_bold_verified"] = True
            # Some archived derivative paths pad the BOLD and nuisance run numbers differently.
            stems = [
                "%s_task-cardgame_run-%s_" % (sub, t) for t in dict.fromkeys((tag, str(run), "%02d" % run))
            ]
            final = next(
                (
                    fsl / "confounds" / sub / (s + "desc-fslConfounds.tsv")
                    for s in stems
                    if (fsl / "confounds" / sub / (s + "desc-fslConfounds.tsv")).is_file()
                ),
                None,
            )
            native = next(
                (
                    func / (s + ext)
                    for s in stems
                    for ext in ("desc-confounds_regressors.tsv", "desc-confounds_timeseries.tsv")
                    if (func / (s + ext)).is_file()
                ),
                None,
            )
            if final is None and native is None:
                # Search surviving FSL nuisance exports separately from the archived BOLD.
                # Conflicting matrices for the same subject/run cannot be silently substituted.
                alternatives = [
                    other / "confounds" / sub / (s + "desc-fslConfounds.tsv")
                    for other in roots
                    if original_preprocessing(other.parent / "fmriprep", sub, bold, run, other)
                    != "different_version"
                    for s in stems
                    if (other / "confounds" / sub / (s + "desc-fslConfounds.tsv")).is_file()
                ]
                matrices = {}
                for candidate in alternatives:
                    raw = confounds(None, candidate, n)
                    matrices.setdefault(hashlib.sha256(raw).hexdigest(), candidate)
                if len(matrices) > 1:
                    raise InputError(
                        "Conflicting archived nuisance files for " + str(bold), "conflicting_inputs"
                    )
                if len(matrices) == 1:
                    final = next(iter(matrices.values()))
            if final is None and native is None:
                missing_nuisance = True
                continue
            try:
                nuisance = confounds(native, final, n)
                if native is not None and final is not None:
                    original = confounds(native, None, n)
                    a = [line.split() for line in original.splitlines()]
                    b = [line.split() for line in nuisance.splitlines()]
                    if not all(
                        len(x) == len(y)
                        and all(
                            math.isclose(float(i), float(j), rel_tol=1e-9, abs_tol=1e-12)
                            for i, j in zip(x, y)
                        )
                        for x, y in zip(a, b)
                    ):
                        raise InputError(
                            "Saved nuisance differs from the historical selection of native columns: "
                            + str(final),
                            "conflicting_inputs",
                        )
            except (KeyError, ValueError) as e:
                raise InputError(
                    "Invalid fMRIPrep nuisance input " + str(final or native) + ": " + str(e),
                    "invalid_original_confounds",
                )
            checks["confounds_verified"] = True
            # Archived three-column condition EVs correspond to complete guess+feedback trials.
            for condition in CONDITIONS:
                orig = ev[(sub, run, condition)]
                rows = numeric_rows(orig)
                insist(
                    len(rows) == 16
                    and all(
                        len(row) == 3
                        and row[0] >= 0
                        and row[1] > 0
                        and row[2] == 1
                        and row[0] + row[1] <= 2 * n + 0.001
                        for row in rows
                    ),
                    "Invalid condition timing in " + str(orig),
                )
                live = fsl / "EVfiles" / sub / orig.name
                if live.is_file():
                    old = numeric_rows(live)
                    insist(
                        len(old) == len(rows)
                        and all(
                            len(a) == len(b) == 3 and all(abs(v - w) <= 1e-6 for v, w in zip(a, b))
                            for a, b in zip(old, rows)
                        ),
                        "Conflicting archived timing: " + str(live),
                    )
            matches.append((bold, n, nuisance, final or native))
    checks["different_preprocessing_version_found"] = version_rejected
    if not matches:
        category = (
            "missing_original_bold"
            if not seen
            else (
                "preprocessed_version_unverified"
                if not valid_version
                else "missing_original_confounds" if missing_nuisance else "bold_grid_or_length_mismatch"
            )
        )
        raise InputError(
            "%s: %s task-cardgame run %02d, expected %d volumes; searched %s"
            % (category, sub, run, expected_n, ", ".join(str(f.parent / "fmriprep") for f in roots)),
            category,
        )
    if len(matches) > 1:
        if len({(sha(b), hashlib.sha256(c).hexdigest()) for b, n, c, p in matches}) != 1:
            raise InputError(
                "Different candidate BOLD/nuisance inputs for %s run %d" % (sub, run), "conflicting_inputs"
            )
    return matches[0]


def l1_name(seed, run):
    return "L1_task-cardgame_model-01_type-ppi_seed-%s_run-%02d_sm-6.feat" % (seed, run)


def l2_name(seed):
    return "L2_task-cardgame_model-01_type-ppi_seed-%s_sm-6.gfeat" % seed


def fit_settings(raw, template):
    a, b = historical.configs(raw), historical.configs(template)
    ignore = {
        "outputdir",
        "npts",
        "regstandard",
        "totalVoxels",
        "featwatcher_yn",
        "version",
        "custom1",
        "custom2",
        "custom3",
        "custom4",
        "custom5",
    }
    # Compare model terms, settings, contrasts and nuisance handling to the frozen specification.
    return all(a.get(k) == v for k, v in b.items() if k not in ignore)


@lru_cache(maxsize=512)
def informative_variance(mask, variance, degrees, stamps):
    # Grid and file-completion checks precede this call. In-mask variance and DOF
    # can be zero in some voxels; at least one usable voxel must remain.
    m = historical.pub.nifti(Path(mask))
    v = historical.pub.nifti(Path(variance))
    d = historical.pub.nifti(Path(degrees)) if degrees else None
    if m is None or v is None or (degrees and d is None):
        return False
    dof = d[0] if d else itertools.repeat(1.0)
    valid = False
    for inside, var, n in zip(m[0], v[0], dof):
        if inside:
            if var < 0 or n < 0:
                return False
            valid |= var > 0 and n > 0
    return valid


def useful_files(mask, variance, degrees=None):
    paths = [mask, variance] + ([degrees] if degrees else [])
    try:
        stamps = tuple((p.stat().st_size, p.stat().st_mtime_ns) for p in paths)
    except OSError:
        return False
    return informative_variance(str(mask), str(variance), str(degrees) if degrees else "", stamps)


def usable_l2(folder):
    required = ["mask.nii.gz", "stats/cope1.nii.gz", "stats/varcope1.nii.gz", "stats/tdof_t1.nii.gz"]
    return (
        all(grid(folder / k) for k in required)
        and useful_files(
            folder / "mask.nii.gz", folder / "stats/varcope1.nii.gz", folder / "stats/tdof_t1.nii.gz"
        )
        and (folder / "design.lev").is_file()
        and "/PPheights" in historical.fsf(folder / "design.con")
        and any(grid(folder / k) for k in ("bg_image.nii.gz", "example_func.nii.gz", "standard.nii.gz"))
    )


def usable_l1(folder, copes):
    dof = historical.fsf(folder / "stats/dof").strip()
    try:
        good_dof = math.isfinite(float(dof)) and float(dof) > 0
    except ValueError:
        good_dof = False
    return (
        good_dof
        and "/PPheights" in historical.fsf(folder / "design.con")
        and all(grid(folder / k) for k in ("mean_func.nii.gz", "mask.nii.gz", "example_func.nii.gz"))
        and all(
            grid(folder / "stats" / ("%s%d.nii.gz" % (t, c))) for t in ("cope", "varcope") for c in copes
        )
        and all(
            useful_files(folder / "mask.nii.gz", folder / "stats" / ("varcope%d.nii.gz" % c)) for c in copes
        )
    )


def unversion(name, suffix):
    # FEAT appends '+' before its extension; older backups can append '+', '.N'
    # or a numbered '+' after the extension. Keep the full model basename intact.
    return re.sub(
        r"(?:\++(?:\d+)?|[.]\d+)?" + re.escape(suffix) + r"(?:\++(?:\d+)?|[.]\d+)?$", suffix, name
    )


def candidate_folders(roots, sub, canonical, suffix, seed):
    stem = canonical[: -len(suffix)]
    before, after = stem.split("seed-" + seed)
    alias_names = {
        "interactionC4": {"leftvlpfc", "lvlpfc", "act_lvlpfc", "leftvlpfc-int"},
        "interactionC5": {"rightvlpfc", "rvlpfc", "act_rvlpfc", "rightvlpfc-int"},
    }[seed]
    seen = set()
    for root in roots:
        folder = root / sub
        for p in folder.glob(before + "seed-*" + after + "*"):
            bare = unversion(p.name, suffix)
            if not bare.endswith(suffix) or not p.is_dir() or p.resolve() in seen:
                continue
            label = bare[len(before + "seed-") : -len(after + suffix)]
            alias = label.lower() in alias_names
            if label != seed and not alias:
                continue
            if bare != before + "seed-" + label + after + suffix:
                continue
            seen.add(p.resolve())
            yield p, alias


def find_archived_l2(roots, sub, rs, seed, cope, template, launched):
    paths = []
    for folder, alias in candidate_folders(roots, sub, l2_name(seed), ".gfeat", seed):
        target = folder / ("cope%d.feat" % cope)
        raw = historical.fsf(folder / "design.fsf")
        if not raw and not alias:
            raw = historical.fsf(folder.parent / (l2_name(seed).split("_sm-")[0] + ".fsf"))
        if (
            not historical.dated_november_fit(target / "report.html")
            or not usable_l2(target)
            or not fit_settings(raw, template)
        ):
            continue
        names = [
            (Path(p).parent.name, unversion(Path(p).name, ".feat"))
            for p in re.findall(r'^set feat_files\(\d+\) "([^"]+)"', raw, re.M)
        ]
        expected = [(sub, l1_name(seed, r)) for r in sorted(rs)]
        if historical.configs(raw).get("npts") != str(len(rs)):
            continue
        if names == expected and all((s, Path(n).stem) in launched for s, n in expected):
            paths.append(target)
    if len(paths) > 1:
        insist(
            len({tuple(sha(p / n) for n in historical.source_files(p)) for p in paths}) == 1,
            "Conflicting archived L2 copies: " + str(paths),
        )
    return paths[0] if paths else None


def find_archived_l1(roots, sub, run, seed, copes, template, launched, expected_n=None):
    name = l1_name(seed, run)
    if (sub, Path(name).stem) not in launched:
        return None
    results = []
    for folder, alias in candidate_folders(roots, sub, name, ".feat", seed):
        if not historical.dated_november_fit(folder / "report.html") or not usable_l1(folder, copes):
            continue
        raw = historical.fsf(folder / "design.fsf")
        if not raw and not alias:
            raw = historical.fsf(
                folder.parent / ("L1_%s_task-cardgame_model-01_seed-%s_run-%02d.fsf" % (sub, seed, run))
            )
        cfg = historical.configs(raw)
        if expected_n is not None and cfg.get("npts") != str(expected_n):
            continue
        bold = re.findall(r'^set feat_files\(1\) "([^"]+)"', raw, re.M)
        conf = re.findall(r'^set confoundev_files\(1\) "([^"]+)"', raw, re.M)
        allowed_runs = {str(run), "%02d" % run}
        if len(bold) != 1 or not any(
            Path(bold[0]).parts[-3:]
            == (
                sub,
                "func",
                sub + "_task-cardgame_run-" + tag + "_space-MNI152NLin2009cAsym_desc-preproc_bold.nii.gz",
            )
            for tag in allowed_runs
        ):
            continue
        if len(conf) != 1 or not any(
            Path(conf[0]).parts[-2:] == (sub, sub + "_task-cardgame_run-" + tag + "_desc-fslConfounds.tsv")
            for tag in allowed_runs
        ):
            continue
        if any(Path(cfg.get("custom%d" % i, "")).parent.name != sub for i in range(1, 6)):
            continue
        if not fit_settings(raw, template):
            continue
        if Path(cfg.get("custom5", "")).name != "ts_task-cardgame_mask-%s_run-%02d.txt" % (seed, run):
            continue
        if [Path(cfg.get("custom%d" % i, "")).name for i in range(1, 5)] != [
            "run-%02d_%s.txt" % (run, c) for c in CONDITIONS
        ]:
            continue
        results.append(folder)
    if len(results) > 1:
        fields = ["stats/%s%d.nii.gz" % (n, c) for c in copes for n in ("cope", "varcope")] + [
            "stats/dof",
            "mask.nii.gz",
            "mean_func.nii.gz",
            "example_func.nii.gz",
            "design.con",
        ]
        insist(
            len({tuple(sha(p / k) for k in fields) for p in results}) == 1,
            "Conflicting archived L1 copies: " + str(results),
        )
    return results[0] if results else None


def private_copy(src, dest, expected=None):
    dest.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(dir=str(dest.parent))
    os.close(fd)
    tmp = Path(name)
    try:
        shutil.copy2(str(src), str(tmp))
        insist(sha(tmp) == (expected or sha(src)), "Source changed during private copy: " + str(src))
        os.replace(str(tmp), str(dest))
    finally:
        if tmp.exists():
            tmp.unlink()


def register(folder):
    reg = folder / "reg"
    reg.mkdir(exist_ok=True)
    ident = Path(os.environ["FSLDIR"]) / "etc/flirtsch/ident.mat"
    for name in ("example_func2standard.mat", "standard2example_func.mat"):
        private_copy(ident, reg / name)
    private_copy(folder / "mean_func.nii.gz", reg / "standard.nii.gz")


def stage_l1(src, dest, copes):
    fields = ["mean_func.nii.gz", "example_func.nii.gz", "mask.nii.gz", "design.con", "stats/dof"]
    fields += ["stats/%s%d.nii.gz" % (t, c) for c in copes for t in ("cope", "varcope")]
    fields += [n for n in ("design.fsf", "design.mat") if (src / n).is_file()]
    for n in fields:
        private_copy(src / n, dest / n)
    register(dest)


def prepare_bold(work, sub, r, item):
    b, n, matrix, conf = item
    label = work / "private_sources" / sub / ("run-%02d" % r)
    target = label / b.name
    meta = label / "source.json"
    sig = sha(b)
    if not target.is_file() or load_json(meta).get("bold_sha256") != sig or sha(target) != sig:
        private_copy(b, target, sig)
    nuisance = label / "confounds.tsv"
    save(nuisance, matrix)
    record = {
        "bold": str(b),
        "bold_sha256": sig,
        "confounds": str(conf),
        "confounds_sha256": sha(nuisance),
        "volumes": n,
    }
    json_save(meta, record)
    return target, n, nuisance, record


def attempt_dir(base):
    # Start a fresh directory on the next invocation after a reported failure. Keep
    # every earlier log/output in place; an interrupted submission is polled in situ.
    number = 1
    while (base / ("attempt-%03d" % number) / "failed").is_file():
        number += 1
    job = base / ("attempt-%03d" % number)
    job.mkdir(parents=True, exist_ok=True)
    return job


def call_feat(template, out, fs, completion, logs, env):
    spec = fs.parent / "job.json"
    started = fs.parent / "submitted"
    fail = fs.parent / "failed"
    digest = hashlib.sha256(template.encode()).hexdigest()
    fs.parent.mkdir(parents=True, exist_ok=True)
    if spec.exists():
        insist(
            load_json(spec).get("fsf_digest") == digest, "Different design in private job " + str(fs.parent)
        )
    json_save(spec, {"fsf_digest": digest})
    if fail.exists():
        raise InputError("Previously failed FEAT job; see " + str(logs))
    if not started.exists():
        insist(not out.exists(), "Existing unowned result: " + str(out))
        save(fs, template.encode())
        save(started, b"submitted\n")
        try:
            with logs.open("w") as log:
                proc = subprocess.run(
                    [str(Path(env["FSLDIR"]) / "bin/feat"), str(fs)],
                    cwd=str(fs.parent),
                    env=env,
                    stdout=log,
                    stderr=subprocess.STDOUT,
                )
        except OSError as exc:
            save(fail, str(exc).encode())
            raise
        if proc.returncode:
            save(fail, str(proc.returncode).encode())
            raise InputError(
                "FEAT failed; inspect "
                + str(logs)
                + " and rerun after correcting the failure. A fresh private attempt will be used.",
                "lower_fit_failed",
            )
    deadline = time.monotonic() + 24 * 3600
    finished_since = None
    while True:
        html = historical.fsf(out / "report.html")
        if re.search(r"errors? occurr?ed during the analysis|fatal error", html, re.I):
            save(fail, b"FEAT report flagged error")
            raise InputError(
                "FEAT report flagged errors: " + str(out) + "; a rerun uses a fresh private attempt.",
                "lower_fit_failed",
            )
        if historical.pub.finished_report(out / "report.html"):
            if completion():
                break
            finished_since = finished_since or time.monotonic()
            if time.monotonic() - finished_since > 60:
                save(fail, b"completed report with missing output")
                raise InputError(
                    "FEAT finished without its required files; inspect " + str(logs) + " before retry.",
                    "lower_fit_failed",
                )
        if time.monotonic() >= deadline:
            raise InputError("FEAT still incomplete; retain private job: " + str(out))
        time.sleep(5)


def adapt_paths(template):
    # The historical FSF hardcodes a specific Debian installation. Use the corresponding
    # installed standard brain pathname only if required; the original mask/identity grid is unchanged.
    old = "/usr/share/fsl/5.0/data/standard/MNI152_T1_2mm_brain"
    if (Path(old + ".nii.gz")).is_file():
        return template
    return template.replace(old, str(Path(os.environ["FSLDIR"]) / "data/standard/MNI152_T1_2mm_brain"))


def run_l1(work, key, copes, templates, masks, ev, bold, archived, env):
    sub, r, seed = key
    if archived is not None:
        fields = ["stats/%s%d.nii.gz" % (t, c) for c in copes for t in ("cope", "varcope")] + [
            "stats/dof",
            "mask.nii.gz",
            "design.con",
            "mean_func.nii.gz",
            "example_func.nii.gz",
        ]
        stamp = key_for([MODEL, [(n, sha(archived / n)) for n in fields]])
        dest = work / "archived_runs" / stamp / sub / l1_name(seed, r)
        if not usable_l1(dest, copes):
            stage_l1(archived, dest, copes)
        return dest, "reused"
    data, n, conf, record = bold
    spec = templates["L1_template-m01_ppi.fsf"]
    vers = env["CARDGAME_FSL_VERSION"]
    stamp = key_for([MODEL, TIMINGS, record["bold_sha256"], record["confounds_sha256"], str(n), seed, vers])
    job = attempt_dir(work / "run_jobs" / sub / ("%s-%02d-%s" % (seed, r, stamp[:18])))
    out = job / l1_name(seed, r)
    fs = job / "design.fsf"
    job.mkdir(parents=True, exist_ok=True)
    signal = job / ("ts_task-cardgame_mask-%s_run-%02d.txt" % (seed, r))
    if not signal.is_file() or not (job / "submitted").exists():
        subprocess.run(
            [
                str(Path(env["FSLDIR"]) / "bin/fslmeants"),
                "-i",
                str(data),
                "-o",
                str(signal),
                "-m",
                str(masks[seed]),
            ],
            check=True,
            env=env,
        )
    vals = numeric_rows(signal)
    insist(
        len(vals) == n
        and all(len(row) == 1 and math.isfinite(row[0]) for row in vals)
        and max(vals) > min(vals),
        "Invalid or constant mean seed signal " + str(signal),
    )
    evprefix = ev[(sub, r, CONDITIONS[0])].parent / ("run-%02d" % r)
    template = adapt_paths(spec)
    for token, val in [
        ("OUTPUT", str(out)[:-5]),
        ("NVOLUMES", str(n)),
        ("DATA", str(data)),
        ("CONFOUNDEVS", str(conf)),
        ("EVDIR", str(evprefix)),
        ("PHYS", str(signal)),
    ]:
        template = template.replace(token, val)
    call_feat(template, out, fs, lambda: usable_l1(out, copes), job / "feat.log", env)
    register(out)
    return out, "reproduced"


def run_l2(work, sub, seed, rs, copes, templates, inputs, env):
    paths = [inputs[(sub, r, seed)][0] for r in sorted(rs)]
    # Each lower-level contrast is combined independently. FEAT preserves its original
    # COPE number when unused lower-level contrasts are disabled, e.g. cope19.feat.
    stamp = key_for([MODEL, seed, env["CARDGAME_FSL_VERSION"], sorted(copes), [str(p) for p in paths]])
    job = attempt_dir(work / "participant_jobs" / sub / (seed + "-" + stamp[:18]))
    job.mkdir(parents=True, exist_ok=True)
    out = job / l2_name(seed)
    spec = adapt_paths(templates["L2_copes-19_runs-%d.fsf" % len(rs)]).replace("OUTPUT", str(out)[:-6])
    for i, p in enumerate(paths, 1):
        spec = spec.replace("INPUT%d" % i, str(p))
    for c in range(1, 20):
        if c not in copes:
            spec = spec.replace("set fmri(copeinput.%d) 1" % c, "set fmri(copeinput.%d) 0" % c)

    def complete():
        return all(
            historical.pub.finished_report(out / ("cope%d.feat" % c) / "report.html")
            and usable_l2(out / ("cope%d.feat" % c))
            for c in copes
        )

    call_feat(spec, out, job / "design.fsf", complete, job / "feat.log", env)
    return {c: out / ("cope%d.feat" % c) for c in copes}


def parallel_tasks(tasks, worker, workers, errors):
    def run(key):
        try:
            return key, worker(key), None
        except (
            InputError,
            historical.Prerequisite,
            OSError,
            ValueError,
            subprocess.CalledProcessError,
        ) as exc:
            return key, None, str(exc)

    complete = {}
    with ThreadPoolExecutor(max_workers=workers) as pool:
        for key, value, error in pool.map(run, tasks):
            if error:
                errors.append(str(key) + ": " + error)
            else:
                complete[key] = value
    return complete


def exported_inputs(work, subjects, requested, outputs):
    remaining = {}
    for seed, cope in sorted(requested):
        keys = [(sub, seed, cope) for sub in subjects]
        if not all(k in outputs for k in keys):
            continue
        signed = []
        for k in keys:
            folder, where = outputs[k]
            signed.append((k[0], where, [(n, sha(folder / n)) for n in historical.source_files(folder)]))
        code = key_for([MODEL, seed, cope, signed])
        base = work / "verified_inputs" / code[:24]
        manifest = base / "private_provenance.json"
        prior = load_json(manifest)
        paths = []
        for (sub, _, _), (_, _, files) in zip(keys, signed):
            target = base / "derivatives/fsl" / sub / l2_name(seed) / ("cope%d.feat" % cope)
            origin = outputs[(sub, seed, cope)][0]
            for name, digest in files:
                p = target / name
                if not p.is_file() or sha(p) != digest:
                    private_copy(origin / name, p)
            insist(usable_l2(target), "Invalid private assembled fixed-effects input " + str(target))
            paths.append(str(target / "stats/cope1.nii.gz"))
        body = {
            "seed": seed,
            "cope": cope,
            "source_signature": code,
            "model_commit": MODEL,
            "participants": signed,
            "paths": paths,
            "input_sources": [outputs[k][1] for k in keys],
        }
        if prior != body:
            json_save(manifest, body)
        remaining[(seed, cope)] = (paths, body["input_sources"], str(manifest))
    return remaining


def read_cached(work, subjects, requested):
    cache = {}
    for path in sorted((work / "verified_inputs").glob("*/private_provenance.json")):
        data = load_json(path)
        key = (data.get("seed"), data.get("cope"))
        if key not in requested or data.get("model_commit") != MODEL:
            continue
        records = data.get("participants", [])
        paths = data.get("paths", [])
        if len(paths) != 28 or [row[0] for row in records] != subjects:
            continue
        if key_for([MODEL, key[0], key[1], records]) != data.get("source_signature"):
            continue
        valid = True
        for sub, source_files_row, file in zip(subjects, records, paths):
            target = Path(file).parent.parent
            expected = path.parent / "derivatives/fsl" / sub / l2_name(key[0]) / ("cope%d.feat" % key[1])
            if (
                target != expected
                or not usable_l2(target)
                or any(not (target / n).is_file() or sha(target / n) != h for n, h in source_files_row[2])
            ):
                valid = False
                break
        if not valid:
            continue
        insist(
            key not in cache,
            "More than one verified private input set for " + str(key) + ". Review private provenance.",
        )
        cache[key] = (paths, data["input_sources"], str(path))
    return cache


def prepare_inputs(project, work, *, jobs=2, dry_run=False, needed=None, source_roots=()):
    """Prepare the original fixed-effects inputs. Publishable fields are only status and counts."""
    project = Path(project).resolve()
    work = Path(work).expanduser().resolve()
    fsl = project / "derivatives/fsl"
    insist(
        work != project and work not in project.parents and fsl not in [work] + list(work.parents),
        "Private work must be outside the primary FSL data tree.",
    )
    if project in work.parents:
        allowed = project / "derivatives/jneurosci_cortical_reproduction"
        insist(
            allowed in work.parents or work == allowed,
            "Private work in project must use the dedicated reproduction tree.",
        )
    insist(
        not re.search(r"[^\w./+:-]", str(work)),
        "FSL needs a private output path without shell metacharacters or spaces.",
    )
    work.mkdir(parents=True, exist_ok=True, mode=0o700)
    requested = set(itertools.product(SEEDS, COPES) if needed is None else needed)
    insist(requested.issubset(set(itertools.product(SEEDS, COPES))), "Unknown seed/contrast request.")
    roots = [fsl] + [Path(p).expanduser().resolve() for p in (source_roots or ())]
    roots = list(
        dict.fromkeys(p for p in roots if p == fsl or p.is_dir() or (p.parent / "fmriprep").is_dir())
    )
    with (work / "staging.lock").open("a") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX)
        return _prepare_locked(project, work, max(1, int(jobs)), dry_run, requested, roots)


def _prepare_locked(project, work, jobs, dry, requested, roots):
    subs, runs, templates, masks, ev, launched, lengths = assets(project, work)
    cache = read_cached(work, subs, requested)
    active = requested - set(cache)
    errors = []
    outputs = {}
    lower = {}
    sources = {}
    missing_groups = set()
    runsets = {}
    source_qc = {}
    reasons = set()
    stage = {
        "configured_groups": len(requested),
        "cached_groups": len(cache),
        "archived_participant_contrasts": 0,
        "required_run_fits": 0,
        "required_participant_fits": 0,
        "reused_run_models": 0,
        "completed_run_fits": 0,
        "completed_participant_fits": 0,
        "completed_groups": len(cache),
    }
    for sub in subs:
        for seed, cope in sorted(active):
            rs = runs[sub]
            t = templates["L2_copes-19_runs-%d.fsf" % len(rs)]
            try:
                src = find_archived_l2(roots, sub, rs, seed, cope, t, launched)
            except (InputError, OSError, ValueError) as exc:
                missing_groups.add((seed, cope))
                errors.append(str(exc))
                continue
            if src:
                outputs[(sub, seed, cope)] = (src, "archived")
                stage["archived_participant_contrasts"] += 1
            else:
                runsets.setdefault((sub, seed), set()).add(cope)
    try:
        _, version = historical.fsl_runtime()
        insist((Path(os.environ["FSLDIR"]) / "bin/fslmeants").is_file(), "FSL fslmeants missing.")
    except (InputError, historical.Prerequisite, OSError) as exc:
        version = None
        if runsets:
            errors.append(str(exc))
            reasons.add("fsl_unavailable")
    for (sub, seed), copes in runsets.items():
        for r in sorted(runs[sub]):
            key = (sub, r, seed)
            try:
                src = find_archived_l1(
                    roots,
                    sub,
                    r,
                    seed,
                    copes,
                    templates["L1_template-m01_ppi.fsf"],
                    launched,
                    lengths[(sub, r)],
                )
                lower[key] = src
                if src is None:
                    # A shared BOLD is needed once for both seed models.
                    if (sub, r) not in sources:
                        flags = {}
                        source_qc[(sub, r)] = flags
                        try:
                            sources[(sub, r)] = source_files(roots, sub, r, ev, lengths[(sub, r)], flags)
                        except (InputError, OSError, ValueError) as exc:
                            flags["reason"] = getattr(exc, "category", "source_design_unverified")
                            reasons.add(flags["reason"])
                            sources[(sub, r)] = str(exc)
                    if isinstance(sources[(sub, r)], str):
                        raise InputError(sources[(sub, r)])
            except (InputError, OSError, ValueError) as exc:
                missing_groups.update((seed, c) for c in copes)
                errors.append(str(exc))
    stage.update(
        raw_runs_required=len(sources),
        timing_runs_verified=len(lengths),
        preprocessed_bold_verified=sum(
            bool(x.get("preprocessed_bold_verified")) for x in source_qc.values()
        ),
        confounds_verified=sum(bool(x.get("confounds_verified")) for x in source_qc.values()),
        usable_bold_and_confounds=sum(not isinstance(v, str) for v in sources.values()),
        missing_preprocessed_bold=sum(
            x.get("reason") == "missing_original_bold" for x in source_qc.values()
        ),
        missing_confounds=sum(x.get("reason") == "missing_original_confounds" for x in source_qc.values()),
        conflicting_source_runs=sum(x.get("reason") == "conflicting_inputs" for x in source_qc.values()),
        different_preprocessing_version_found=sum(
            bool(x.get("different_preprocessing_version_found")) for x in source_qc.values()
        ),
    )
    needed_groups = set(active) - missing_groups
    todo = {k: {c for c in cs if (k[1], c) in needed_groups} for k, cs in runsets.items()}
    todo = {k: cs for k, cs in todo.items() if cs}
    tasks = [(sub, r, seed) for sub, seed in todo for r in sorted(runs[sub])]
    stage["required_run_fits"] = sum(value is None for value in lower.values())
    stage["required_participant_fits"] = len(runsets)
    stage["launchable_run_fits"] = sum(lower[k] is None for k in tasks) if version else 0
    stage["launchable_participant_fits"] = len(todo) if version else 0
    stage["reused_run_models"] = sum(value is not None for value in lower.values())
    if not dry and todo and version:
        print(
            "Preparing %d run models and %d participant models with up to %d FEAT calls at once."
            % (stage["launchable_run_fits"], stage["launchable_participant_fits"], jobs),
            flush=True,
        )
        env = dict(os.environ, CARDGAME_FSL_VERSION=version)
        required_bold = sorted({(sub, r) for sub, r, seed in tasks if lower[(sub, r, seed)] is None})
        copies = parallel_tasks(
            required_bold, lambda k: prepare_bold(work, k[0], k[1], sources[k]), jobs, errors
        )
        valid = [k for k in tasks if lower[k] is not None or k[:2] in copies]

        def fit_run(k):
            return run_l1(
                work, k, todo[(k[0], k[2])], templates, masks, ev, copies.get(k[:2]), lower[k], env
            )

        completed = parallel_tasks(valid, fit_run, jobs, errors)
        stage["completed_run_fits"] = sum(v[1] == "reproduced" for v in completed.values())
        print("Verified %d/%d requested run inputs." % (len(completed), len(tasks)), flush=True)
        valid_keys = [k for k in todo if all((k[0], r, k[1]) in completed for r in runs[k[0]])]

        def fit_person(k):
            return run_l2(work, k[0], k[1], runs[k[0]], todo[k], templates, completed, env)

        combined = parallel_tasks(valid_keys, fit_person, jobs, errors)
        for (sub, seed), by_cope in combined.items():
            for cope, value in by_cope.items():
                outputs[(sub, seed, cope)] = (value, "reproduced")
        stage["completed_participant_fits"] = len(combined)
        print("Verified %d/%d new participant fits." % (len(combined), len(todo)), flush=True)
    if not dry:
        cache.update(exported_inputs(work, subs, active, outputs))
        stage["completed_groups"] = len(cache)
    ready = (not missing_groups and (not todo or version is not None)) if dry else set(cache) == requested
    status = (
        ("preflight_ready" if dry else "ready")
        if ready
        else ("missing_or_unverified_inputs" if missing_groups else "execution_incomplete")
    )
    seeds = {seed: {} for seed in SEEDS}
    provenance = {seed: {} for seed in SEEDS}
    manifests = {}
    for (seed, cope), (paths, classification, manifest) in cache.items():
        seeds[seed][str(cope)] = paths
        provenance[seed][str(cope)] = classification
        manifests[seed + "-" + str(cope)] = manifest
    if not ready and not reasons:
        reasons.add("source_design_unverified" if missing_groups else "lower_fit_failed")
    report = {
        "blocking_reasons": sorted(reasons),
        "ready": ready,
        "status": status,
        "counts": stage,
        "seeds": seeds,
        "source_provenance": provenance,
        "manifests": manifests,
        "work_project": str(work),
        "fsl_version": version,
        "errors": sorted(set(errors)),
    }
    json_save(work / ("private_preflight.json" if dry else "private_input_status.json"), report)
    return report
