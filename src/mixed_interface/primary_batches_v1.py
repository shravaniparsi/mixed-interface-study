"""Independent, immutable diagnostic units; preserve terminal halts within each unit."""
from copy import deepcopy
from .repetition import require,digest
from .terminal_outcomes import decision,validate,observation_signature


def application(profile):return 'petclinic' if profile=='petclinic_v4' else 'quartz' if profile=='quartz_v2' else 'realworld'

def attempt(binding,repetition,control=False):
    base=binding['initial_attempt_id'];runtime=binding['reference_runtime'] if control else binding['runtime']
    require(runtime is not None,'Singleton has no paired control')
    return {'attempt_id':f'{base}-'+('control' if control else 'candidate')+f'-r{repetition}',
            'target_pair_id':binding['entry']['pair_id'],'entry_pair_id':binding['reference_pair_id'] if control else binding['entry']['pair_id'],
            'role':'reference_control' if control else 'candidate','repetition':repetition,
            'entry_kind':'pair' if control else binding['entry_kind'],'runtime':deepcopy(runtime),'binding_sha256':binding['binding_sha256']}

def batch(binding,repetition):
    jobs=[attempt(binding,repetition)]
    if binding['entry_kind']=='pair' and binding['reference_pair_id']!=binding['entry']['pair_id']:
        jobs.append(attempt(binding,repetition,True))
    return {'batch_id':binding['initial_attempt_id']+f'-r{repetition}','target_pair_id':binding['entry']['pair_id'],
            'application':application(binding['runtime']['profile']),'repetition':repetition,'jobs':jobs,
            'application_timeout_s':900,'hosted_job_timeout_minutes':30,'replace_or_resume':False}

def plan(catalog):
    bindings=catalog['bindings'];require(len(bindings)==75 and len({b['entry']['pair_id'] for b in bindings})==75,'Catalog differs')
    for b in bindings:require(b['binding_sha256']==digest({k:v for k,v in b.items() if k!='binding_sha256'}),'Binding hash differs')
    initial=[batch(b,1) for b in bindings]
    potential={b['entry']['pair_id']:[batch(b,r) for r in (2,3)] for b in bindings if b['entry_kind']=='pair'}
    core={'kind':'independent_primary_diagnostic_units_v1','catalog_sha256':digest(catalog),'initial_batches':initial,
          'potential_followup_batches':potential,'repeat_policy':'terminal_v2_repeat_eligible_with_clean_same_instrumentation_reference',
          'halt_scope':'current independent diagnostic unit; no resume or replacement; other predeclared units retain independent environments',
          'primary_freeze_complete':False,'execution_authorized':False}
    return {**core,'plan_sha256':digest(core)}

def drive(unit,execute,checkpoint):
    state={'batch_id':unit['batch_id'],'status':'running','started':[],'observations':[],'independent_sample_size':None}
    checkpoint(deepcopy(state))
    try:
        for job in unit['jobs']:
            state['started'].append(job['attempt_id']);checkpoint(deepcopy(state));value=execute(deepcopy(job))
            require(value['attempt_id']==job['attempt_id'] and value['entry_kind']==job['entry_kind'],'Attempt identity differs')
            state['observations'].append(deepcopy(value))
            if value['entry_kind']=='pair':
                validate(value['terminal']);require(value['terminal']['outcome']['job_id']==job['attempt_id'],'Terminal identity differs')
                if decision(value['terminal'])['action']=='halt':
                    state['status']='halted_terminal_outcome';checkpoint(deepcopy(state));return state
            else:require('terminal' not in value and value['paired_comparison_eligible'] is False,'Singleton promoted')
            checkpoint(deepcopy(state))
        state['status']='completed_observations';checkpoint(deepcopy(state));return state
    except BaseException as error:
        state.update(status='halted_executor_error',error_type=type(error).__name__,error=str(error));checkpoint(deepcopy(state));raise


def candidate_and_control(unit,record):
    require(record['batch_id']==unit['batch_id'],'Foreign batch')
    require(record['started']==[j['attempt_id'] for j in unit['jobs']][:len(record['started'])],'Foreign dispatch sequence')
    require([v['attempt_id'] for v in record['observations']]==record['started'][:len(record['observations'])],'Foreign observation sequence')
    if record['status']!='completed_observations':return None,None
    require(len(record['observations'])==len(unit['jobs']),'Incomplete batch marked complete')
    if unit['jobs'][0]['entry_kind']=='singleton':return None,None
    candidate=record['observations'][0]['terminal'];control=record['observations'][-1]['terminal']
    validate(candidate);validate(control)
    return candidate,control


def followups(value,initial,repetition,previous=None):
    require(repetition in (2,3),'Unknown repetition')
    expected={b['batch_id']:b for b in value['initial_batches']}
    require(set(initial)==set(expected),'Initial batch inventory incomplete or foreign')
    selected=[];blocked=[]
    for bid,unit in expected.items():
        candidate,control=candidate_and_control(unit,initial[bid]);pid=unit['target_pair_id']
        if candidate is None or not decision(candidate)['repeat']:continue
        if control['kind']!='clean_observation':blocked.append({'pair_id':pid,'reason':'initial_reference_not_clean'});continue
        planned=value['potential_followup_batches'][pid]
        if repetition==3:
            require(previous is not None,'Second repetition results required')
            second=planned[0];require(second['batch_id'] in previous,'Missing second repetition')
            a,b=candidate_and_control(second,previous[second['batch_id']])
            if a is None or b['kind']!='clean_observation':blocked.append({'pair_id':pid,'reason':'second_repetition_halted_or_control_failed'});continue
        selected.append(deepcopy(planned[repetition-2]))
    if repetition==3:
        second=followups(value,initial,2)['batches'];require(set(previous)=={b['batch_id'] for b in second},'Second repetition inventory differs')
    return {'repetition':repetition,'batches':selected,'blocked':blocked,'initial_observations_sha256':digest(initial),
            'previous_observations_sha256':digest(previous) if previous is not None else None,'replacement_allowed':False}
