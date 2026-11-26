"""Build a public, aggregate-only result from a private CardGame FEAT retrieval report."""
import csv
import gzip
import hashlib
import json
import math
from pathlib import Path
import re
import array
import sys
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
                get("mixed_yn") == 1 and get("robust_yn") == 0 and get("thresh") == 3 and z == 3.1 and p == .05 and whole)
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


# Read-only discovery of archived cortical products and lower-level readiness.
TARGET = 'L3_model-01_task-cardgame_n28_FLAME1+2'
COHORT_HASH = 'd768be3b713b38c54473714cc4302105cc08172f6111c9dc5f6dc1d7dfa6f44d'
CONTRAST = {16: 'ppi_vlpfc-tpj', 17: 'ppi_R_vlpfc-tpj', 18: 'ppi_P_vlpfc-tpj', 19: 'ppi_interaction'}
SIDES = {'interactionC4':'left VLPFC', 'interactionC5':'right VLPFC'}

def _rows(path):
    if not path.is_file():
        return []
    with path.open(encoding='utf-8-sig',newline='') as source:
        return list(csv.DictReader(source,delimiter='\t'))

def _project(report):
    candidates = []
    for env_key in ('CARDGAME_PROJECT',):
        if os.environ.get(env_key):
            candidates.append(Path(os.environ[env_key]))
    for file, key in (('manifest.tsv','source'),('group_inputs.tsv','input_path')):
        for row in _rows(report/file):
            p = Path(row.get(key,''))
            for parent in p.parents:
                if parent.name in ('derivatives','masks','code','templates','logs'):
                    candidates.append(parent.parent)
                    break
    for candidate in dict.fromkeys(candidates):
        if (candidate/'derivatives/fsl').is_dir():
            return candidate.resolve()
    return None

def _fsf(path):
    return path.read_text(errors='replace') if path.is_file() else ''

def _inputs(text):
    return re.findall(r'^set feat_files\((\d+)\)\s+"([^"]+)"', text, flags=re.M)

def _verified_roster(project):
    qc = _rows(project/'derivatives/mriqc-extractions/outliers_task-cardgame_runinfo.tsv')
    runs = {}
    for row in qc:
        if row.get('outlier_run_Custom1','').strip().lower()=='false':
            runs.setdefault(row['Sub'],set()).add(int(row['run']))
    runs = {sub:rs for sub,rs in runs.items() if len(rs)>=2}
    if hashlib.sha256(('\n'.join(sorted(runs))+'\n').encode()).hexdigest()!=COHORT_HASH:
        return {}
    return runs

def _group_candidates(fsl,diag):
    roots = [fsl]
    roots.extend(p for p in fsl.parent.glob('fsl*') if p.is_dir() and p!=fsl)
    visited = set()
    for base in roots:
        for name,children,_ in os.walk(str(base),followlinks=False):
            p = Path(name)
            if len(p.relative_to(base).parts)>7:
                children[:] = []
                continue
            keep = []
            for child in sorted(children):
                c = p/child
                s = child.lower()
                if '.gfeat' in s and ('l3' in s or 'l3' in p.name.lower()):
                    if c.resolve() in visited:
                        continue
                    visited.add(c.resolve())
                    if not any(k in s for k in ('interactionc4','interactionc5','vlpfc')):
                        continue
                    if not any(k in s for k in ('ppi_seed','type-ppi','ppi-seed')):
                        continue
                    if not re.search(r'c(?:num|openum|ope)[-_]?(?:16|17|18|19)(?:[^0-9]|$)',s):
                        continue
                    yield c
                elif not (s.startswith(('sub-','.')) or '.feat' in s or '.gfeat' in s or
                          s in ('evfiles','confounds','singletrial','regressors')):
                    keep.append(child)
            children[:] = keep
            # The original collector requires an exact L3 parent and unmodified .gfeat suffix.
            # Count surviving adjacent designs even when FEAT did not leave a group directory.
            for side in SIDES:
                for cope in (16,19):
                    pat = '*'+side+'*copenum-'+str(cope)+'*onegroup.fsf'
                    diag[SIDES[side]][str(cope)]['adjacent_group_designs'] += sum(1 for v in p.glob(pat) if v.is_file())

