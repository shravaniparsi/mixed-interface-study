#!/usr/bin/env python3
"""Reconstruct a bounded database-instrumented diagnostic without promoting semantics."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from realworld_identity_campaign import read,write,sha
from realworld_identity_database_job_v7 import read_job
from realworld_paired_database_plan_v7 import jobs
from mixed_interface.repetition import require
from mixed_interface.terminal_outcomes import decision


def validate(directory):
    from run_realworld_paired_database_v7 import SOURCES
    directory=Path(directory);cert=read(directory/'plan.json')
    require(set(cert['sources'])==set(SOURCES),'Diagnostic source inventory differs')
    for name,h in cert['sources'].items():
        require(sha(directory/'sources'/name)==h==sha(ROOT/name),'Diagnostic source differs: '+name)
    registry=read(directory/'sources/manifests/realworld-identity-controls-v1.json');selected=jobs(registry)
    require(cert['jobs']==selected and cert['new_primary_samples']==0 and cert['primary_freeze_complete'] is False,'Diagnostic plan differs')
    require(sha(directory/'bootstrap.json')==cert['bootstrap_sha256'],'Bootstrap hash differs')
    bootstrap=read(directory/'bootstrap.json')
    require(bootstrap['status']=='prepared_not_started' and bootstrap['application_source_modified'] is False
            and bootstrap['backend_commit']=='87dd078c883a046f5ff20269df2fb004d8b5f83f'
            and bootstrap['frontend_commit']=='b14ba5011cf9cc97babfcd7ca99dcfbb058862e7'
            and bootstrap['python_lock_sha256']==sha(ROOT/'manifests/realworld-python-lock.txt'),'Bootstrap differs')
    report=read(directory/'diagnostic.json');ids=[j['job_id'] for j in selected]
    require(report['status']=='completed_bounded_diagnostic' and report['started_jobs']==report['completed_jobs']==ids,'Incomplete diagnostic')
    require(report['primary_freeze_complete'] is False and report['new_primary_samples']==0,'Diagnostic promoted')
    require(sorted(p.name for p in directory.iterdir() if p.is_dir() and p.name!='sources')==sorted(ids),'Attempt inventory differs')
    observed=[];kinds=[];backups=0
    for index,job in enumerate(selected):
        d=directory/job['job_id'];require(read(d/'job.json')==job and read(d/'dispatch.json')['job']==job,'Dispatch differs')
        value=read_job(d,job,registry,read(d/'execution.json'))
        require(value==read(d/'observations.json'),'Observed measurement differs')
        summary=read(next((d/'run').glob('*/summary.json')))
        require(summary['source_commit']==cert['source_commit'],'Execution source commit differs')
        terminal=value['legacy_result']['terminal'];kinds.append(terminal['kind'])
        require(index!=0 or terminal['kind']=='clean_observation','Unclean route control')
        require(index==len(selected)-1 or decision(terminal)['action']!='halt','Dispatch after halt')
        backups+=sum(len(m['snapshot_sha256']) for m in value['measurements'].values())
        observed.append({'candidate_id':job['pair_id'],'terminal_kind':terminal['kind'],
                         'measurements':value['measurements'],'database_pair_comparison':value['database_pair_comparison']})
    require(report['terminal_kinds']==kinds,'Terminal summary differs')
    return {'verified':True,'source_commit':cert['source_commit'],'pairs':4,'branches':8,'database_backups':backups,
            'results':observed,'primary_freeze_complete':False,'new_primary_samples':0,
            'scope':'bounded engineering diagnostic; no stable finding or primary prevalence estimate'}


if __name__=='__main__':
    result=validate(sys.argv[1]);write(Path(sys.argv[1])/'verification.json',result)
    print('Verified four paired database diagnostics and',result['database_backups'],'backups')
