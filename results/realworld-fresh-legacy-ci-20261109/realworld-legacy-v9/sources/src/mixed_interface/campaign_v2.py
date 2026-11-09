"""Versioned driver and planner sharing one terminal policy; no resume or replacement."""
from copy import deepcopy
from . import repetition as v1
from .terminal_outcomes import POLICY_SHA256, decision, observation_signature, validate


def build_plan(pairs):
    core = {'schema_version': 2, 'kind': 'terminal_campaign_plan', 'terminal_policy_sha256': POLICY_SHA256,
            'schedule': v1.build_plan(pairs), 'primary_freeze_complete': False}
    return {**core, 'plan_sha256': v1.digest(core)}


def validate_plan(plan):
    v1.require(build_plan(plan['schedule']['pairs']) == plan, 'Campaign plan or terminal policy differs')


def followups(plan, outcomes):
    validate_plan(plan)
    expected = [j['job_id'] for j in plan['schedule']['initial_jobs']]
    for o in outcomes: validate(o)
    v1.require([o['outcome']['job_id'] for o in outcomes] == expected[:len(outcomes)], 'Initial outcomes duplicated, reordered or foreign')
    base = {'plan_sha256': plan['plan_sha256'], 'initial_outcomes_sha256': v1.digest(outcomes),
            'preserve_initial_attempt': True, 'resume_allowed': False, 'jobs': [], 'triggers': {}}
    if any(decision(o)['action'] == 'halt' for o in outcomes):
        return {**base, 'status': 'halted_terminal_outcome'}
    if len(outcomes) != len(expected): return {**base, 'status': 'halted_incomplete_sweep'}
    pairs = plan['schedule']['pairs']; by_id = {p['pair_id']: p for p in pairs}
    jobs = []; triggers = {}
    for index, (p, o) in enumerate(zip(pairs, outcomes)):
        if not decision(o)['repeat']: continue
        triggers[p['pair_id']] = [o['kind']]
        for repetition in (2, 3):
            jobs.append(v1.job(p, f'followup-{index:03d}-r{repetition}', 'candidate_repeat', p['pair_id'], repetition))
            jobs.append(v1.job(by_id[p['reference_control']], f'control-{index:03d}-r{repetition}', 'reference_control', p['pair_id'], repetition))
    return {**base, 'status': 'planned', 'jobs': jobs, 'triggers': triggers}


def summarize(plan, initial, repeated):
    schedule = followups(plan, initial)
    v1.require(schedule['status'] == 'planned', 'Halted campaign cannot be summarized as repeats')
    expected = [j['job_id'] for j in schedule['jobs']]
    for o in repeated: validate(o)
    v1.require([o['outcome']['job_id'] for o in repeated] == expected[:len(repeated)], 'Repeats duplicated, reordered or foreign')
    observed = {o['outcome']['job_id']: o for o in repeated}
    originals = dict(zip([p['pair_id'] for p in plan['schedule']['pairs']], initial))
    rows = []
    for p in plan['schedule']['pairs']:
        if p['pair_id'] not in schedule['triggers']: continue
        jobs = [j for j in schedule['jobs'] if j['target_pair_id'] == p['pair_id']]
        candidates = [originals[p['pair_id']]] + [observed[j['job_id']] for j in jobs if j['role'] == 'candidate_repeat' and j['job_id'] in observed]
        controls = [originals[p['reference_control']]] + [observed[j['job_id']] for j in jobs if j['role'] == 'reference_control' and j['job_id'] in observed]
        complete = len(candidates) == len(controls) == 3
        semantic = complete and all(decision(o)['semantic_evidence_complete'] for o in candidates + controls)
        controls_pass = all(o['kind'] == 'clean_observation' for o in controls)
        variable = len({v1.digest(observation_signature(o)) for o in candidates}) > 1
        status = ('incomplete_repeats' if not complete else 'unresolved_execution' if not semantic else
                  'unresolved_control_failure' if not controls_pass else 'variable_observations' if variable else 'stable_observations')
        rows.append({'pair_id': p['pair_id'], 'status': status, 'candidate_attempts_observed': len(candidates),
                     'control_attempts_observed': len(controls), 'variability_observed': variable,
                     'terminal_kinds': [o['kind'] for o in candidates], 'all_attempts_retained': True,
                     'defect_adjudicated': False})
    return {'status': 'complete' if len(repeated) == len(expected) else 'incomplete', 'pairs': rows,
            'independent_sample_size': None, 'primary_freeze_complete': False}


def drive(plan, execute, checkpoint):
    validate_plan(plan)
    state = {'schema_version': 2, 'status': 'running', 'plan_sha256': plan['plan_sha256'],
             'terminal_policy_sha256': POLICY_SHA256, 'initial': [], 'repeated': [], 'dispatches': [],
             'primary_freeze_complete': False}
    def run(job, phase):
        state['dispatches'].append({'job': deepcopy(job), 'phase': phase, 'status': 'started'})
        checkpoint(deepcopy(state))
        try:
            result = execute(deepcopy(job)); validate(result)
            v1.require(result['outcome']['job_id'] == job['job_id'], 'Executor returned another job')
            state[phase].append(deepcopy(result))
            dispatch = state['dispatches'][-1]
            dispatch.update(status='recorded', decision=decision(result))
            if dispatch['decision']['action'] == 'halt':
                state['status'] = 'halted_terminal_outcome'; state['halt_reason'] = result['kind']
            checkpoint(deepcopy(state))
            return state['status'] == 'running'
        except BaseException as error:
            state['status'] = 'halted_executor_error'
            state['dispatches'][-1]['error'] = type(error).__name__ + ': ' + str(error)
            checkpoint(deepcopy(state)); raise
    for job in plan['schedule']['initial_jobs']:
        if not run(job, 'initial'): return state
    schedule = followups(plan, state['initial']); state['followup_plan'] = schedule
    checkpoint(deepcopy(state))
    for job in schedule['jobs']:
        if not run(job, 'repeated'): return state
    state['repeat_summary'] = summarize(plan, state['initial'], state['repeated'])
    state['status'] = 'completed_observations'; checkpoint(deepcopy(state))
    return state