def _counts(fsl, roster, side, cope):
    out = dict(L2_participants_with_cope_varcope=0,L2_participants_with_DOF=0,
               L2_participants_with_matching_run_design=0,L1_runs_with_cope_varcope=0,
               L1_runs_with_archived_seed_design=0,L1_runs_with_cope_varcope_and_DOF=0)
    for sub,runs in roster.items():
        folder=fsl/sub
        l2=folder/('L2_task-cardgame_model-01_type-ppi_seed-'+side+'_sm-6.gfeat')
        cdir=l2/('cope%d.feat'%cope)/'stats'
        paired=all((cdir/(var+'1.nii.gz')).is_file() for var in ('cope','varcope'))
        out['L2_participants_with_cope_varcope']+=int(paired)
        out['L2_participants_with_DOF']+=int(paired and (cdir/'tdof_t1.nii.gz').is_file())
        fsf=_fsf(l2/'design.fsf') or _fsf(folder/('L2_task-cardgame_model-01_type-ppi_seed-'+side+'.fsf'))
        inp=_inputs(fsf);rx=r'/'+re.escape(sub)+r'/L1_task-cardgame_model-01_type-ppi_seed-'+side+r'_run-(\d+)_sm-6[+]*\.feat(?:/|$)'
        rs=[re.search(rx,path) for _,path in inp]
        matches=(len(rs)==len(runs) and all(rs) and set(int(m.group(1)) for m in rs)==runs)
        out['L2_participants_with_matching_run_design']+=int(paired and matches)
        for run in runs:
            pat='L1_task-cardgame_model-01_type-ppi_seed-%s_run-%02d_sm-6.feat'%(side,run)
            l1=folder/pat; stats=l1/'stats'
            ok=all((stats/('%s%d.nii.gz'%(var,cope))).is_file() for var in ('cope','varcope'))
            out['L1_runs_with_cope_varcope']+=int(ok)
            fsf=_fsf(l1/'design.fsf') or _fsf(folder/('L1_'+sub+'_task-cardgame_model-01_seed-%s_run-%02d.fsf'%(side,run)))
            signal=bool(re.search(r'^set fmri\(custom5\)\s+"[^"]*/ts_task-cardgame_mask-'+side+r'_run-%02d\.txt"'%run,fsf,flags=re.M))
            out['L1_runs_with_archived_seed_design']+=int(ok and signal)
            out['L1_runs_with_cope_varcope_and_DOF']+=int(ok and (stats/'dof').is_file())
    return out

def _link(src, dst):
    if not src.is_file():
        return False
    dst.symlink_to(src.resolve())
    return True

