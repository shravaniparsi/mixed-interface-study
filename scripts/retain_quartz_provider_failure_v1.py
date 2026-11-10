#!/usr/bin/env python3
"""Account for never-started hosted jobs without inventing experiment artifacts."""
import argparse,json
from pathlib import Path
from quartz_correction_preflight_v1 import ROOT,read,sha,units
from validate_quartz_correction_unit_v1 import validate
from mixed_interface.common_execution_v1 import inventory,write
from mixed_interface.repetition import require
PROVIDER=ROOT/'results/quartz-correction-provider-ci-42791911582'
ARCHIVE=ROOT/'results/quartz-correction-initial-ci-42791911582'
OUTPUT=ROOT/'manifests/quartz-correction-initial-attempt1-retention-v1.json'
MESSAGE="The job was not started because recent account payments have failed or your spending limit needs to be increased. Please check the 'Billing & plans' section in your settings"

def provider_rejection(job,annotations):
    require(job['status']=='completed' and job['conclusion']=='failure','Provider job not terminal failure')
    require(job['steps']==[] and job['runner_id']==0 and job['runner_name']=='','A started job cannot be called unstarted')
    require(any(a['annotation_level']=='failure' and a['message']==MESSAGE for a in annotations),'Provider rejection annotation absent')
    return {'status':'not_started_provider_billing_rejection','job_id':job['id'],'runner_assigned':False,'steps_executed':0,'reason':MESSAGE}

def build():
    run=read(PROVIDER/'workflow-run-final.json');require(run['id']==42791911582 and run['run_attempt']==1 and run['status']=='completed','Provider run differs')
    expected={u['batch_id']:u for u in units('initial')};jobs={}
    for job in read(PROVIDER/'jobs.json')['jobs']:
        if job['name']=='selection':require(job['conclusion']=='success','Selection failed');continue
        require(job['run_id']==run['id'],'Foreign provider job')
        bid=job['name'].removeprefix('application (').split(',',1)[0]
        require(bid in expected and bid not in jobs and job['name']==f'application ({bid}, quartz, 20.20.2, 21.0.13+9)','Provider matrix differs')
        jobs[bid]=job
    require(set(jobs)==set(expected),'Provider job inventory incomplete')
    folders={}
    for path in ARCHIVE.glob('*/requested-unit.json'):
        request=read(path);bid=request['batch']
        require(bid in expected and bid not in folders and request['mode']=='initial' and request['run_identity']==str(run['id'])+':1' and request['source_commit']==run['head_sha'],'Artifact request differs')
        folders[bid]=path.parent
    require(len(list(ARCHIVE.iterdir()))==len(folders),'Foreign archive entries')
    records={}
    for bid,job in jobs.items():
        if bid in folders:
            require(job['conclusion']=='success','Executed job provider status differs')
            value=validate(folders[bid]/'quartz-correction-unit-v1')
            require(value['run_identity']==str(run['id'])+':1' and value['source_commit']==run['head_sha'],'Executed provenance differs')
            records[bid]={'status':'executed_and_reconstructed','verification':value}
        else:
            records[bid]=provider_rejection(job,read(PROVIDER/f"check-{job['id']}-annotations.json"))
    unstarted=[bid for bid,r in records.items() if r['status']=='not_started_provider_billing_rejection']
    return {'kind':'incomplete_correction_collection_provider_retention_v1','application_run':run['id'],'run_attempt':1,
        'source_commit':run['head_sha'],'records':records,'executed_units':len(folders),'unstarted_units':len(unstarted),
        'unstarted_batch_ids':sorted(unstarted),'all_declared_units_accounted_for':True,'complete_registered_execution':False,
        'replacement_or_resume_authorized':False,'provider_files_sha256':inventory(PROVIDER),'application_files_sha256':inventory(ARCHIVE),
        'scope':'Provider rejections are not application observations. No full correction-phase manifest or completion certificate is issued.'}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');args=p.parse_args();value=build()
    if args.verify:require(read(OUTPUT)==value,'Provider retention differs')
    else:require(not OUTPUT.exists(),'Provider retention already registered');write(OUTPUT,value)
    print(json.dumps({k:value[k] for k in ('executed_units','unstarted_units','complete_registered_execution')}))
