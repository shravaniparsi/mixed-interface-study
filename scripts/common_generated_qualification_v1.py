"""Two exposed generated references through the common bridge, bounded without repeats."""
from copy import deepcopy
from petclinic_timed_jobs_v4 import ROOT,read,sha
from mixed_interface.common_bindings_v1 import preflight
from mixed_interface.repetition import require,digest
from mixed_interface.terminal_outcomes import decision
PAIR_TIMEOUT_S=190
OUTER_TIMEOUT_S=600

def plan():
    registry=read(ROOT/'manifests/common-bindings-v1.json')['registry']
    selection=[b['pair_id'] for b in registry['bindings'] if b['profile'].startswith('generated_') and b['pair_id']==b['reference_pair_id']]
    live={p:sha(ROOT/p) for profile in registry['profiles'].values() for p in profile['source_sha256']}
    checked=preflight(registry,selection,live)
    return {'kind':'common_generated_qualification_v1','preflight':checked,'expected_kinds':['clean_observation','clean_observation'],
            'pair_timeout_s':PAIR_TIMEOUT_S,'outer_timeout_s':OUTER_TIMEOUT_S,'automatic_repeats':False,
            'resume':False,'new_primary_samples':0,'primary_freeze_complete':False}

def drive(execute,checkpoint):
    p=plan();r={'status':'running','plan_sha256':digest(p),'started':[],'completed':[],
        'decisions':[],'new_primary_samples':0,'primary_freeze_complete':False}
    checkpoint(deepcopy(r))
    try:
        for job,expected in zip(p['preflight']['campaign']['schedule']['initial_jobs'],p['expected_kinds']):
            r['started'].append(job['job_id']);checkpoint(deepcopy(r));t=execute(deepcopy(job))
            require(t['outcome']['job_id']==job['job_id'],'Common job identity differs')
            action=decision(t);r['completed'].append(job['job_id'])
            r['decisions'].append({'job_id':job['job_id'],'kind':t['kind'],**action,'repeat_dispatched':False})
            if action['action']=='halt' or t['kind']!=expected:
                r['status']='halted_terminal_outcome';checkpoint(deepcopy(r));return r
            checkpoint(deepcopy(r))
        r['status']='completed_bounded_diagnostic';checkpoint(deepcopy(r));return r
    except BaseException as error:
        r.update(status='halted_executor_error',error_type=type(error).__name__,error=str(error));checkpoint(deepcopy(r));raise
