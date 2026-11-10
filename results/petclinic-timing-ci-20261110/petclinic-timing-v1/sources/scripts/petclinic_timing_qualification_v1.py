"""Six fixed exposed control pairs; initial attempts only, no resume or repeats."""
from copy import deepcopy
from petclinic_timed_jobs_v4 import contract
from mixed_interface.repetition import require,digest
from mixed_interface.terminal_outcomes import decision,POLICY_SHA256
SELECTION=(('owner_required','owner_telephone_10','clean_observation'),('owner_required','owner_omit_firstName','matched_rejection'),
           ('pets','pet_valid','clean_observation'),('pets','pet_omit_name','matched_rejection'),
           ('visits','visit_valid','clean_observation'),('visits','visit_omit_date','matched_rejection'))
PAIR_TIMEOUT_S=120
OUTER_TIMEOUT_S=900

def plan():
    slots=[]
    for i,(batch,cid,expected) in enumerate(SELECTION):
        job=next(j for j in contract(batch)['plan']['schedule']['initial_jobs'] if j['pair_id']==cid)
        slots.append({'slot_id':f'cost-{i:03d}','batch':batch,'job':job,'expected_kind':expected})
    require(len(slots)*PAIR_TIMEOUT_S+150<OUTER_TIMEOUT_S,'Qualification exceeds budget')
    return {'kind':'exposed_petclinic_timing_qualification_v1','slots':slots,'pair_timeout_s':PAIR_TIMEOUT_S,
            'outer_timeout_s':OUTER_TIMEOUT_S,'automatic_repeats':False,'resume':False,'primary_freeze_complete':False}

def drive(execute,checkpoint):
    p=plan();r={'status':'running','plan_sha256':digest(p),'terminal_policy_sha256':POLICY_SHA256,
        'started_slots':[],'completed_slots':[],'decisions':[],'new_primary_samples':0,'primary_freeze_complete':False}
    checkpoint(deepcopy(r))
    try:
        for slot in p['slots']:
            r['started_slots'].append(slot['slot_id']);checkpoint(deepcopy(r));v=execute(deepcopy(slot));t=v['terminal']
            require(t['outcome']['job_id']==slot['job']['job_id'],'Result job differs')
            action=decision(t)
            if t['kind']!=slot['expected_kind']:action={**action,'action':'halt'}
            r['completed_slots'].append(slot['slot_id']);r['decisions'].append({'slot_id':slot['slot_id'],'kind':t['kind'],**action,'repeat_dispatched':False})
            if action['action']=='halt':r['status']='halted_terminal_outcome';checkpoint(deepcopy(r));return r
            checkpoint(deepcopy(r))
        r['status']='completed_bounded_diagnostic';checkpoint(deepcopy(r));return r
    except BaseException as e:
        r.update(status='halted_executor_error',error_type=type(e).__name__,error=str(e));checkpoint(deepcopy(r));raise
