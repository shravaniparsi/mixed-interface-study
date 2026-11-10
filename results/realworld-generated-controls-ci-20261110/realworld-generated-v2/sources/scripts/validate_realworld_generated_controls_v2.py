#!/usr/bin/env python3
"""Independently reconstruct exactly four exposed runtime branches."""
import json,sys
from pathlib import Path
from realworld_generated_runtime_v2 import ROOT,SOURCES,jobs,read,branch
from realworld_generated_loader_v1 import sha
from realworld_generated_terminal_v1 import compare
from mixed_interface.repetition import require

def validate(root):
    root=Path(root);cert=read(root/'plan.json');report=read(root/'report.json')
    require(cert['jobs']==jobs() and set(cert['sources'])==set(SOURCES),'Source or job selection differs')
    for s,h in cert['sources'].items():require(sha(root/'sources'/s)==h==sha(ROOT/s),'Executed source differs: '+s)
    require(cert['worker_timeout_s']==80 and cert['outer_timeout_s']==600 and cert['primary_freeze_complete'] is False,'Budget/scope differs')
    bootstrap=read(root/'realworld-bootstrap.json')
    require(bootstrap['status']=='prepared_not_started' and bootstrap['application_source_modified'] is False,'Bootstrap not qualified')
    require(bootstrap['backend_commit']=='87dd078c883a046f5ff20269df2fb004d8b5f83f' and bootstrap['frontend_commit']=='b14ba5011cf9cc97babfcd7ca99dcfbb058862e7','Application revision differs')
    require(report['status']=='completed' and report['completed_jobs']==[j['job_id'] for j in jobs()] and report['new_primary_samples']==0 and report['primary_freeze_complete'] is False,'Run incomplete or promoted')
    cleanup=report['frontend_cleanup'];require(cleanup['exit_confirmed'] and not cleanup['errors'],'Frontend cleanup incomplete')
    require({p.name for p in root.glob('generated-*')}=={j['job_id'] for j in jobs()},'Unexpected job directory')
    results=[];fixture_sha=sha(root/'fixture.sqlite3')
    for job in jobs():
        d=root/job['job_id'];require(read(d/'job.json')==job,'Dispatched job differs')
        require({p.name for p in d.iterdir() if p.is_dir()}=={'api','ui'},'Branch inventory differs')
        branches={c:branch(d/c,job,c,fixture_sha) for c in ('api','ui')}
        value=compare(job,branches,{c:sha(d/c/'observation.json') for c in branches})
        require(value==read(d/'observations.json') and value['terminal']['kind']=='clean_observation','Pair reconstruction differs')
        results.append({'job_id':job['job_id'],'terminal_kind':value['terminal']['kind'],'branch_total_s':{c:r['branch_total_s'] for c,(_,r) in branches.items()}})
    return {'verified':True,'source_commit':cert['source_commit'],'pairs':2,'branches':4,'results':results,'primary_freeze_complete':False,'new_primary_samples':0}

if __name__=='__main__':print(json.dumps(validate(sys.argv[1]),indent=2))
