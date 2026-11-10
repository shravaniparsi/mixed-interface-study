"""Bounded prospective reference-comparison qualification; no automatic dispatch."""
from copy import deepcopy
from realworld_legacy_jobs_v8 import selection, plan_for as worker_plan, validate_job
from mixed_interface.repetition import require, digest
from mixed_interface.terminal_outcomes import POLICY, POLICY_SHA256, decision

JOB_TIMEOUT_S = 240
OUTER_TIMEOUT_S = 1920


FRESH_IDS = ('article-valid','article-update-unique-partial','article-title-whitespace',
             'article-update-duplicate-partial','article-update-duplicate-full',
             'comment-native-control','profile-native-control')


def plan_for(registry):
    source=worker_plan(registry)
    jobs=[j for j in source['jobs'] if j['candidate_id'] in FRESH_IDS]
    require(tuple(j['candidate_id'] for j in jobs)==FRESH_IDS,'Fresh selection/order differs')
    return {'kind':'exposed_reference_comparison_qualification_v10','jobs':jobs,
            'counts':{'paired_references':2,'candidate_pairs':3,'native_singletons':2,'branch_slots':12},
            'retained_replay_source':'42708069641','prior_attempt_resumed':False,
            'comparison_bridge':'scripts/realworld_reference_terminal_v2.py',
            'primary_freeze_complete':False,'automatic_repeats':False}


def outcome_decision(job, value):
    require(value.get('entry_kind') == job['entry_kind'], 'Result cardinality differs')
    if job['entry_kind'] == 'pair':
        terminal = value['terminal']; result = decision(terminal)
        require(terminal['outcome']['job_id'] == job['job_id'], 'Result job differs')
        kind = terminal['kind']
    else:
        require(value.get('job_id') == job['job_id'] and value.get('channel_discrepancy') is None
                and value.get('paired_comparison_eligible') is False
                and value.get('primary_freeze_complete') is False, 'Singleton promoted or misbound')
        refs = value.get('evidence_sha256')
        require(isinstance(refs, dict) and bool(refs), 'Singleton evidence missing')
        require(all(isinstance(h, str) and len(h) == 64 and all(c in '0123456789abcdef' for c in h)
                    for h in refs.values()), 'Invalid singleton evidence hash')
        kind = value['branch']['kind']; require(kind in POLICY, 'Unknown singleton terminal')
        action, repeat, complete = POLICY[kind]
        if kind in ('clean_observation', 'completed_mismatch', 'matched_rejection', 'unresolved_policy'):
            require(value['branch'].get('components', {}).get('execution_evidence_complete') is True,
                    'Singleton semantic evidence incomplete')
        result = {'action': action, 'repeat': repeat, 'semantic_evidence_complete': complete}
    # Diagnostic scope has no repeat dispatch, even when the primary policy suggests it.
    if job['candidate_id'] in ('article-valid', 'article-update-unique-partial') and kind != 'clean_observation':
        result = {**result, 'action': 'halt'}
    return {'kind': kind, **result, 'repeat_dispatched': False}


def drive(registry, execute, checkpoint):
    plan = plan_for(registry)
    report = {'status': 'running', 'plan_sha256': digest(plan), 'policy_sha256': POLICY_SHA256,
              'started_jobs': [], 'completed_jobs': [], 'decisions': [],
              'primary_freeze_complete': False, 'new_primary_samples': 0}
    checkpoint(deepcopy(report))
    try:
        for job in plan['jobs']:
            validate_job(job, registry)
            report['started_jobs'].append(job['job_id']); checkpoint(deepcopy(report))
            value = execute(deepcopy(job)); control = outcome_decision(job, value)
            report['completed_jobs'].append(job['job_id']); report['decisions'].append(control)
            if control['action'] == 'halt':
                report['status'] = 'halted_terminal_outcome'; checkpoint(deepcopy(report)); return report
            checkpoint(deepcopy(report))
        report['status'] = 'completed_bounded_diagnostic'; checkpoint(deepcopy(report)); return report
    except BaseException as error:
        report.update(status='halted_executor_error', error_type=type(error).__name__, error=str(error))
        checkpoint(deepcopy(report)); raise
