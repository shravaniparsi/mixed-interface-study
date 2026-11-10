#!/usr/bin/env python3
"""Actual job elapsed time for the finite cohort; not invoice or lifetime cost."""
import hashlib,json
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def build():
    summary=json.loads((ROOT/'manifests/production-extension-summary-v1.json').read_text());runs={}
    for app,a in summary['applications'].items():
        for phase in ['initial','followup']:
            if phase+'_run' in a:runs[a[phase+'_run'].split(':')[0]]=(app,phase)
    rows=[]
    for run,(app,phase) in runs.items():
        p=ROOT/'results/production-extension-run-accounting-v1'/f'{run}.json';v=json.loads(p.read_text());assert str(v['databaseId'])==run and v['status']=='completed';seconds=0
        for j in v['jobs']:
            assert j['status']=='completed';start=datetime.fromisoformat(j['startedAt'].replace('Z','+00:00'));end=datetime.fromisoformat(j['completedAt'].replace('Z','+00:00'));elapsed=(end-start).total_seconds();assert elapsed>=0;seconds+=elapsed
        rows.append(dict(application=app,phase=phase,run_id=run,jobs=len(v['jobs']),job_elapsed_seconds=seconds,metadata=str(p.relative_to(ROOT)),metadata_sha256=hashlib.sha256(p.read_bytes()).hexdigest()))
    return dict(kind='production_extension_finite_compute_v1',runs=rows,total_job_elapsed_seconds=sum(r['job_elapsed_seconds'] for r in rows),total_jobs=sum(r['jobs'] for r in rows),paid_model_calls=0,scope='Finite initial and fixed-followup cohorts only. Job-start to job-completion includes runner setup and artifact upload, excludes queued time. Does not include adapter qualification, earlier exploratory cohorts, downloads, developer time or storage. Standard public hosted workflows were used; elapsed seconds are not a billing statement. No API-versus-native speedup is inferred from aggregate CI duration.')
if __name__=='__main__':
    p=ROOT/'manifests/production-extension-cost-v1.json';assert not p.exists();v=build();p.write_text(json.dumps(v,indent=2)+'\n');print('Finite runner elapsed minutes:',round(v['total_job_elapsed_seconds']/60,2),'jobs:',v['total_jobs'])
