"""Pure paired-repeat planning. No applications, retries, or defect adjudication."""
from copy import deepcopy
import hashlib
import json


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False).encode()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def build_plan(pairs):
    pairs = deepcopy(pairs)
    require(bool(pairs), 'Empty pair inventory')
    ids = [p['pair_id'] for p in pairs]
    require(len(set(ids)) == len(ids), 'Duplicate pair ID')
    controls = {}
    for p in pairs:
        require(p['producer_interface'] in ('api', 'ui') and set(p['case_ids']) == {'api', 'ui'}, 'Invalid route')
        require(len(set(p['case_ids'].values())) == 2, 'Branches must have distinct case IDs')
        if p['intervention'] == 'route_only':
            require(p.get('mutation') is None, 'Mutated reference control')
            key = (p['workflow_id'], p['producer_interface'])
            require(key not in controls, 'Ambiguous reference control')
            controls[key] = p['pair_id']
        else:
            require(p['intervention'] == 'payload_mutation', 'Unknown intervention')
    jobs = []
    for index, p in enumerate(pairs):
        key = (p['workflow_id'], p['producer_interface'])
        require(key in controls, 'Missing workflow/producer reference control')
        p['reference_control'] = controls[key]
        p['consumer_order'] = ['api', 'ui'] if index % 2 == 0 else ['ui', 'api']
        jobs.append(job(p, f'initial-{index:03d}', 'initial', p['pair_id'], 1))
    core = {'schema_version': 1, 'kind': 'paired_repeat_plan', 'pairs': pairs, 'initial_jobs': jobs,
            'extra_candidate_attempts': 2, 'resume': False, 'primary_freeze_complete': False,
            'scope': 'Planning only; adapter integration and primary qualification remain required'}
    return {**core, 'plan_sha256': digest(core)}


def job(pair, job_id, role, target, repetition):
    return {'job_id': job_id, 'pair_id': pair['pair_id'], 'target_pair_id': target,
            'role': role, 'repetition': repetition,
            'branches': [{'case_id': pair['case_ids'][c], 'continuation': c, 'fresh_reset_required': True}
                         for c in pair['consumer_order']]}


def validate_plan(plan):
    require(digest({k: v for k, v in plan.items() if k != 'plan_sha256'}) == plan['plan_sha256'], 'Plan hash differs')
    # Rebuilding also validates semantics; a caller cannot just rehash an altered schedule.
    require(build_plan(plan['pairs']) == plan, 'Plan schedule or policy differs')


def validate_outcome(outcome):
    require(set(outcome) == {'job_id', 'execution', 'prefix', 'channel_discrepancy', 'check_failure',
                             'cleanup_confirmed', 'observation_signature'}, 'Unknown/missing outcome fields')
    require(outcome['execution'] in ('complete', 'incomplete'), 'Unknown execution state')
    require(outcome['prefix'] in ('accepted', 'rejected', 'mixed', 'unobserved'), 'Unknown prefix state')
    require(type(outcome['cleanup_confirmed']) is bool, 'Cleanup must be explicit')
    for key in ('channel_discrepancy', 'check_failure'):
        require(type(outcome[key]) is bool or outcome[key] is None, 'Invalid diagnostic flag')
    if outcome['execution'] == 'complete':
        require(all(type(outcome[k]) is bool for k in ('channel_discrepancy', 'check_failure')), 'Missing complete-run diagnostics')
        require(outcome['prefix'] != 'unobserved', 'Complete execution lacks prefix evidence')
        require(isinstance(outcome['observation_signature'], dict) and outcome['observation_signature'], 'Missing observation signature')
    else:
        require(outcome['observation_signature'] is None or isinstance(outcome['observation_signature'], dict), 'Invalid partial signature')
    digest(outcome)  # Reject non-finite JSON numbers.


def reasons(outcome):
    validate_outcome(outcome)
    return [name for name, applies in (
        ('channel_discrepancy', outcome['channel_discrepancy'] is True),
        ('check_failure', outcome['check_failure'] is True),
        ('unresolved_execution', outcome['execution'] == 'incomplete' or outcome['prefix'] == 'mixed')) if applies]


