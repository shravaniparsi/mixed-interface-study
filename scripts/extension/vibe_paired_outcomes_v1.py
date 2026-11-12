"""Compare aggregate scoring with identified test transitions, retaining uncertainty."""


import json


def parse_event_text(text):
    # JSON strings may legally contain Unicode line/paragraph separators.
    # JSONL records are delimited by ASCII LF, not str.splitlines().
    events = []
    malformed = []
    for number, line in enumerate(text.split('\n'), 1):
        if not line:
            continue
        try:
            events.append(json.loads(line))
        except json.JSONDecodeError as error:
            malformed.append({'line': number, 'message': error.msg})
    return events, malformed


def aggregate_kill(before, mutant):
    return mutant['passed'] < before['passed'] or mutant['failures'] > before['failures'] or mutant['errors'] > before['errors']


def node_outcomes(events):
    collections = [e['nodeids'] for e in events if e['kind'] == 'collection']
    finishes = [e for e in events if e['kind'] == 'session_finish']
    if len(collections) != 1 or len(finishes) != 1:
        return None
    ids = collections[0]
    assert len(ids) == len(set(ids))
    reports = {key: {} for key in ids}
    for event in events:
        if event['kind'] != 'test_report':
            continue
        key = event['test_nodeid']; stage = event['when']
        assert key in reports and stage not in reports[key]
        reports[key][stage] = event
    result = {}
    for key, stages in reports.items():
        failed = [r for r in stages.values() if r['outcome'] == 'failed']
        if failed:
            kind = 'error' if any(r['when'] != 'call' for r in failed) else 'failed'
        elif any(r['outcome'] == 'skipped' or r.get('wasxfail') for r in stages.values()):
            kind = 'skipped'
        elif set(stages) == {'setup', 'call', 'teardown'} and all(r['outcome'] == 'passed' for r in stages.values()):
            kind = 'passed'
        else:
            kind = 'incomplete'
        result[key] = {'outcome': kind, 'failed_stages': [{'when': r['when'], 'exception': r.get('exception'), 'longrepr': r.get('longrepr', '')} for r in failed]}
    return result


def compare(before, mutant, after, before_counts, mutant_counts):
    result = {'aggregate_kill': aggregate_kill(before_counts, mutant_counts), 'paired_evidence_qualified': False}
    if before is None or mutant is None or after is None:
        return {**result, 'reason': 'missing_per_test_evidence'}
    if not before or set(before) != set(mutant) or set(before) != set(after):
        return {**result, 'reason': 'collection_mismatch_or_empty'}
    if any(r['outcome'] == 'incomplete' for group in [before, mutant, after] for r in group.values()):
        return {**result, 'reason': 'incomplete_test_stages'}
    unstable = [key for key in before if before[key]['outcome'] != after[key]['outcome']]
    if unstable:
        return {**result, 'reason': 'unstable_original_controls', 'unstable_nodes': unstable}
    passing = [key for key in before if before[key]['outcome'] == after[key]['outcome'] == 'passed']
    if not passing:
        return {**result, 'reason': 'no_stably_passing_original_tests'}
    new = [key for key in passing if mutant[key]['outcome'] in ['failed', 'error']]
    skipped = [key for key in passing if mutant[key]['outcome'] == 'skipped']
    if skipped:
        return {**result, 'reason': 'previously_passing_test_skipped', 'skipped_nodes': skipped}
    explicit = [key for key in new if any(s['when'] == 'call' and s['exception'] == 'AssertionError' for s in mutant[key]['failed_stages'])]
    return {**result, 'paired_evidence_qualified': True, 'stably_passing_original_tests': len(passing), 'new_failure_nodes': new, 'new_assertion_failure_nodes': explicit, 'identified_new_failure': bool(new), 'count_rule_disagrees_with_new_failure': result['aggregate_kill'] != bool(new)}
