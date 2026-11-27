#!/usr/bin/env python3
"""Locate the original task BOLD inputs on Linux1. --resume launches the unchanged
connectivity controller when source discovery can enable a group. The controller verifies each group independently.
The diagnostic reads source drives, keeps all path/participant information local,
and automatically exports aggregate counts to the dedicated source inventory.
"""
import argparse
from collections import Counter, defaultdict
import fcntl
import gzip
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import struct
import subprocess
import sys
import tempfile

import reproduce_jneurosci_cortical as control
import reproduce_jneurosci_cortical_inputs as inputs

TARGET = "MNI152NLin2009cAsym"
BASES = ("r21-cardgame", "ds.tacsCardGame", "klab/rutgers-r21", "rutgers-r21")
STUDY = re.compile(r"(r21[-_.]?cardgame|ds[._-]?tacscardgame|rutgers[-_.]?r21)", re.I)
VERSION = re.compile(r"^v?\d{1,2}\.\d{1,2}(?:\.\d{1,2})?$")
BOLD = re.compile(r"(sub-[^_]+)_(.*?)_bold\.nii(\.gz)?$")
PREFIX = "sub-"


def distinct(paths, directory=True):
    result = {}
    for p in paths:
        p = Path(p).expanduser()
        if not (p.is_dir() if directory else p.is_file()):
            continue
        st = p.stat()
        result.setdefault((st.st_dev, st.st_ino), p)
    return list(result.values())


def children(folder):
    try:
        return sorted(folder.iterdir()) if folder.is_dir() else []
    except (OSError, PermissionError):
        return []


def roots(project, extras):
    """List named studies only, including versioned wrappers and mounted backup study roots."""
    h = Path.home()
    studies = [project, h / "r21-cardgame", h / "work/r21-cardgame", h / "github/r21-cardgame"]
    mounts = [
        project.parent,
        Path("/ZPOOL/data"),
        Path("/data"),
        Path("/ZPOOL/data/projects"),
        Path("/data/projects"),
        Path("/mnt"),
        Path("/media"),
        Path("/backup"),
        Path("/backups"),
    ]
    # Dataset backup mounts are often one directory below /mnt or /media.
    mounts += [
        p
        for root in (Path("/mnt"), Path("/media"))
        for p in children(root)
        if p.is_dir() and re.search("backup|archive|san|zpool|rutgers|tuscan|lab", p.name, re.I)
    ]
    for base in distinct(mounts):
        for box in (
            base,
            base / "projects",
            base / "backup",
            base / "backups",
            base / "archive",
            base / "archives",
        ):
            studies += [box / n for n in BASES]
            studies += [p for p in children(box) if STUDY.search(p.name)]
    studies = distinct(studies)
    raw, deriv, archives = [], list(extras), []
    for p in studies:
        raw += [p, p / "bids", p / "sourcedata/bids", p / "sourcedata", p / "BIDS"]
        for base in (
            p,
            p / "bids",
            p / "sourcedata",
            p / "sourcedata/bids",
            p / "archive",
            p / "archives",
            p / "backup",
            p / "backups",
        ):
            archives += [
                f
                for v in [base, base / "derivatives"]
                for f in children(v)
                if f.is_file()
                and re.search(r"fmriprep|preproc|r21[-_.]?cardgame", f.name, re.I)
                and re.search(r"\.(?:zip|tar|tar\.gz|tgz|tar\.zst|tar\.xz)$", f.name, re.I)
            ]
            ds = [base / "derivatives"] + [
                v for v in children(base) if v.name.lower().startswith("derivatives")
            ]
            deriv += [v for v in children(base) if v.name.lower().startswith("fmriprep")]
            for d in distinct(ds):
                deriv += [d] + [
                    v for v in children(d) if v.name.lower().startswith(("fmriprep", "fmriprep-backup"))
                ]
    for f in control.archive_roots(project, []):
        deriv += [f.parent / "fmriprep"]
        deriv += [v for v in children(f.parent) if v.name.lower().startswith("fmriprep")]
    # Older images write an extra fmriprep/ inside the requested output directory.
    for d in distinct(deriv):
        deriv += [d / "fmriprep", d / "derivatives/fmriprep"]
        deriv += [
            v for v in children(d) if VERSION.fullmatch(v.name) or v.name.lower().startswith("fmriprep")
        ]
    return distinct(raw), distinct(deriv), distinct(archives, directory=False)