def followups(plan, outcomes):
    validate_plan(plan)
    expected = [j['job_id'] for j in plan['initial_jobs']]
    actual = [o['job_id'] for o in outcomes]
    require(actual == expected[:len(actual)], 'Initial outcomes are duplicated, reordered or foreign')
    for o in outcomes:
        validate_outcome(o)
    base = {'plan_sha256': plan['plan_sha256'], 'initial_outcomes_sha256': digest(outcomes),
            'preserve_initial_attempt': True, 'resume_allowed': False, 'jobs': [], 'triggers': {}}
    if any(not o['cleanup_confirmed'] for o in outcomes):
        return {**base, 'status': 'halted_unconfirmed_cleanup'}
    if len(actual) != len(expected):
        return {**base, 'status': 'halted_incomplete_sweep'}
    by_id = {p['pair_id']: p for p in plan['pairs']}
    jobs = []; triggers = {}
    for index, (p, o) in enumerate(zip(plan['pairs'], outcomes)):
        why = reasons(o)
        if not why:
            continue
        triggers[p['pair_id']] = why
        for repetition in (2, 3):
            jobs.append(job(p, f'followup-{index:03d}-r{repetition}', 'candidate_repeat', p['pair_id'], repetition))
            control = by_id[p['reference_control']]
            jobs.append(job(control, f'control-{index:03d}-r{repetition}', 'reference_control', p['pair_id'], repetition))
    return {**base, 'status': 'planned', 'jobs': jobs, 'triggers': triggers}


def signature(outcome):
    return {k: outcome[k] for k in ('execution', 'prefix', 'channel_discrepancy', 'check_failure', 'observation_signature')}


def clean_control(outcome):
    return (outcome['execution'] == 'complete' and outcome['prefix'] == 'accepted'
            and outcome['cleanup_confirmed'] and not outcome['check_failure'] and not outcome['channel_discrepancy'])


def summarize(plan, initial, repeated):
    schedule = followups(plan, initial)
    require(schedule['status'] == 'planned', 'Halted campaign cannot be summarized as repeats')
    expected = [j['job_id'] for j in schedule['jobs']]
    require([o['job_id'] for o in repeated] == expected[:len(repeated)], 'Repeat outcomes are duplicated, reordered or foreign')
    for o in repeated:
        validate_outcome(o)
    observed = dict(zip(expected, repeated)); originals = dict(zip([p['pair_id'] for p in plan['pairs']], initial))
    rows = []
    for p in plan['pairs']:
        if p['pair_id'] not in schedule['triggers']:
            continue
        jobs = [j for j in schedule['jobs'] if j['target_pair_id'] == p['pair_id']]
        candidates = [originals[p['pair_id']]] + [observed[j['job_id']] for j in jobs if j['role'] == 'candidate_repeat' and j['job_id'] in observed]
        controls = [originals[p['reference_control']]] + [observed[j['job_id']] for j in jobs if j['role'] == 'reference_control' and j['job_id'] in observed]
        complete = len(candidates) == 3 and len(controls) == 3
        evidence_complete = complete and all(o['execution'] == 'complete' and o['prefix'] in ('accepted', 'rejected') and o['cleanup_confirmed'] for o in candidates+controls)
        controls_pass = len(controls) == 3 and all(clean_control(o) for o in controls)
        variable = len({digest(signature(o)) for o in candidates}) > 1
        state = ('incomplete_repeats' if not complete else 'unresolved_execution' if not evidence_complete
                 else 'unresolved_control_failure' if not controls_pass else 'variable_observations' if variable else 'stable_observations')
        rows.append({'pair_id': p['pair_id'], 'status': state, 'candidate_attempts_observed': len(candidates),
                     'control_attempts_observed': len(controls), 'variability_observed': variable,
                     'defect_adjudicated': False, 'all_attempts_retained': True})
    return {'status': 'complete' if len(repeated) == len(expected) else 'incomplete', 'pairs': rows,
            'independent_sample_size': None, 'primary_freeze_complete': False}
