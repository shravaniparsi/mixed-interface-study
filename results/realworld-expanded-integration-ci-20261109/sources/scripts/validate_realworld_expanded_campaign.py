#!/usr/bin/env python3
"""Independently reconstruct the archived RealWorld terminal campaign."""
import sys
from pathlib import Path
from copy import deepcopy
from run_realworld_expanded_campaign import SOURCES, ROOT
from realworld_expanded_campaign import read,write,sha,plan_for,read_job
from mixed_interface.campaign_v2 import drive
from mixed_interface.repetition import require


def validate(directory):
    directory=Path(directory);cert=read(directory/'plan.json')
    require(set(cert['sources'])==set(SOURCES),'Source inventory differs')
    for n,h in cert['sources'].items():
        require(sha(directory/'sources'/n)==h==sha(ROOT/n),'Source differs: '+n)
    registry=read(directory/'sources/manifests/realworld-paired-controls-v1.json')
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
    require(state['status']=='completed_observations' and len(state['initial'])==7 and not state['repeated'],'Ordinary qualification shape differs')
    require(all(o['kind']=='clean_observation' for o in state['initial']),'Control observations differ')
    return {'verified':True,'pairs':7,'branches':14,'followup_jobs':0,'primary_freeze_complete':False,
            'source_commit':cert['source_commit'],'campaign_sha256':sha(directory/'campaign.json')}


if __name__=='__main__':
    d=Path(sys.argv[1]);result=validate(d);write(d/'verification.json',result);print(result)
