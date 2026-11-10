#!/usr/bin/env python3
"""Register the full exposed Quartz correction cohort before corrected outcomes."""
from copy import deepcopy
from datetime import datetime,timezone
from pathlib import Path
from primary_preflight_v1 import ROOT,PREPARATION as ORIGINAL,read,sha
from quartz_correction_preflight_v1 import PREPARATION
from mixed_interface.common_execution_v1 import write
from mixed_interface.repetition import digest,require

NEW_SOURCES=[
 'scripts/quartz_generated_case_v3.mjs','scripts/run_quartz_pair_job_v3.mjs',
 'scripts/summarize_quartz_oracle_components_v3.py','scripts/quartz_repeat_outcomes_v3.py','scripts/quartz_terminal_outcomes_v3.py',
 'scripts/quartz_correction_preflight_v1.py','scripts/run_quartz_correction_unit_v1.py','scripts/validate_quartz_correction_unit_v1.py',
 'scripts/quartz_correction_matrix_v1.py','scripts/quartz_correction_collection_v1.py','scripts/verify_quartz_correction_collection_v1.py',
 'scripts/prepare_quartz_correction_followups_v1.py','scripts/prepare_quartz_correction_v1.py',
 '.github/workflows/quartz_correction_v1.yml','protocol/quartz-form-correction-v1.md']

def prepare():
    require(not PREPARATION.exists(),'Correction preparation already registered')
    original=read(ORIGINAL);initial=[];potential={}
    for old in original['plan']['initial_batches']:
        if old['application']!='quartz':continue
        unit=deepcopy(old);unit['batch_id']=unit['batch_id'].replace('initial-','qfix-')
        for job in unit['jobs']:
            job['attempt_id']=job['attempt_id'].replace('initial-','qfix-')
            job['runtime']['runner']='scripts/run_quartz_pair_job_v3.mjs'
            job['runtime']['loader']='quartz_terminal_outcomes_v3'
            job['binding_sha256']=digest({'original_binding':job['binding_sha256'],'corrected_runtime':job['runtime']})
        initial.append(unit);repeats=[]
        for r in (2,3):
            later=deepcopy(unit);later['batch_id']=later['batch_id'][:-1]+str(r);later['repetition']=r
            for job in later['jobs']:job['attempt_id']=job['attempt_id'][:-1]+str(r);job['repetition']=r
            repeats.append(later)
        potential[unit['target_pair_id']]=repeats
    require(len(initial)==22,'Quartz inventory differs')
    smoke=deepcopy(initial[0]);smoke['batch_id']='qfix-smoke';smoke['jobs']=[]
    for number,label in ((51,'empty'),(67,'nonempty_string')):
        source=next(u for u in initial if u['batch_id']==f'qfix-{number:03}-r1')['jobs'][0]
        for r in (1,2):
            job=deepcopy(source);job.update(attempt_id=f'qfix-smoke-{label}-r{r}',role='measurement_qualification',repetition=r);smoke['jobs'].append(job)
    value={'kind':'exposed_quartz_form_correction_v1','registered_at_utc':datetime.now(timezone.utc).isoformat(),
        'original_preparation_sha256':sha(ORIGINAL),'source_sha256':{**original['source_sha256'],**{p:sha(ROOT/p) for p in NEW_SOURCES}},
        'environment':original['environment'],'smoke_units':[smoke],
        'plan':{'initial_batches':initial,'potential_followup_batches':potential},
        'scope':'All 22 Quartz pairs after measurement correction. Previously observed; no held-out or replacement claim.',
        'primary_freeze_complete':False,'execution_authorized':False}
    write(PREPARATION,value);return value

if __name__=='__main__':print('Registered corrected Quartz units:',len(prepare()['plan']['initial_batches']))
