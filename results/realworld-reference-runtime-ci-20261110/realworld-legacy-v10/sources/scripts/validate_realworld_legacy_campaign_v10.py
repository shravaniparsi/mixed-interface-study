#!/usr/bin/env python3
"""Reconstruct fresh v10 raw job evidence; stored outcome summaries are never trusted."""
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from realworld_terminal_campaign import read,write,sha
from realworld_legacy_jobs_v8 import selection
from realworld_legacy_jobs_v10 import read_job
from realworld_legacy_campaign_v10 import drive,plan_for,JOB_TIMEOUT_S,OUTER_TIMEOUT_S
from mixed_interface.repetition import require


def verify_accounting(registry, report, observations):
    def replay(job):
        require(job['job_id'] in observations, 'Missing dispatched observation')
        return observations[job['job_id']]
    reconstructed=drive(registry,replay,lambda value:None)
    require(reconstructed==report,'Recorded sweep differs from reconstructed decisions')
    require(set(observations)==set(reconstructed['completed_jobs']),'Extra or omitted observations')
    return reconstructed


def validate(directory):
    from run_realworld_legacy_campaign_v10 import SOURCES
    directory=Path(directory);cert=read(directory/'plan.json')
    require(set(cert['sources'])==set(SOURCES),'Source inventory differs')
    for name,h in cert['sources'].items():
        require(sha(directory/'sources'/name)==h==sha(ROOT/name),'Source differs: '+name)
    require(set(cert['runtime_sha256'])=={'runtime-versions.json','browser.json'},'Runtime inventory differs')
    for name,h in cert['runtime_sha256'].items():
        require(sha(directory/name)==h,'Runtime record differs: '+name)
    registry=selection();plan=plan_for(registry)
    require(read(directory/'selection.json')==registry and cert['plan']==plan,'Selection or plan differs')
    require(cert['primary_freeze_complete'] is False and cert['new_primary_samples']==0,'Primary promotion')
    require((cert['job_timeout_s'],cert['outer_timeout_s'],cert['cleanup_grace_s'],cert['kill_wait_s'])
            ==(JOB_TIMEOUT_S,OUTER_TIMEOUT_S,5,2),'Time budget differs')
    require(sha(directory/'bootstrap.json')==cert['bootstrap_sha256'],'Bootstrap hash differs')
    bootstrap=read(directory/'bootstrap.json');source=read(ROOT/registry['source'])
    require(bootstrap['status']=='prepared_not_started' and bootstrap['application_source_modified'] is False
            and all(bootstrap[k]==source[k] for k in ('backend_commit','frontend_commit'))
            and bootstrap['python_lock_sha256']==sha(ROOT/'manifests/realworld-python-lock.txt'),'Bootstrap differs')
    report=read(directory/'diagnostic.json')
    require(report['status'] in ('completed_bounded_diagnostic','halted_terminal_outcome'),
            'Executor/setup failure retained but not a verified semantic sweep')
    ids=report['started_jobs'];expected=[j['job_id'] for j in plan['jobs']]
    require(ids==expected[:len(ids)] and ids==report['completed_jobs'],'Incomplete or reordered attempt inventory')
    require(sorted(p.name for p in directory.iterdir() if p.is_dir() and p.name!='sources')==sorted(ids),
            'Unexpected attempt directory')
    observations={};branches=0
    for job in plan['jobs'][:len(ids)]:
        d=directory/job['job_id']
        require(read(d/'job.json')==job and read(d/'dispatch.json')['job']==job,'Dispatch differs')
        value=read_job(d,job,registry,read(d/'execution.json'))
        require(value==read(d/'observations.json'),'Stored observation differs from raw evidence')
        summary=read(next((d/'run').glob('*/summary.json')))
        require(summary['source_commit']==cert['source_commit'],'Executed commit differs')
        observations[job['job_id']]=value;branches+=len(job['branches'])
    verify_accounting(registry,report,observations)
    return {'verified':True,'status':report['status'],'source_commit':cert['source_commit'],
            'completed_jobs':len(ids),'branches':branches,'decisions':report['decisions'],
            'primary_freeze_complete':False,'new_primary_samples':0}


if __name__=='__main__':
    result=validate(sys.argv[1]);write(Path(sys.argv[1])/'verification.json',result)
    print('Verified',result['completed_jobs'],'jobs:',result['status'])