def design_inputs(project, runs):
    rows, evidence = defaultdict(set), defaultdict(set)
    fslroots = control.archive_roots(project, [])
    for f in fslroots:
        for sub, approved in runs.items():
            subject = f / sub
            for r in approved:
                for tag in {str(r), "%02d" % r}:
                    paths = list(
                        subject.glob("L1_%s_task-cardgame_model-01_seed-*_run-%s.fsf" % (sub, tag))
                    )
                    for name in (
                        "type-act",
                        "type-ppi_seed-rightVS",
                        "type-ppi_seed-interactionC4",
                        "type-ppi_seed-interactionC5",
                    ):
                        paths += list(
                            subject.glob(
                                "L1_task-cardgame_model-01_%s_run-%s_sm-6*.feat/design.fsf" % (name, tag)
                            )
                        )
                    for p in paths:
                        raw = inputs.historical.fsf(p)
                        for rhs in re.findall(r'^set feat_files\(1\)\s+"([^"]+)"', raw, re.M):
                            v = Path(rhs)
                            if v.is_absolute() and v.parent.name == "func" and v.name.startswith(sub + "_"):
                                rows[(sub, r)].add(str(v))
                                cfg = control.hist.configs(raw)
                                if p.parent.name.endswith(".feat"):
                                    out = p.parent
                                else:
                                    name = Path(cfg.get("outputdir", "")).name
                                    out = subject / (name if name.endswith(".feat") else name + ".feat")
                                old = control.hist.dated_november_fit(out / "report.html")
                                npts = cfg.get("npts", "")
                                for nuisance in re.findall(
                                    r'^set confoundev_files\(1\)\s+"([^"]+)"', raw, re.M
                                ):
                                    q = Path(nuisance)
                                    if (
                                        q.is_absolute()
                                        and q.parent.name == sub
                                        and re.fullmatch(
                                            re.escape(sub)
                                            + r"_task-cardgame_run-0*"
                                            + str(r)
                                            + r"_desc-fslConfounds\.tsv",
                                            q.name,
                                        )
                                    ):
                                        evidence[(sub, r)].add((str(p), str(v), str(q), npts, old))
    return rows, evidence, fslroots


def header(p, expected=None):
    opener = gzip.open if p.name.endswith(".gz") else open
    try:
        with opener(str(p), "rb") as stream:
            h = stream.read(348)
        e = "<" if h[:4] == struct.pack("<i", 348) else ">"
        if len(h) != 348 or struct.unpack_from(e + "i", h)[0] != 348 or h[344:347] != b"n+1":
            return {"issue": "invalid_nifti_header"}
        dim = struct.unpack_from(e + "8h", h, 40)
        tr = struct.unpack_from(e + "f", h, 92)[0] * {8: 1, 16: 0.001, 24: 0.000001}.get(h[123] & 56, 1.0)
        sform = struct.unpack_from(e + "h", h, 254)[0]
        aff = struct.unpack_from(e + "12f", h, 280)
        if not math.isfinite(tr) or not all(map(math.isfinite, aff)):
            return {"issue": "nonfinite_header"}
        issues = []
        if dim[0] != 4 or dim[4] <= 1:
            issues.append("not_timeseries")
        if expected is not None and dim[4] != expected:
            issues.append("volume_count")
        if abs(tr - 2.0) >= 0.001:
            issues.append("TR")
        geometry, displacement = inputs.source_geometry(h)
        if geometry not in {"exact_sform", "equivalent_qform_only", "equivalent_roundoff"}:
            issues.append(geometry)
        return {
            "issue": "+".join(issues) or "header_matches",
            "shape": list(dim[1:5]),
            "expected_volumes": expected,
            "TR_seconds": round(tr, 6),
            "sform_code": sform,
            "sform": list(aff),
            "source_geometry": geometry,
            "max_corner_displacement_mm": displacement,
        }
    except (OSError, ValueError, struct.error, EOFError):
        return {"issue": "unreadable_nifti"}