def live_evidence(report, scratch):
    report=Path(report); scratch=Path(scratch)
    inventory=[];group_inputs=[]
    project=_project(report)
    if project is None:
        return inventory,group_inputs,{'project_located':False}
    fsl=project/'derivatives/fsl'
    runs=_verified_roster(project)
    diag={label:{str(cope):dict(adjacent_group_designs=0,group_directories=0,
                                matching_original_inputs=0,matched_candidate_outputs=0)
                 for cope in CONTRAST} for label in SIDES.values()}
    legacy=0;idx=900000
    for g in _group_candidates(fsl,diag):
        match=re.search(r'c(?:num|openum|ope)[-_]?(16|17|18|19)(?:[^0-9]|$)',g.name.lower())
        cope=int(match.group(1))
        fsf=g/'design.fsf'
        if not fsf.is_file():
            stem=re.sub(r'(?:\+*\.gfeat\+*)$','',g.name)
            items=list(g.parent.glob(stem+'.fsf'))
            items.extend(g.parent.glob(re.split(r'_cnum-',stem)[0]+'_copenum-'+str(cope)+'_onegroup.fsf'))
            fsf=next((f for f in items if f.is_file()),fsf)
        raw=_fsf(fsf); inp=_inputs(raw)
        side=next((k for k in SIDES if k.lower() in g.name.lower()),None)
        if side is None:
            # Legacy names alone cannot adjudicate which mask was actually used.
            for k in SIDES:
                if inp and all(re.search(r'/L2_task-cardgame_model-01_type-ppi_seed-'+k+
                                 r'_sm-6\+*\.gfeat\+*/cope'+str(cope)+r'\.feat/',p) for _,p in inp):
                    side=k;break
            if side is None:
                legacy+=1;continue
        rec=diag[SIDES[side]][str(cope)]
        rec['group_directories']+=1
        mapped=[]
        for seq,path in inp:
            m=re.search(r'/(sub-[A-Za-z0-9]+)/L2_task-cardgame_model-01_type-ppi_seed-'+side+
                r'_sm-6\+*\.gfeat\+*/cope(\d+)\.feat/stats/cope1\.nii(?:\.gz)?$',path)
            if not m or int(m.group(2))!=cope:break
            mapped.append([seq,m.group(1),m.group(2),path])
        if (len(mapped)!=28 or len(inp)!=28 or len(set(row[1] for row in mapped))!=28 or
            set(row[1] for row in mapped)!=set(runs)):continue
        # A matching path may also come from later covariate/outlier variants;
        # require the November one-group operating mode in addition to the
        # downstream roster, direction, threshold, seed and map validations.
        cfg=dict(re.findall(r'^set fmri\(([^)]+)\)\s+([^\n]+)',raw,flags=re.M))
        if any(cfg.get(key,'').strip() != val for key,val in
               [('robust_yn','0'),('evs_orig','1'),('npts','28'),('mixed_yn','1')]): continue
        rec['matching_original_inputs']+=1
        feat=g/'cope1.feat'
        if not feat.is_dir():continue
        idx+=1; model_id=str(idx);dest=scratch/'models'/model_id;dest.mkdir(parents=True,exist_ok=True)
        # A single source may already have been staged by a first attempt.
        def add(src,key):
            target=dest/key
            return (target.is_symlink() and target.resolve()==src.resolve() and src.is_file()) or _link(src,target)
        add(fsf,'group-design.fsf')
        for src,dst in ((g/'design.con','group-design.con'),(g/'design.mat','group-design.mat'),
                         (feat/'design.con','cope-design.con'),(feat/'design.mat','cope-design.mat'),
                         (feat/'mask.nii.gz','search-mask.nii.gz')):
            add(src,dst)
        for seq,sub,c,path in mapped:
            group_inputs.append(dict(id=model_id,row=seq,participant_code=sub,input_cope=c,input_path=path))
        for sign in (1,2):
            names=['cluster_zstat%d_std.txt'%sign,'cluster_zstat%d.txt'%sign,
                   'thresh_zstat%d.nii.gz'%sign,'cluster_mask_zstat%d.nii.gz'%sign]
            has=[add(feat/n,n) for n in names]
            # Known-compatible input directories may have backup suffixes or
            # different archive parents. Preserve their true paths in private
            # staging; consumers validate design/seed/threshold independently.
            inventory.append(dict(id=model_id,group_path=str(g),expected_model_parent='True',analysis='ppi_seed-'+side,cope=str(cope),
                name=CONTRAST[cope],group_zstat=str(sign),table_MNI_mm=str(has[0]),table_native=str(has[1]),
                thresholded_map=str(has[2]),read_status=('present; fslstats unavailable' if has[2] else 'missing'),
                range_min_max='',nonzero_voxels='',cluster_labels=str(has[3])))
        rec['matched_candidate_outputs']+=1
    for side,label in SIDES.items():
        for cope in (16,19):
            diag[label][str(cope)].update(_counts(fsl,runs,side,cope))
    return inventory,group_inputs,{'project_located':True,'submitted_cohort_size':len(runs),
        'eligible_runs':sum(map(len,runs.values())),'other_seed_name_candidates_without_matching_inputs':legacy,
        'cortical_evidence':diag}


