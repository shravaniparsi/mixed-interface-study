#!/usr/bin/env python3
"""Derive a prospective recovery inventory solely from verified pre-run rejection."""
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
from primary_preflight_v1 import ROOT,read,sha
from quartz_recovery_preflight_v1 import PREPARATION
from retain_quartz_provider_failure_v1 import build,OUTPUT as RETENTION
from mixed_interface.common_execution_v1 import write
from mixed_interface.repetition import require
NEW_SOURCES=['scripts/freeze_quartz_recovery_v1.py','scripts/verify_quartz_recovery_release_v1.py','scripts/retain_quartz_provider_failure_v1.py','scripts/verify_quartz_correction_freeze_v1.py','scripts/quartz_recovery_preflight_v1.py','scripts/run_quartz_recovery_unit_v1.py',
 'scripts/validate_quartz_recovery_unit_v1.py','scripts/quartz_recovery_matrix_v1.py',
 'scripts/quartz_recovery_collection_v1.py','scripts/verify_quartz_recovery_collection_v1.py',
 'scripts/prepare_quartz_recovery_followups_v1.py','scripts/prepare_quartz_recovery_v1.py',
 '.github/workflows/quartz_recovery_v1.yml','protocol/quartz-provider-recovery-v1.md']

def derive(original,retention):
    missing=set(retention['unstarted_batch_ids']);initial=[];potential={};links={}
    for old in original['plan']['initial_batches']:
        if old['batch_id'] not in missing:continue
        record=retention['records'][old['batch_id']]
        require(record['status']=='not_started_provider_billing_rejection' and record['runner_assigned'] is False and record['steps_executed']==0,'A started unit cannot enter recovery')
        unit=deepcopy(old);unit['batch_id']=unit['batch_id'].replace('qfix-','qrecover-')
        for job in unit['jobs']:job['attempt_id']=job['attempt_id'].replace('qfix-','qrecover-')
        initial.append(unit);links[unit['batch_id']]={'original_batch_id':old['batch_id'],'provider_job_id':record['job_id']}
        repeats=[]
        for r in (2,3):
            later=deepcopy(unit);later['batch_id']=later['batch_id'][:-1]+str(r);later['repetition']=r
            for job in later['jobs']:job['attempt_id']=job['attempt_id'][:-1]+str(r);job['repetition']=r
            repeats.append(later)
        potential[unit['target_pair_id']]=repeats
    require({v['original_batch_id'] for v in links.values()}==missing,'Recovery inventory differs from never-started cases')
    return {'initial_batches':initial,'potential_followup_batches':potential},links

def prepare():
    require(not PREPARATION.exists(),'Recovery already registered')
    retained=build();require(retained==read(RETENTION),'Retained provider evidence differs')
    original=read(ROOT/'manifests/quartz-form-correction-preparation-v1.json');plan,links=derive(original,retained)
    require(len(plan['initial_batches'])==16,'Expected provider-rejected inventory differs')
    value={'kind':'additional_exposed_quartz_provider_recovery_v1','registered_at_utc':datetime.now(timezone.utc).isoformat(),
        'provider_retention_sha256':sha(RETENTION),'original_correction_preparation_sha256':sha(ROOT/'manifests/quartz-form-correction-preparation-v1.json'),
        'qualification_sha256':sha(ROOT/'manifests/quartz-form-correction-freeze-v1.json'),
        'source_sha256':{**original['source_sha256'],**{p:sha(ROOT/p) for p in NEW_SOURCES}},
        'environment':original['environment'],'plan':plan,'original_case_links':links,
        'primary_freeze_complete':False,'execution_authorized':False,
        'scope':'Additional exposed collection for never-started cases; no substitution, no duplicate independent-sample credit'}
    write(PREPARATION,value);return value
if __name__=='__main__':print('Prepared recovery units:',len(prepare()['plan']['initial_batches']))