def entities(p):
    m = BOLD.fullmatch(p.name)
    if not m:
        return {}
    parts = [s.split("-", 1) for s in m[2].split("_")]
    if any(len(v) != 2 for v in parts):
        return {}
    return dict(parts, sub=m[1])


def func_dirs(root, sub):
    return distinct([root / sub / "func"] + list((root / sub).glob("ses-*/func")))


def candidate_ok(e, sub, run):
    # Additional session/resolution entities are inspected, but any change in
    # acquisition/pipeline identity requires confirmation from the original design.
    try:
        return e.get("sub") == sub and int(e.get("run", "-1")) == run and e.get("task") == "cardgame"
    except ValueError:
        return False


def add_link(source, target):
    if not source.is_file():
        return
    target.parent.mkdir(parents=True, exist_ok=True)
    if not target.exists():
        target.symlink_to(source.resolve())


def dataset_for_design(image):
    for p in image.parents:
        if p.name.startswith("sub-"):
            return p.parent
    return None


def cached_issue_counts(work):
    prior = inputs.load_json(work / "local_inputs/private_input_status.json")
    counts = prior.get("counts", {})
    return {
        k: counts[k]
        for k in (
            "missing_preprocessed_bold",
            "preprocessed_bold_verified",
            "usable_bold_and_confounds",
            "different_preprocessing_version_found",
        )
        if type(counts.get(k)) is int
    }


def raw_inventory(raw, lengths):
    result = {}
    for sub, run in lengths:
        for d in raw:
            for f in func_dirs(d, sub):
                for p in f.glob(sub + "_*task-cardgame*bold.nii*"):
                    e = entities(p)
                    if candidate_ok(e, sub, run) and not any(k in e for k in ("space", "desc")):
                        rec = header(p, lengths[(sub, run)])
                        if (
                            "shape" in rec
                            and rec["shape"][3] == lengths[(sub, run)]
                            and rec["TR_seconds"] == 2.0
                        ):
                            result.setdefault((sub, run), set()).add(str(p))
    return result


def workflow_cache(lengths):
    # The 20.1.0 wrapper mounted /data/scratch/$USER. Count potential retained
    # MNI preprocessing intermediates separately, without staging intermediates
    # as final derivative files or running container preprocessing.
    h = Path.home()
    users = {h.name, os.environ.get("USER", h.name), "dsmith"}
    starts = [h / "scratch/fmriprep"] + [
        root / u
        for root in (Path("/data/scratch"), Path("/ZPOOL/data/scratch"))
        for u in users
        if re.fullmatch(r"[A-Za-z0-9._-]+", u)
    ]
    seen = set()
    for d in distinct(starts):
        workflows = distinct(
            [d / "fmriprep_wf"] + list(d.glob("fmriprep*_wf")) + list(d.glob("fmriprep*/fmriprep*_wf"))
        )
        for w in workflows:
            for sub, r in lengths:
                subdir = w / ("single_subject_%s_wf" % sub[4:])
                for runwf in subdir.glob("*task_cardgame*run*wf"):
                    if not re.search(r"run_?0*%d(?:_|$)" % r, runwf.name):
                        continue
                    for p in runwf.glob("bold_std_trans_wf/*/merge*/vol*merged.nii*"):
                        if p.is_file():
                            seen.add((sub, r, str(p)))
                    for p in runwf.glob("bold_std_trans_wf/merge*/vol*merged.nii*"):
                        if p.is_file():
                            seen.add((sub, r, str(p)))
    return sorted(seen)


def original_raw_checksums(project, keys):
    meta = {}
    for sub, r in keys:
        fname = "%s_task-cardgame_run-%02d_bold.json" % (sub, r)
        path = "derivatives/mriqc/%s/func/%s" % (sub, fname)
        doc = json.loads(inputs.binary(project, inputs.MODEL, path))
        meta[(sub, r)] = (int(doc["size_t"]), int(doc["dummy_trs"]), doc["provenance"]["md5sum"])
    return meta


