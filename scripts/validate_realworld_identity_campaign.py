#!/usr/bin/env python3
"""Independently reconstruct the archived RealWorld terminal campaign."""
import sys
from pathlib import Path
from copy import deepcopy
from run_realworld_identity_campaign import SOURCES, ROOT
from realworld_identity_campaign import read,write,sha,plan_for,read_job
from mixed_interface.campaign_v2 import drive
from mixed_interface.repetition import require


def read_selection(directory):
    registry=read(Path(directory)/'sources/manifests/realworld-identity-controls-v1.json')
    plan_for(registry)
    return registry


def validate(directory):
    directory=Path(directory);cert=read(directory/'plan.json')
    require(set(cert['sources'])==set(SOURCES),'Source inventory differs')
    for n,h in cert['sources'].items():
        require(sha(directory/'sources'/n)==h==sha(ROOT/n),'Source differs: '+n)
    registry=read_selection(directory)
    require(cert['plan']==plan_for(registry),'Plan differs')
    reconstructed=[]
    def execute(job):
        d=directory/job['job_id'];require(read(d/'job.json')==job,'Job differs')
        require(read(d/'dispatch.json')['job']==job,'Dispatch differs')
        result=read_job(d,job,registry,read(d/'execution.json'))
        require(result==read(d/'observations.json'),'Extracted observations differ')
        reconstructed.append(job['job_id']);return result['terminal']
    state=drive(cert['plan'],execute,lambda _:None)
    require(state==read(directory/'campaign.json'),'Ledger differs')
    require(sorted(p.name for p in directory.iterdir() if p.is_dir() and p.name!='sources')==sorted(reconstructed),'Unexpected job directories')
    require(state['status']=='completed_observations' and len(state['initial'])==5,'Initial sweep incomplete')
    from collections import Counter
    attempts=state['initial']+state['repeated']
    return {'verified':True,'initial_pairs':5,'pair_attempts':len(attempts),'branches':len(attempts)*2,
            'kinds':dict(Counter(o['kind'] for o in attempts)), 'followup_jobs':len(state['repeated']),
            'primary_freeze_complete':False,'source_commit':cert['source_commit'],'campaign_sha256':sha(directory/'campaign.json')}



if __name__=='__main__':
    d=Path(sys.argv[1]);result=validate(d);write(d/'verification.json',result);print(result)
