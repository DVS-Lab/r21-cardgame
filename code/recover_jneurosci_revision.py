#!/usr/bin/env python3
"""Recover and publish existing results. --fit-missing additionally reproduces eligible historic L3s.

Private output and logs remain under the Linux user's home. Neither archived L1 nor L2 fits
are launched. FSL sees only private copies of its inputs.
"""
import argparse
import csv
import datetime
import fcntl
import hashlib
import gzip
import struct
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import time

import publish_jneurosci_revision as pub

TEMPLATE_SHA='ffc31bd1507a38152e6284f83f74cbd1ba2b84c08c21e043cc73c66985c63c84'
PUBLISHABLE={'clusters_reported','no_surviving_clusters'}
MODULE=Path(__file__).resolve().parent
TARGET='L3_model-01_task-cardgame_n28_FLAME1+2'
SEEDS={'interactionC4':'left VLPFC','interactionC5':'right VLPFC'}
COPES={16:'ppi_vlpfc-tpj',19:'ppi_interaction'}
MARKER=['id','analysis','cope','fsl_version','template_sha256','positive_map_sha256','negative_map_sha256']
class Prerequisite(Exception):
    pass

def require(ok,detail):
    if not ok: raise Prerequisite(detail)

def digest(x):
    h=hashlib.sha256()
    with x.open('rb') as f:
        for b in iter(lambda:f.read(2**20),b''): h.update(b)
    return h.hexdigest()

def fsf(p):
    return p.read_text(errors='replace') if p.is_file() else ''

def configs(s):
    return {k:v.strip().strip('"') for k,v in re.findall(r'^set fmri\(([^)]+)\)\s+([^\n]*)',s,flags=re.M)}

def rows(p):
    with p.open(encoding='utf-8-sig',newline='') as f: return list(csv.DictReader(f,delimiter='\t'))

def writetab(p,header,rr):
    with p.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=header,delimiter='\t',lineterminator='\n');w.writeheader();w.writerows(rr)

def template(project):
    p=project/'templates/L3_template_n28.fsf'
    require(p.is_file() and digest(p)==TEMPLATE_SHA,'authentic one-group November L3 template unavailable')
    return p.read_text()

def roster(project):
    q=project/'derivatives/mriqc-extractions/outliers_task-cardgame_runinfo.tsv'
    require(q.is_file(),'missing archived run QC list')
    runs={}
    for r in rows(q):
        if r['outlier_run_Custom1'].lower()=='false':
            runs.setdefault(r['Sub'],set()).add(int(r['run']))
    runs={s:v for s,v in runs.items() if len(v)>=2}
    fingerprint=hashlib.sha256(('\n'.join(sorted(runs))+'\n').encode()).hexdigest()
    require(fingerprint==pub.COHORT and sum(map(len,runs.values()))==79,'submitted 28-person/79-run cohort mismatch')
    # Fingerprint all subject/run pairs independently of the QC flags at runtime.
    full=''.join('%s\t%d\n'%(s,r) for s in sorted(runs) for r in sorted(runs[s]))
    require(hashlib.sha256(full.encode()).hexdigest()==RUNS_SHA,'archived per-participant run list mismatch')
    return runs

