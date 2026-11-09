#!/usr/bin/env python3
"""Reconstruct PetClinic jobs, extraction, ordering and campaign from retained evidence."""
import sys
from pathlib import Path
from run_petclinic_terminal_campaign import SOURCES
from petclinic_terminal_campaign import ROOT,read,write,sha,contract,read_job
from mixed_interface.repetition import require
from mixed_interface.campaign_v2 import drive

def validate(directory):
    directory=Path(directory);cert=read(directory/'plan.json')
    require(set(cert['sources'])==set(SOURCES),'Source inventory differs')
    for n,h in cert['sources'].items():require(sha(directory/'sources'/n)==h==sha(ROOT/n),'Source differs: '+n)
    require(set(cert['environment'])=={'petclinic-bootstrap.json','runtime-versions.json','browser.json'},'Environment inventory differs')
    for n,h in cert['environment'].items():require(sha(directory/n)==h,'Environment differs')
    require(cert['plan']==contract()['plan'],'Plan differs')
    cleanup=read(directory/'cleanup.json');require(set(cleanup)=={'frontend'} and cleanup['frontend']['exit_confirmed'] is True and not cleanup['frontend']['errors'],'Frontend exit unconfirmed')
    reconstructed=[];pids=[]
    def execute(job):
        d=directory/job['job_id'];require(read(d/'dispatch.json')['job']==job,'Dispatch differs')
        result=read_job(d,job,read(d/'execution.json'))
        require(read(d/'run/summary.json')['jar_sha256']==read(directory/'petclinic-bootstrap.json')['jar_sha256'],'Runtime jar differs')
        require(result==read(d/'observations.json'),'Extraction differs')
        for b in read(d/'run/summary.json')['branches']:pids.append(read(d/'run'/b['result'])['backend_pid'])
        reconstructed.append(job['job_id']);return result['terminal']
    state=drive(cert['plan'],execute,lambda _:None)
    require(state==read(directory/'campaign.json'),'Campaign differs')
    require(sorted(p.name for p in directory.iterdir() if p.is_dir() and p.name!='sources')==sorted(reconstructed),'Unexpected jobs')
    require(len(set(pids))==len(pids),'Backend PID reused')
    require(state['status']=='completed_observations' and len(state['initial'])==6 and not state['repeated'],'Qualification shape differs')
    require([o['kind'] for o in state['initial']]==['clean_observation']*3+['matched_rejection']*3,'Control outcome differs')
    return {'verified':True,'pairs':6,'branches':12,'matched_rejection_pairs':3,'followup_jobs':0,'source_commit':cert['source_commit'],'campaign_sha256':sha(directory/'campaign.json'),'primary_freeze_complete':False}
if __name__=='__main__':
    d=Path(sys.argv[1]);result=validate(d);write(d/'verification.json',result);print(result)