def md5(path):
    h = hashlib.md5()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(2**20), b""):
            h.update(block)
    return h.hexdigest()


def store_gzip(source, folder):
    # This is a container change only. Verify the complete decoded NIfTI bytes
    # both on first write and when an earlier private packed source is reused.
    folder.mkdir(parents=True, exist_ok=True)
    expected = inputs.sha(source)
    dest = folder / (expected + ".nii.gz")

    def decoded_hash(candidate):
        h = hashlib.sha256()
        with gzip.open(str(candidate), "rb") as f:
            for chunk in iter(lambda: f.read(2**20), b""):
                h.update(chunk)
        return h.hexdigest()

    if dest.is_file() and decoded_hash(dest) == expected:
        return dest
    with tempfile.NamedTemporaryFile(dir=str(folder), delete=False) as tmp:
        temp = Path(tmp.name)
        try:
            with source.open("rb") as raw, gzip.GzipFile(
                filename="", mode="wb", fileobj=tmp, mtime=0, compresslevel=1
            ) as output:
                shutil.copyfileobj(raw, output, 1024 * 1024)
            tmp.flush()
            if decoded_hash(temp) != expected:
                raise ValueError("lossless packaging did not verify for " + str(source))
            os.replace(str(temp), str(dest))
        finally:
            if temp.exists():
                temp.unlink()
    return dest


def link_candidate(local, root_id, sub, run, p, payload, deriv, func):
    base = local / root_id / "derivatives"
    new = base / "fmriprep" / sub / "func"
    stem = "%s_task-cardgame_run-%d_" % (sub, run)
    add_link(deriv / "dataset_description.json", base / "fmriprep/dataset_description.json")
    add_link(deriv / (sub + ".html"), base / "fmriprep" / (sub + ".html"))
    add_link(payload, new / (stem + "space-" + TARGET + "_desc-preproc_bold.nii.gz"))
    # Never collapse multiple nuisance candidates into a single apparent source.
    # Link the nuisance with the exact acquisition entities used in the derivative.
    prefix = p.name.split("_space-", 1)[0]
    for suffix in ("desc-confounds_regressors.tsv", "desc-confounds_timeseries.tsv"):
        for s in [prefix, sub + "_task-cardgame_run-" + str(run), sub + "_task-cardgame_run-%02d" % run]:
            q = func / (s + "_" + suffix)
            if q.is_file():
                add_link(q, new / (stem + suffix))
                break
    fs = base / "fsl"
    fs.mkdir(exist_ok=True)
    original_fsl = deriv.parent / "fsl"
    if original_fsl.is_dir():
        conf = original_fsl / "confounds"
        if conf.is_dir() and not (fs / "confounds").exists():
            (fs / "confounds").symlink_to(conf.resolve(), target_is_directory=True)
        # Only the dated source-design fallback needs the corresponding first-level design.
        subfolder = original_fsl / sub
        if subfolder.is_dir() and not (fs / sub).exists():
            (fs / sub).symlink_to(subfolder.resolve(), target_is_directory=True)
    return fs