def check_seed(project,seed):
    name,mask,expected=pub.SEEDS[SEEDS[seed]]
    ref=pub.mask_summary(project/'masks'/mask,expected)
    require(ref.get('matches_reference') is True,'submitted cortical seed membership or MNI grid differs')
    named=pub.mask_summary(project/'masks'/name,expected)
    require(named.get('matches_reference') is not False,'named cortical seed disagrees with submitted mask')
    if named.get('matches_reference') is not True:
        obj=subprocess.run(['git','-C',str(project),'show','bda8c1b8:masks/'+name],stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        require(obj.returncode==0,'historical named seed unavailable for identity check')
        with tempfile.TemporaryDirectory() as t:
            p=Path(t)/name;p.write_bytes(obj.stdout)
            require(pub.mask_summary(p,expected).get('matches_reference') is True,'historical named seed disagrees with reference')

def choose_fsf(embedded,adjacent):
    return fsf(embedded) or fsf(adjacent)

def dated_november_fit(report):
    body=fsf(report)
    return (bool(re.search(r'Finished at [^<>\n]*\bNov\s+(?:2[2-9]|30)\b[^<>\n]*\b2021\b',body)) and
            not re.search(r'errors? occurr?ed during the analysis|fatal error',body,re.I))

def inputs_for(project,seed,cope,runs):
    source=project/'derivatives/fsl'
    result={}
    launch_log = project/'logs/rerunL1_date-2021-11-22T0204.log'
    require(launch_log.is_file() and digest(launch_log)=='e0c19d5431cf13b6f7dc679326deaef3bfac853e48e11f2870f848e679c3c5bf',
            'authentic November mean-seed launch history unavailable')
    launches={Path(v).parts[-2:] for v in re.findall(r'^running:\s+(\S+)',fsf(launch_log),flags=re.M)}
    conditions=['R_vlpfc','R_tpj','P_vlpfc','P_tpj']
    weights=([0,0,0,0,0,1,-1,1,-1] if cope==16 else [0,0,0,0,0,1,-1,-1,1])
    for sub,allowed in sorted(runs.items()):
        folder=source/sub
        name='L2_task-cardgame_model-01_type-ppi_seed-'+seed
        l2=folder/(name+'_sm-6.gfeat')
        inp=choose_fsf(l2/'design.fsf',folder/(name+'.fsf'))
        require(bool(inp),'missing archived level-two design')
        cfg=configs(inp)
        require(cfg.get('mixed_yn')=='3' and cfg.get('ncopeinputs')=='19' and cfg.get('copeinput.'+str(cope))=='1',
                'source L2 fixed-effects design unavailable or mismatched')
        require(cfg.get('level')=='2' and cfg.get('npts')==str(len(allowed)) and cfg.get('evs_orig')=='1' and
                cfg.get('con_real1.1')=='1' and all(cfg.get('evg%d.1'%i) in ('1','1.0') for i in range(1,len(allowed)+1)),
                'source L2 group-mean or run weights differ')
        item_paths=re.findall(r'^set feat_files\(\d+\)\s+"([^"]+)"',inp,flags=re.M)
        exp=[folder/('L1_task-cardgame_model-01_type-ppi_seed-%s_run-%02d_sm-6.feat'%(seed,r)) for r in sorted(allowed)]
        require(len(item_paths)==len(exp) and {Path(v).parts[-2:] for v in item_paths}=={p.parts[-2:] for p in exp},
                'L2 run selection or seed model differs from original')
        for run, l1 in zip(sorted(allowed),exp):
            require((sub,l1.stem) in launches and dated_november_fit(l1/'report.html'),
                    'L1 output cannot be tied to the November mean-seed extraction')
            l1txt=choose_fsf(l1/'design.fsf',folder/('L1_%s_task-cardgame_model-01_seed-%s_run-%02d.fsf'%(sub,seed,run)))
            require(bool(l1txt),'missing archived level-one design')
            a=configs(l1txt)
            signal='ts_task-cardgame_mask-%s_run-%02d.txt'%(seed,run)
            require(Path(a.get('custom5','')).name==signal,'archived run design lacks the matched seed regressor')
            require([a.get('evtitle%d'%i) for i in range(1,5)]==conditions,'run-level task design differs')
            try: vals=[float(a['con_real%d.%d'%(cope,i)]) for i in range(1,10)]
            except (KeyError,ValueError): vals=[]
            require(vals==weights,'run-level gPPI contrast weights differ')
        src=l2/('cope%d.feat'%cope)
        required=['stats/cope1.nii.gz','stats/varcope1.nii.gz','stats/tdof_t1.nii.gz','mask.nii.gz','design.con','design.lev']
        require(all((src/k).is_file() and (k=='design.lev' or (src/k).stat().st_size>0) for k in required),'missing L2 effect, variance, voxelwise DOF, mask, or design')
        require(dated_november_fit(src/'report.html'),'L2 result is not verified as a completed November model')
        require(any((src/k).is_file() for k in ('bg_image.nii.gz','example_func.nii.gz','standard.nii.gz')),
                'missing higher-level FEAT background image')
        require(all(grid_agrees(src/k) for k in source_files(src) if k.endswith('.nii.gz')),
                'L2 image dimensions or affine differ from the submitted MNI grid')
        require('/PPheights' in fsf(src/'design.con'),'L2 design.con missing FEAT normalization')
        result[sub]=src
    return result

def fsl_runtime():
    root=os.environ.get('FSLDIR','')
    feat=Path(root)/'bin/feat'
    require(root and feat.is_file() and os.access(str(feat),os.X_OK),'FSL is unavailable')
    version=fsf(Path(root)/'etc/fslversion').strip()
    require(re.fullmatch(r'6\.\d+(?:\.\d+){0,3}',version),'FSL 6 version could not be verified')
    return str(feat),version

def grid_agrees(path):
    try:
        with gzip.open(str(path),'rb') as f: h=f.read(348)
        endian='<' if struct.unpack_from('<i',h)[0]==348 else '>'
        dim=struct.unpack_from(endian+'8h',h,40)
        return (struct.unpack_from(endian+'i',h)[0]==348 and h[344:347]==b'n+1' and
                dim[0] in (3,4) and dim[1:4]==(65,77,65) and (dim[0]==3 or dim[4]==1) and
                struct.unpack_from(endian+'h',h,254)[0]>0 and struct.unpack_from(endian+'12f',h,280)==pub.GRID)
    except (OSError,EOFError,struct.error):return False

def source_files(src):
    required=('stats/cope1.nii.gz','stats/varcope1.nii.gz','stats/tdof_t1.nii.gz','design.lev','design.con',
              'mask.nii.gz')
    optional=('design.lcon','mean_func.nii.gz','example_func.nii.gz','bg_image.nii.gz','standard.nii.gz')
    return [f for f in required+optional if (src/f).is_file()]

def copy_inputs(sources,stage):
    # FSL uses the higher-level branch of featregapply/find_std when design.lev
    # is present. Its effect/variance/DOF and background reads are all local
    # to the enclosing copeNN.feat. All inputs, including links, become copies.
    for sub,src in sources.items():
        dest=stage/'inputs/derivatives/fsl'/sub/src.parent.name/src.name
        for name in source_files(src):
            a=src/name;b=dest/name
            b.parent.mkdir(parents=True,exist_ok=True)
            shutil.copy2(str(a),str(b))
            require(not b.is_symlink() and digest(a)==digest(b),'private L2 input copy failed byte verification')

def completion(g):
    reports=[g/'report.html',g/'cope1.feat/report.html']
    texts=[fsf(x) for x in reports]
    if any(re.search(r'Errors? occurr?ed during the analysis',t,re.I) for t in texts):
        return 'failed'
    if not all('Finished at' in t for t in texts): return 'pending'
    stage=g/'cope1.feat'
    for i in (1,2):
        if pub.nifti(stage/('thresh_zstat%d.nii.gz'%i)) is None or pub.nifti(stage/('cluster_mask_zstat%d.nii.gz'%i)) is None:
            return 'invalid'
    return 'finished'

def fit(project,store,seed,cope,runs,base_template,feat,version):
    check_seed(project,seed)
    source=inputs_for(project,seed,cope,runs)
    signature=hashlib.sha256()
    signature.update((TEMPLATE_SHA+'|'+version+'|'+seed+'|'+str(cope)).encode())
    for sub,src in sorted(source.items()):
        signature.update(sub.encode())
        for fn in source_files(src):signature.update((fn+digest(src/fn)).encode())
    dest=store/(seed+'-cope'+str(cope)+'-'+signature.hexdigest()[:16]);dest.mkdir(exist_ok=True)
    output=dest/'derived'/TARGET/('L3_task-cardgame_type-ppi_seed-%s_cnum-%02d_cname-%s_onegroup'%(seed,cope,COPES[cope]))
    g=Path(str(output)+'.gfeat')
    with (dest/'task.lock').open('a') as lock:
        fcntl.flock(lock,fcntl.LOCK_EX)
        state=completion(g)
        if state=='finished':return g,dest/'reproduced_design.fsf'
        require(state not in ('failed','invalid'),'previous fit finished with errors; see private log '+str(dest))
        started=dest/'started'
        if not started.exists():
            require(not g.exists(),'unidentified prior output at '+str(g))
            temp=dest/'inputs'
            if temp.exists(): raise Prerequisite('incomplete private input copy at '+str(temp))
            copy_inputs(source,dest)
            output.parent.mkdir(parents=True,exist_ok=True)
            params=base_template.replace('OUTPUT',str(output)).replace('BASEDIR',str(dest/'inputs')).replace('REPLACEME','type-ppi_seed-'+seed).replace('COPENUM',str(cope))
            fs=dest/'reproduced_design.fsf';fs.write_text(params)
            config=dest/'fsl_sub.yml';config.write_text('method: shell\n')
            env=dict(os.environ,FSLSUB_CONF=str(config),FSLSUB_PARALLEL='0')
            env.pop('FSLPARALLEL',None)
            started.write_text(datetime.datetime.now().isoformat()+'\n')
            print('Reproducing existing L3 for %s, COPE %d. Private output: %s'%(SEEDS[seed],cope,dest),flush=True)
            with (dest/'feat.log').open('w') as log:
                proc=subprocess.run([feat,str(fs)],env=env,cwd=str(dest),stdout=log,stderr=subprocess.STDOUT)
            if proc.returncode:
                (dest/'failed').write_text(str(proc.returncode))
                raise Prerequisite('FEAT failed; see '+str(dest/'feat.log'))
        require(not (dest/'failed').exists(),'earlier FEAT failure; see '+str(dest/'feat.log'))
        until=time.monotonic()+12*3600;notice=0
        while True:
            state=completion(g)
            if state=='finished':return g,dest/'reproduced_design.fsf'
            require(state not in ('failed','invalid'),'FEAT reports or signed products failed verification: '+str(dest))
            require(time.monotonic()<until,'timed out pending existing FEAT run; inspect '+str(dest))
            if time.monotonic()>notice:
                print('Waiting for both signed maps and completed FEAT reports in '+str(dest),flush=True)
                notice=time.monotonic()+60
            time.sleep(10)

RUNS_SHA='f19e49b0656377c7963aabf7195aaa6d5098de0787db93c64f9af439d4122bb9'
def add_reproductions(original, completed, store, version, outcome):
    h=Path.home();temp=Path(tempfile.mkdtemp(prefix='.cardgame-group-report-',dir=str(h)))
    for f in original.iterdir():
        if f.name not in ('models','contrasts.tsv','group_inputs.tsv','reproduced_groups.tsv','recovery_status.tsv'):
            (temp/f.name).symlink_to(f.resolve())
    (temp/'models').mkdir()
    if (original/'models').is_dir():
        for model in (original/'models').iterdir(): (temp/'models'/model.name).symlink_to(model.resolve())
    inv=rows(original/'contrasts.tsv');gin=rows(original/'group_inputs.tsv')
    marks=rows(original/'reproduced_groups.tsv') if (original/'reproduced_groups.tsv').is_file() else []
    for seed,cope,g,design in completed:
        mi=str(800001+list(SEEDS).index(seed)*2+list(COPES).index(cope))
        require(not (temp/'models'/mi).exists(),'reproduction id already exists in saved report')
        d=temp/'models'/mi;d.mkdir();feat=g/'cope1.feat'
        for source,name in [(design,'group-design.fsf'),(g/'design.con','group-design.con'),
                            (g/'design.mat','group-design.mat'),(feat/'design.con','cope-design.con'),
                            (feat/'mask.nii.gz','search-mask.nii.gz'),(g/'report.html','group-report.html'),
                            (feat/'report.html','cope-report.html')]:
            if source.is_file():(d/name).symlink_to(source.resolve())
        for seq,path in re.findall(r'^set feat_files\((\d+)\)\s+"([^"]+)"',design.read_text(),flags=re.M):
            match=re.search(r'/(sub-[A-Za-z0-9]+)/L2_task-cardgame_model-01_type-ppi_seed-'+seed+
                            r'_sm-6\.gfeat/cope'+str(cope)+r'\.feat/stats/cope1.nii.gz$',path)
            require(match,'private reproduction uses unexpected L2 input paths')
            gin.append(dict(id=mi,row=seq,participant_code=match.group(1),input_cope=str(cope),input_path=path))
        m={'id':mi,'analysis':SEEDS[seed],'cope':str(cope),'fsl_version':version,'template_sha256':TEMPLATE_SHA}
        for sign in (1,2):
            names=['cluster_zstat%d_std.txt'%sign,'cluster_zstat%d.txt'%sign,
                   'thresh_zstat%d.nii.gz'%sign,'cluster_mask_zstat%d.nii.gz'%sign]
            for name in names:
                if (feat/name).is_file():(d/name).symlink_to((feat/name).resolve())
            has=[str((d/name).is_file()) for name in names]
            row=dict(id=mi,group_path='historical-reproduction/'+TARGET+'/'+g.name,
                    expected_model_parent='True',analysis='ppi_seed-'+seed,cope=str(cope),name=COPES[cope],group_zstat=str(sign),
                    table_MNI_mm=has[0],table_native=has[1],thresholded_map=has[2],read_status='present; fslstats unavailable',
                    range_min_max='',nonzero_voxels='',cluster_labels=has[3])
            require(pub.sign_info(d,sign,True,row)['status'] in PUBLISHABLE,
                    'reproduced map and cluster output cannot substantiate a result for both signs')
            inv.append(row)
            m[('positive' if sign==1 else 'negative')+'_map_sha256']=pub.map_digest(d/names[2])
        marks.append(m)
    for n,records in [('contrasts.tsv',inv),('group_inputs.tsv',gin)]:
        with (original/n).open() as f: header=next(csv.reader(f,delimiter='\t'))
        writetab(temp/n,header,records)
    writetab(temp/'reproduced_groups.tsv',MARKER,marks)
    writetab(temp/'recovery_status.tsv',['analysis','cope','status'],outcome)
    checked=pub.group_summary(temp)
    for seed,cope,_,_ in completed:
        model=next(m for m in checked['models'] if m['analysis']==SEEDS[seed] and m['cope']==cope)
        require(all(s['status'] in PUBLISHABLE for s in model['signs']) and
                (model.get('source_provenance')=='historical_group_model_reproduced' or
                 model.get('source_provenance') in ('see_signed_result_provenance','archived_group_output')),
                'publisher could not bind the reproduced outcome to its provenance')
    while True:
        path=h/('cardgame-revision-'+datetime.datetime.now().strftime('%Y%m%d-%H%M%S'))
        if not path.exists():break
        time.sleep(1)
    temp.rename(path)
    return path

def decision(model):
    signs = {s['status'] for s in model['signs']}
    if signs <= PUBLISHABLE:
        previous = any(s.get('source_provenance') == 'historical_group_model_reproduced' for s in model['signs'])
        return 'reproduced' if previous else 'archived_already_available'
    if signs == {'model_missing'}:
        return 'eligible'
    if ('incomplete_output' in signs and signs <= PUBLISHABLE | {'incomplete_output'} and
            model.get('design', {}).get('design_verified') and model.get('L2_input_family_match') and
            model.get('seed_reference_verified') and model.get('model_available')):
        return 'eligible'
    return 'archive_candidates_unresolved'

def status_code(error, default):
    message = str(error)
    if message.startswith(('missing L2','missing higher-level FEAT background','missing archived level')):
        return 'missing_lower_level_inputs'
    if message.startswith(('previous fit','FEAT failed','earlier FEAT failure','FEAT reports')):
        return 'fit_failed'
    if message.startswith('timed out'):
        return 'fit_pending'
    if message.startswith(('reproduced map','publisher could not','reproduction id')):
        return 'publication_verification_failed'
    return default

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--fit-missing',action='store_true',help='reproduce eligible historic C4/C5 group fits from verified existing L2 inputs')
    parser.add_argument('--report',type=Path,help='private collector report (default: latest complete report)')
    parser.add_argument('--project',type=Path,help='analysis checkout (default: infer it from the report)')
    opts=parser.parse_args()
    repo=MODULE.parent
    store=Path.home()/'cardgame-jneurosci-group-fits'
    if opts.fit_missing:
        store.mkdir(mode=0o700,exist_ok=True)
    if opts.fit_missing:
        # Serialize discovery and report promotion as well as FEAT itself.
        lock=(store/'recovery.lock').open('a')
        fcntl.flock(lock,fcntl.LOCK_EX)
    report=(opts.report.expanduser().resolve() if opts.report else pub.latest_report())
    require(pub.complete(report),'no complete original collector report')
    summary=pub.group_summary(report)
    pub.publish(report,repo)
    if not opts.fit_missing:return 0
    statuses={}
    needs=[]
    for seed,label in SEEDS.items():
        for cope in COPES:
            model=next(v for v in summary['models'] if v['analysis']==label and v['cope']==cope)
            action=decision(model)
            if action=='eligible':needs.append((seed,cope))
            else:statuses[(label,cope)]=action

    def save(completed=(),version=''):
        nonlocal report
        outcome=[dict(analysis=a,cope=str(c),status=st) for (a,c),st in sorted(statuses.items())]
        prev=report/'recovery_status.tsv'
        if not completed and prev.is_file() and rows(prev)==outcome:return
        report=add_reproductions(report,completed,store,version,outcome)
        pub.publish(report,repo)

    errors=[]
    problem=None
    if needs:
        try:
            project=(opts.project.expanduser().resolve() if opts.project else pub._project(report))
            require(project is not None,'could not locate Linux1 analysis project')
            base=template(project);runs=roster(project)
            require(not re.search(r'[\s"]',str(store)),'private FEAT staging path contains whitespace or quotes')
        except (Prerequisite,OSError,KeyError,ValueError) as error:
            problem='source_design_unverified';errors.append(str(error))
        if not problem:
            try:feat,version=fsl_runtime()
            except (Prerequisite,OSError) as error:
                problem='fsl_unavailable';errors.append(str(error))
    for seed,cope in needs:
        key=(SEEDS[seed],cope)
        if problem:
            statuses[key]=problem
            continue
        try:
            previous='source_design_unverified'
            g,design=fit(project,store,seed,cope,runs,base,feat,version)
            previous='publication_verification_failed'
            statuses[key]='reproduced'
            save([(seed,cope,g,design)],version)
        except (Prerequisite,OSError,ValueError,KeyError,shutil.Error) as error:
            statuses[key]=status_code(error,previous)
            errors.append('%s COPE %d: %s'%(key[0],cope,error))
    save()
    for line in errors:print(line,file=sys.stderr,flush=True)
    return 3 if any(s not in ('reproduced','archived_already_available') for s in statuses.values()) else 0

if __name__=='__main__':
    try:sys.exit(main())
    except (Prerequisite,OSError,KeyError,ValueError,shutil.Error,subprocess.CalledProcessError) as error:
        print('Recovery stopped: '+str(error),file=sys.stderr)
        sys.exit(2)
