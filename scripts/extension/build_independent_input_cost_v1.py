#!/usr/bin/env python3
"""Account for captured application-run job elapsed time, not a billing invoice."""
import argparse,hashlib,json
from datetime import datetime
from pathlib import Path
from collections import Counter
ROOT=Path(__file__).resolve().parents[2]
RUNS={'43067934033':'schema_capture','43068337661':'schema_capture','43069604760':'qualification','43070094888':'qualification','43070783189':'qualification','43071019063':'scientific_initial','43071407472':'qualification','43071680510':'qualification','43072084690':'scientific_followup','43072645323':'scientific_initial','43072847302':'qualification','43074513003':'qualification','43075314681':'qualification','43075912184':'scientific_initial'}
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def seconds(a,b):return (datetime.fromisoformat(b.replace('Z','+00:00'))-datetime.fromisoformat(a.replace('Z','+00:00'))).total_seconds()
def build():
    root=ROOT/'results/independent-input-run-accounting-v1';rows=[];sources={}
    for run,phase in RUNS.items():
        rp=root/f'{run}-run.json';jp=root/f'{run}-jobs.json';r=read(rp);j=read(jp)
        assert str(r['id'])==run and r['run_attempt']==1 and r['status']=='completed' and r['repository']['private'] is False
        assert len(j['jobs'])==j['total_count']
        jobs=[]
        for job in j['jobs']:
            assert str(job['run_id'])==run and job['status']=='completed' and job['labels']==['ubuntu-24.04']
            elapsed=seconds(job['started_at'],job['completed_at']);assert elapsed>=0
            jobs.append({'id':job['id'],'name':job['name'],'conclusion':job['conclusion'],'elapsed_seconds':elapsed,'labels':job['labels']})
        rows.append({'run_id':run,'phase':phase,'source_commit':r['head_sha'],'conclusion':r['conclusion'],'jobs':jobs,'job_elapsed_seconds':sum(x['elapsed_seconds'] for x in jobs)})
        for p in [rp,jp]:sources[str(p.relative_to(ROOT))]=sha(p)
    return dict(kind='independent_input_application_compute_v1',runs=rows,run_count=len(rows),jobs=sum(len(r['jobs']) for r in rows),job_conclusions=dict(Counter(j['conclusion'] for r in rows for j in r['jobs'])),job_elapsed_minutes=round(sum(r['job_elapsed_seconds'] for r in rows)/60,3),phase_job_elapsed_minutes={phase:round(sum(r['job_elapsed_seconds'] for r in rows if r['phase']==phase)/60,3) for phase in sorted(set(RUNS.values()))},paid_model_calls=0,source_sha256=sources,scope='Captured application schema, qualification, initial and fixed-followup runs of this independent-input study. Includes failed qualification jobs. Excludes repository unit-check jobs, earlier studies, local development time and tool/assistant usage. Elapsed job time is not billable minutes or a cash invoice. All recorded application jobs used the public repository and standard ubuntu-24.04 label.')
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args();target=ROOT/'manifests/independent-input-cost-v1.json';v=build()
    if a.verify:assert read(target)==v
    else:assert not target.exists();target.write_text(json.dumps(v,indent=2)+'\n')
    print(json.dumps({k:v[k] for k in ['run_count','jobs','job_conclusions','job_elapsed_minutes']}))
