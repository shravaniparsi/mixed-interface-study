#!/usr/bin/env python3
"""Independently reconstruct the archived RealWorld terminal campaign."""
import sys
from pathlib import Path
from copy import deepcopy
from run_realworld_field_campaign import SOURCES, ROOT
from realworld_field_campaign import read,write,sha,plan_for,read_job
from mixed_interface.campaign_v2 import drive
from mixed_interface.repetition import require


def validate(directory):
    directory=Path(directory);cert=read(directory/'plan.json')
    require(set(cert['sources'])==set(SOURCES),'Source inventory differs')
    for n,h in cert['sources'].items():
        require(sha(directory/'sources'/n)==h==sha(ROOT/n),'Source differs: '+n)
    registry=read(directory/'sources/manifests/realworld-rejection-controls-v1.json')
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
    require(state['status']=='completed_observations' and len(state['initial'])==9 and not state['repeated'],'Ordinary qualification shape differs')
    require([o['kind'] for o in state['initial']]==['clean_observation']*5+['matched_rejection']*4,'Acceptance/rejection observations differ')
    for o in state['initial'][5:]:
        require(set(o['outcome']['observation_signature']['prefix_http_status'].values())=={422},'Expected recorded 422 rejection')
    return {'verified':True,'pairs':9,'branches':18,'matched_rejection_pairs':4,'followup_jobs':0,'primary_freeze_complete':False,
            'source_commit':cert['source_commit'],'campaign_sha256':sha(directory/'campaign.json')}


if __name__=='__main__':
    d=Path(sys.argv[1]);result=validate(d);write(d/'verification.json',result);print(result)