def inspect(project, folder, extras):
    _, runs, _, _, events, _, lengths = inputs.assets(project, folder)
    meta = original_raw_checksums(project, lengths)
    refs, design_evidence, fslroots = design_inputs(project, runs)
    raw, derivs, archives = roots(project, extras)
    for values in refs.values():
        for value in values:
            d = dataset_for_design(Path(value))
            if d is not None:
                derivs.append(d)
                if str(d).startswith("/data/"):
                    derivs.append(Path("/ZPOOL") / d.relative_to("/"))
                if str(d).startswith("/ZPOOL/data/"):
                    derivs.append(Path("/") / d.relative_to("/ZPOOL"))
    derivs = distinct(derivs)
    derivatives = defaultdict(list)
    aliases = set()
    kinds = defaultdict(set)
    header_issues = Counter()
    volumes = Counter()
    print("Checking raw BIDS files and historical checksums, then the named fMRIPrep outputs.", flush=True)
    raw_paths = raw_inventory(raw, lengths)
    raw_exact = set()
    small_files = {}
    for k, paths in raw_paths.items():
        for name in paths:
            q = Path(name)
            s = q.stat()
            identity = (s.st_dev, s.st_ino)
            if identity not in small_files:
                small_files[identity] = md5(q)
            if small_files[identity] == meta[k][2]:
                raw_exact.add(k)
    for ordinal, deriv in enumerate(derivs):
        for sub, rs in runs.items():
            for func in func_dirs(deriv, sub):
                for p in func.glob(sub + "_*task-cardgame*bold.nii*"):
                    e = entities(p)
                    for r in rs:
                        if not candidate_ok(e, sub, r):
                            continue
                        k = (sub, r)
                        if not (e.get("desc") or e.get("space")):
                            continue
                        if p.is_symlink() and not p.is_file():
                            kinds["broken_derivative_link"].add(k)
                            continue
                        if not p.is_file():
                            continue
                        if e.get("space") != TARGET or e.get("desc") != "preproc":
                            kinds["other_space_or_preprocessing_description"].add(k)
                            continue
                        # A canonical matching image can be connected by 20.1.0 provenance
                        # and the identical study grid. Additional non-layout BIDS entities
                        # require an original design that points to this exact file.
                        design_reference = any(
                            Path(v).is_file() and os.path.samefile(v, p) for v in refs.get(k, ())
                        )
                        variant = set(e) - {"sub", "ses", "run", "task", "res", "desc", "space"}
                        version = inputs.original_preprocessing(deriv, sub, p, r, deriv.parent / "fsl")
                        hdr = header(p, lengths[k])
                        record = {
                            "path": str(p),
                            "dataset": str(deriv),
                            "version_check": version,
                            "original_design_points_here": design_reference,
                            "header": hdr,
                        }
                        derivatives[k].append(record)
                        kinds[
                            {
                                "verified": "verified_original_provenance",
                                "different_version": "different_fmriprep_version",
                                "unknown": "preprocessing_provenance_unknown",
                            }[version]
                        ].add(k)
                        if version != "verified":
                            continue
                        header_issues[hdr["issue"]] += 1
                        if "shape" in hdr:
                            n = hdr["shape"][3]
                            size, dummy, _ = meta[k]
                            volumes[
                                (
                                    "matches_both"
                                    if n == size == size + dummy
                                    else (
                                        "matches_size_plus_dummy_only"
                                        if n == size + dummy
                                        else "matches_size_only" if n == size else "matches_neither"
                                    )
                                )
                            ] += 1
                        if variant and not design_reference:
                            kinds["unbound_acquisition_variant"].add(k)
                            continue
                        if hdr["issue"] != "header_matches":
                            kinds["BOLD_header_or_run_length_rejected"].add(k)
                            continue
                        payload = p
                        if not p.name.endswith(".gz"):
                            payload = store_gzip(p, folder.parent / "packed_sources")
                            kinds["losslessly_packaged_original"].add(k)
                        if inputs.grid(payload, True) != lengths[k]:
                            kinds["data_payload_validation_failed"].add(k)
                            continue
                        # Per-dataset and session/variant private paths prevent replacement of
                        # a competing input. The existing controller resolves source conflicts.
                        identity = hashlib.sha256(str(p.parent).replace(sub, "{SUB}").encode()).hexdigest()[
                            :16
                        ]
                        # Preserve literal run padding and BIDS variants; competing
                        # streams cannot silently overwrite an existing alias.
                        variant_pattern = re.sub(
                            r"run-([0-9]+)",
                            lambda m: "runwidth-" + str(len(m[1])),
                            p.name.replace(sub, "{SUB}"),
                        )
                        variant_id = hashlib.sha256(variant_pattern.encode()).hexdigest()[:12]
                        fs = link_candidate(
                            folder / "aliases",
                            "d%d-%s-%s" % (ordinal, identity, variant_id),
                            sub,
                            r,
                            p,
                            payload,
                            deriv,
                            func,
                        )
                        aliases.add(fs)
    historical_extra = set(distinct([d.parent / "fsl" for d in derivs])) - set(fslroots)
    # Only a completed November design with this subject, run and full npts
    # can supply an otherwise relocated final FSL nuisance matrix.
    proven = defaultdict(set)
    for (sub, r), items in design_evidence.items():
        for _, source, text, npts, november in items:
            if not november or npts != str(lengths[(sub, r)]):
                continue
            if (
                not candidate_ok(entities(Path(source)), sub, r)
                or "space-" + TARGET + "_desc-preproc_bold" not in Path(source).name
            ):
                continue
            targets = [Path(text)]
            if text.startswith("/data/"):
                targets.append(Path("/ZPOOL") / Path(text).relative_to("/"))
            if text.startswith("/ZPOOL/data/"):
                targets.append(Path("/") / Path(text).relative_to("/ZPOOL"))
            for q in distinct(targets, directory=False):
                proven[(sub, r)].add(q)
                token = hashlib.sha256(str(q).encode()).hexdigest()[:20]
                fs = folder / "nuisance" / token / "derivatives/fsl"
                add_link(
                    q, fs / "confounds" / sub / ("%s_task-cardgame_run-%d_desc-fslConfounds.tsv" % (sub, r))
                )
                aliases.add(fs)
    allroots = list(sorted(aliases | historical_extra)) + fslroots
    verified = set()
    failure = Counter()
    conflicting_nuisance = set()
    run_records = []
    for k, n in lengths.items():
        try:
            _, _, model_matrix, _ = inputs.source_files(allroots, k[0], k[1], events, n, {})
            for q in proven[k]:
                a = [line.split() for line in model_matrix.splitlines()]
                b = [line.split() for line in inputs.confounds(None, q, n).splitlines()]
                if len(a) != len(b) or any(
                    len(x) != len(y)
                    or any(
                        not math.isclose(float(v), float(w), rel_tol=1e-9, abs_tol=1e-12)
                        for v, w in zip(x, y)
                    )
                    for x, y in zip(a, b)
                ):
                    conflicting_nuisance.add(k)
                    raise inputs.InputError(
                        "saved and original design nuisance disagree", "conflicting_inputs"
                    )
            verified.add(k)
        except (inputs.InputError, ValueError, KeyError, OSError) as exc:
            category = getattr(exc, "category", "source_design_unverified")
            if category not in control.LOWER_REASONS:
                category = "source_design_unverified"
            failure[category] += 1
        run_records.append(
            {
                "participant": k[0],
                "run": k[1],
                "expected_full_volumes": n,
                "MRIQC_size_t": meta[k][0],
                "MRIQC_dummy_trs": meta[k][1],
                "source_design_nuisance_and_npts": sorted(design_evidence.get(k, [])),
                "raw_files": sorted(raw_paths.get(k, [])),
                "raw_MRIQC_md5_match": k in raw_exact,
                "design_source_paths": sorted(refs.get(k, [])),
                "preprocessed": derivatives.get(k, []),
            }
        )
    scratch = workflow_cache(lengths)
    local = {
        "runs": run_records,
        "candidate_derivative_roots": list(map(str, derivs)),
        "candidate_raw_roots": list(map(str, raw)),
        "private_aliases_for_controller": list(map(str, sorted(aliases))),
        "workflow_intermediates": scratch,
        "named_project_archives_not_opened": list(map(str, archives)),
    }
    control.write_json(folder / "sources_private.json", local)
    prior = cached_issue_counts(project / control.SUBDIR)
    anatomy = set()
    fieldmaps = set()
    for base in raw:
        for sub in runs:
            for level in [base / sub] + list((base / sub).glob("ses-*")):
                for modality, pattern, observed in (
                    ("anat", "*_T1w.nii*", anatomy),
                    ("fmap", "*.nii*", fieldmaps),
                ):
                    if sub not in observed and any(
                        "shape" in header(p) for p in (level / modality).glob(pattern)
                    ):
                        observed.add(sub)
    containers = [
        Path(base) / "fmriprep-20.1.0.simg"
        for base in ("/data/tools", "/ZPOOL/data/tools", str(Path.home() / "work/tools"))
    ]
    public = {
        "n_participants": len(runs),
        "n_required_runs": len(lengths),
        "earlier_source_counts": prior,
        "raw_runs_with_matching_acquisition_length_and_TR": len(raw_paths),
        "raw_byte_identical_to_MRIQC": len(raw_exact),
        "participants_with_readable_raw_T1w": len(anatomy),
        "participants_with_readable_raw_fieldmap_images": len(fieldmaps),
        "named_historical_container_file_present": any(
            p.is_file() and p.stat().st_size > 0 for p in containers
        ),
        "runs_with_nuisance_target_from_dated_original_design": sum(bool(v) for v in proven.values()),
        "runs_with_inconsistent_dated_nuisance_matrix": len(conflicting_nuisance),
        "runs_with_saved_original_design_path": sum(bool(refs.get(k)) for k in lengths),
        "runs_with_dated_design_full_length_confirmed": sum(
            any(old and n == str(lengths[k]) for _, _, _, n, old in design_evidence.get(k, ()))
            for k in lengths
        ),
        "runs_with_dated_design_length_disagreement": sum(
            any(
                old and n.isdigit() and int(n) != lengths[k]
                for _, _, _, n, old in design_evidence.get(k, ())
            )
            for k in lengths
        ),
        "runs_with_existing_design_target": sum(
            any(Path(p).is_file() for p in refs.get(k, ())) for k in lengths
        ),
        "runs_with_preprocessed_2009cAsym_candidates": len(derivatives),
        "run_counts_by_source_class": {k: len(v) for k, v in sorted(kinds.items())},
        "candidate_file_header_issues_with_original_provenance": dict(header_issues),
        "candidate_file_length_vs_MRIQC": dict(volumes),
        "candidate_geometry_for_original_provenance": dict(
            Counter(
                item["header"].get("source_geometry", "unreadable")
                for stream in derivatives.values()
                for item in stream
                if item["version_check"] == "verified"
            )
        ),
        "runs_with_possible_standard_space_workflow_intermediate": len({(a, b) for a, b, _ in scratch}),
        "named_project_archives_not_opened": len(archives),
        "runs_with_verified_BOLD_and_nuisance": len(verified),
        "remaining_run_blockers": dict(failure),
        "all_79_source_pairs_verified": len(verified) == len(lengths),
    }
    public["new_historical_FSL_roots"] = len(historical_extra)
    public["controller_recheck_warranted"] = bool(verified or historical_extra) and not conflicting_nuisance
    return public, aliases | historical_extra


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--project", type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument(
        "--source-root",
        type=Path,
        action="append",
        default=[],
        help="additional known fMRIPrep output directory",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="resume independently eligible group fits via the original controller",
    )
    parser.add_argument(
        "--local-only",
        action="store_true",
        help="save the inventory without Git publication or launching FEAT",
    )
    args = parser.parse_args()
    os.umask(0o077)
    project = args.project.expanduser().resolve()
    root = project / control.SUBDIR / "source_locator"
    root.mkdir(parents=True, exist_ok=True)
    with (root / "locator.lock").open("a") as f:
        try:
            fcntl.flock(f, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            print("Source locator already active.")
            return 0
        folder = Path(tempfile.mkdtemp(prefix="inventory-", dir=str(root)))
        print("Checking historical BOLD source paths. Private report directory: " + str(folder), flush=True)
        public, aliases = inspect(project, folder, args.source_root)
        control.write_json(folder / "sources_aggregate.json", public)
        print(json.dumps(public, indent=2, sort_keys=True), flush=True)
        if not args.local_only:
            control.git_publish(project, control.SOURCE_INVENTORY, public)
        if public["controller_recheck_warranted"] and args.resume and not args.local_only:
            cmd = [
                sys.executable,
                "-u",
                str(Path(__file__).resolve().with_name("reproduce_jneurosci_cortical.py")),
                "--project",
                str(project),
            ]
            for alias in sorted(aliases):
                cmd += ["--archive-fsl", str(alias)]
            return subprocess.run(cmd).returncode
        return 0 if public["all_79_source_pairs_verified"] else 3


if __name__ == "__main__":
    sys.exit(main())