# Original deposited NeuroVault thresholded arrays. Hash float32 voxels in NIfTI order,
# independently of gzip headers, file modification dates and NIfTI description fields.
REFERENCE_MAPS = {
    ("act", 5): (1, "bd37bac5274719248f19f21d8e6f835ac1327c3c4cc166768662f0f83324fd04"),
    ("act", 9): (1, "4730f25a572f30b113a9f27c6cbd619e1529d781d1d081fdf805797dac782fb8"),
    ("ppi_seed-rightVS", 19): (2, "301f37bae8d4257b35e403cbbb5bb86ecf4a30baccf2cad9bde1557117647dfe"),
}


def map_digest(path, submitted_grid=False):
    img = nifti(path)
    if img is None:
        return None
    values, shape, affine = img
    if submitted_grid and (shape != (65, 77, 65) or affine != GRID):
        return "different_grid"
    data = array.array("f", (0. if v == 0 else v for v in values))
    if sys.byteorder != "little":
        data.byteswap()
    h = hashlib.sha256()
    if not submitted_grid:
        h.update(repr((shape, affine)).encode("ascii"))
    h.update(data.tobytes())
    return h.hexdigest()


def path_class(raw):
    # The original collector stores paths relative to derivatives/fsl. Also accept an
    # absolute Linux1 path after stripping that explicit prefix, never just its basename.
    parts = Path(raw).parts
    if Path(raw).is_absolute():
        prefixes = [i for i in range(len(parts)-1) if parts[i:i+2] == ("derivatives", "fsl")]
        if not prefixes:
            return "other"
        parts = parts[prefixes[-1] + 2:]
    if len(parts) == 2 and parts[0] == TEMPLATE and parts[1].endswith(".gfeat") and "+" not in parts[1]:
        return "direct"
    return "archive" if TEMPLATE in parts[:-1] else "other"


def input_family(rows, kind, cope):
    pattern = r"(?:^|/)L2_task-cardgame_model-01_type-%s_sm-6\+*\.gfeat\+*/cope0*%d\.feat/stats/cope1\.nii(?:\.gz)?$"
    expected = re.compile(pattern % (re.escape(kind), cope))
    return bool(rows) and all(expected.search(row.get("input_path", "")) for row in rows)


def candidate(report_root, code, rows, inputs, kind, cope, seed_ok):
    folder = report_root / "models" / code
    design = design_info(folder, inputs, cope)
    family = input_family(inputs, kind, cope)
    ref = REFERENCE_MAPS.get((kind, cope))
    reference_match = None
    if ref:
        checksum = map_digest(folder / ("thresh_zstat%d.nii.gz" % ref[0]), submitted_grid=True)
        reference_match = checksum == ref[1] if checksum is not None else None
    eligible = design["design_verified"] and family and seed_ok and (ref is None or reference_match is True)
    signs = [sign_info(folder, sign, eligible, next((r for r in rows if r["group_zstat"] == str(sign)), None))
             for sign in (1, 2)]
    return {"folder": folder, "source": path_class(rows[0]["group_path"]), "design": design, "family": family,
            "match": reference_match, "eligible": eligible, "signs": signs}


def full_record(c):
    return all(s["status"] in ("clusters_reported", "no_surviving_clusters") for s in c["signs"])


def equivalent_evidence(records):
    # Two group runs may share filenames. Compare underlying arrays, geometry and p values.
    # An incomplete archive may supply the same maps as a complete copy but lacks a table.
    for i in range(2):
        digests = {map_digest(c["folder"] / ("thresh_zstat%d.nii.gz" % (i+1))) for c in records}
        digests.discard(None)
        if len(digests) > 1:
            return False
        reported = set()
        for c in records:
            sign = c["signs"][i]
            if sign["cluster_table_readable"]:
                reported.add(tuple(sorted((r["cluster_index"], r["voxels"], r["cluster_corrected_p"])
                                          for r in (sign["clusters"] or []))))
        if len(reported) > 1:
            return False
    return True


def select_candidate(records):
    eligible = [c for c in records if c["eligible"] and not any(
        s["status"] == "conflicting_outputs" for s in c["signs"])]
    direct = [c for c in eligible if c["source"] == "direct"]
    if len(eligible) == 1:
        if direct:
            return eligible[0], "verified_direct_original"
        return eligible[0], "verified_inputs_and_map" if eligible[0]["match"] else "verified_inputs_and_seed"
    if eligible and equivalent_evidence(eligible):
        return max(eligible, key=lambda c: (full_record(c), sum(s["cluster_table_readable"] for s in c["signs"]),
                                            c["source"] == "direct")), "consistent_result_copies"
    # Keep a single incomplete candidate visible for diagnostics; its verified status stays false.
    if len(records) == 1 and not eligible:
        return records[0], "candidate_unverified"
    return None, "candidates_disagree" if eligible else ("no_verified_candidate" if records else "no_candidate")


REPRO_TEMPLATE = "ffc31bd1507a38152e6284f83f74cbd1ba2b84c08c21e043cc73c66985c63c84"


def finished_report(path):
    if not path.is_file():
        return False
    text = path.read_text(errors="replace").lower()
    return ("finished at" in text and "fatal error" not in text and
            "errors occured during the analysis" not in text and "errors occurred during the analysis" not in text)


def verified_reproduction(record, marks, label, cope):
    if len(marks) != 1 or label not in ("left VLPFC","right VLPFC") or cope not in (16,19):
        return None
    mark = marks[0]
    folder = record["folder"]
    if (not record["reproduction_location"] or not record["eligible"] or not full_record(record) or
            mark.get("analysis") != label or mark.get("cope") != str(cope) or
            mark.get("template_sha256") != REPRO_TEMPLATE or
            not re.fullmatch(r"[0-9]{1,2}(?:\.[0-9]{1,3}){1,4}", mark.get("fsl_version","")) or
            not all(finished_report(folder/name) for name in ("group-report.html","cope-report.html"))):
        return None
    for sign, column in ((1,"positive_map_sha256"),(2,"negative_map_sha256")):
        declared = mark.get(column, "")
        if (not re.fullmatch(r"[0-9a-f]{64}", declared) or
                map_digest(folder / ("thresh_zstat%d.nii.gz"%sign)) != declared):
            return None
    return {"source_provenance":"historical_group_model_reproduced", "FSL_version":mark["fsl_version"],
            "original_template_commit":"33becdaa", "template_sha256":REPRO_TEMPLATE}


def keep_provenance(model, records, markers, label, cope):
    for sign in model["signs"]:
        sign["source_provenance"] = ("archived_group_output" if sign["status"] in
                ("clusters_reported","no_surviving_clusters","clusters_present_exact_p_unavailable")
                else "unresolved")
    model["source_provenance"] = ("archived_group_output" if any(s["source_provenance"] ==
            "archived_group_output" for s in model["signs"]) else "unresolved")
    if not records:
        return
    supported = []
    for record in records:
        meta = verified_reproduction(record, markers.get(record["private_index"],[]), label, cope)
        if meta:
            supported.append((record,meta))
    model["reproduction_candidates"] = len(records)
    model["verified_reproductions"] = len(supported)
    # Distinct new FEAT runs can differ slightly. Never silently pick one of multiple fits.
    if len(supported) != 1:
        return
    record,meta = supported[0]
    model["original_signed_status"] = [s["status"] for s in model["signs"]]
    replacement = [dict(s, source_provenance="historical_group_model_reproduced") for s in record["signs"]]
    missing = {"model_missing", "unverified_model", "incomplete_output"}
    replaced = [s["status"] in missing for s in model["signs"]]
    if all(replaced):
        model.update(meta, signs=replacement, model_available=True, design=record["design"],
                     L2_input_family_match=record["family"], candidate_resolution="verified_reproduction")
    elif any(replaced):
        model["signs"] = [r if flag else s for flag,r,s in zip(replaced,replacement,model["signs"])]
        model["source_provenance"] = "see_signed_result_provenance"
        model["reproduction"] = meta
    elif not all(s["status"] in ("clusters_reported","no_surviving_clusters") for s in model["signs"]):
        # Retain disagreements/incomplete archived p values. Report the reproduction separately.
        model["separate_reproduction"] = dict(meta, signs=replacement)


def resolve(inventory, inputs, report, folders):
    markers = {}
    for row in tsv(report / "reproduced_groups.tsv"):
        markers.setdefault(row.get("id",""),[]).append(row)
    seeds = {}
    for name, (named, fallback, identity) in SEEDS.items():
        base = report / "sources" / "masks"
        seeds[name] = {"named_seed": mask_summary(base / named, identity)}
        if fallback:
            seeds[name]["reference_cluster"] = mask_summary(base / fallback, identity)
    checks = [("act", 5, "R-P", "activation"), ("act", 9, "interaction", "activation"),
              ("ppi_seed-rightVS", 19, PPI[19], "right VS")]
    for alias, label in (("interactionC4", "left VLPFC"), ("interactionC5", "right VLPFC")):
        checks.extend(("ppi_seed-" + alias, c, PPI[c], label) for c in (16, 19, 17, 18))
    models = []
    for kind, cope, contrast, label in checks:
        seed_ok = True
        if label in seeds:
            s = seeds[label]
            available = s["named_seed"] if s["named_seed"]["available"] else s.get("reference_cluster", {})
            seed_ok = available.get("matches_reference") is True and s.get("reference_cluster", {}).get("matches_reference") is not False
        matched = [r for r in inventory if r.get("analysis","").lower() == kind.lower()
                   and r.get("cope") == str(cope) and r.get("name") == contrast
                   and re.fullmatch(r"\d+", r["id"])]
        ids = sorted({r["id"] for r in matched})
        records = [candidate(folders.get(code, report), code, [r for r in matched if r["id"] == code],
                             [r for r in inputs if r["id"] == code], kind, cope, seed_ok) for code in ids]
        reproduced = []
        archived = []
        for code, record in zip(ids, records):
            paths = [Path(r["group_path"]).parts for r in matched if r["id"] == code]
            record["private_index"] = code
            record["reproduction_location"] = all(len(q) == 3 and q[:2] == ("historical-reproduction", TEMPLATE)
                                                   for q in paths)
            synthetic = any("historical-reproduction" in q for q in paths)
            if code in markers or synthetic:
                reproduced.append(record)
            else:
                archived.append(record)
        records = archived
        selected, why = select_candidate(records)
        model = {"analysis": label, "cope": cope, "contrast": contrast, "model_available": selected is not None,
                 "candidate_resolution": why, "candidate_count": len(records),
                 "direct_candidates": sum(c["source"] == "direct" for c in records),
                 "design_input_matches": sum(c["family"] and c["design"]["design_verified"] for c in records)}
        if (kind, cope) in REFERENCE_MAPS:
            model["submitted_map_matches"] = sum(c["match"] is True for c in records)
        if label in seeds:
            model["seed_reference_verified"] = seed_ok
        if selected is not None:
            model.update({"design": selected["design"], "L2_input_family_match": selected["family"],
                          "signs": selected["signs"]})
        else:
            if records:
                model["candidate_evidence"] = [{"source_class": c["source"], "design_verified": c["design"]["design_verified"],
                    "submitted_map_match": c["match"], "input_family_match": c["family"],
                    "signs": c["signs"]} for c in records]
            why = "model_missing" if not records else "ambiguous_model"
            model["signs"] = [{"zstat": i, "status": why} for i in (1, 2)]
        keep_provenance(model, reproduced, markers, label, cope)
        models.append(model)
    return {"seeds": seeds, "models": models}


def group_summary(report: Path) -> dict:
    report = Path(report)
    inventory = tsv(report / "contrasts.tsv")
    inputs = tsv(report / "group_inputs.tsv")
    result = resolve(inventory, inputs, report, {})
    needs_live = any(m["analysis"] in ("left VLPFC", "right VLPFC") and m["cope"] in (16,19)
                     and any(s["status"] not in ("clusters_reported", "no_surviving_clusters") for s in m["signs"])
                     for m in result["models"])
    if needs_live:
        with tempfile.TemporaryDirectory() as temp:
            scratch = Path(temp)
            rows, group_inputs, diagnostics = live_evidence(report, scratch)
            if rows:
                roots = {row["id"]: scratch for row in rows}
                result = resolve(inventory + rows, inputs + group_inputs, report, roots)
            result["live_recovery"] = diagnostics
    return result


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
