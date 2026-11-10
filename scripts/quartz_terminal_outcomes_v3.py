"""Source-specific Quartz extraction for terminal contract v2; no application execution."""
import argparse
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sys
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'src'))
from mixed_interface.repetition import digest, require
from mixed_interface.terminal_outcomes import terminal, POLICY
import quartz_repeat_outcomes_v3 as old
reducer = old.reducer


def cleanup_confirmed(run):
    return all(run.get(k, {}).get('ok') is True for k in ('node_cleanup', 'java_cleanup', 'browser_cleanup')) and run.get('browser_process_absent') is True and run.get('application_port_released') is True


def expected_exit(raw):
    return 1 if not raw.get('completed') or (raw.get('intervention') == 'route_only' and raw.get('status') != 'pass') else 0


def transport_valid(raw, run):
    e = run.get('child_exit', {})
    return (type(e.get('code')) is int and e['code'] == expected_exit(raw)
            and not any(e.get(k) for k in ('signal', 'spawn_error', 'exit_unconfirmed')))


def partial_read_issues(raw, run, spec, reduced):
    """Validate a trace-supported read failure after a verified empty reset.

    Missing later observations remain missing; no completion or channel verdict
    is synthesized. The old reducer's structural issues are retained verbatim.
    """
    errors = []
    error = raw.get('error', {}); phase = error.get('phase'); status = error.get('http_status')
    permitted_paths = {'producer_state': {'/quartz-manager/scheduler', '/quartz-manager/jobs', '/quartz-manager/triggers', reducer.JOB_PATH},
                       'continuation': {reducer.JOB_PATH},
                       'final_read': {reducer.JOB_PATH, '/quartz-manager/scheduler', '/quartz-manager/jobs', '/quartz-manager/triggers'}}
    trace = raw.get('trace', [])
    direct = [x for x in trace if isinstance(x, dict) and x.get('source') == 'direct_api'] if isinstance(trace, list) else []
    last = direct[-1] if direct else {}
    if (phase not in permitted_paths or error.get('observation_kind') != 'application_read_response'
        or type(status) is not int or not 100 <= status <= 599 or status == 200
        or last.get('method') != 'GET' or last.get('phase') != phase or last.get('status') != status
        or last.get('path') not in permitted_paths.get(phase, set()) or last.get('request') is not None
        or error.get('message') != f"Native read returned {status} for {last.get('path')}"):
        errors.append('unsupported_application_read_trace')
    if run.get('status') != raw.get('status'): errors.append('result_run_status_mismatch')
    if raw.get('completed') is not False or run.get('completed') is not False:
        errors.append('read_failure_marked_completed')
    initial = raw.get('initial_state', {})
    if initial.get('jobs') != [] or initial.get('triggers') != []:
        errors.append('initial_store_not_empty')
    checks = {x.get('id'): x for x in raw.get('checks', []) if isinstance(x, dict)}
    required = {'initial_state_inactive_scheduler'}
    if raw.get('route', '').startswith('ui-'):
        required |= {'native_create_form', 'native_POST_payload_matches_bound_intent'}
    if phase == 'producer_state' and last.get('path') == reducer.JOB_PATH:
        required |= {'post_producer_state_inactive_scheduler','producer_status'}
        if not isinstance(raw.get('post_producer_state'), dict): errors.append('missing_pre_failure:post_producer_state')
    if phase in ('continuation', 'final_read'):
        required |= {'post_producer_state_inactive_scheduler', 'producer_status',
                     'producer_response_matches_persisted_job', 'producer_business_fields', 'single_stored_resource'}
        if raw.get('accepted_prefix') is not True or raw.get('reached_continuation') is not True:
            errors.append('missing_accepted_progress')
        if raw.get('bindings', {}).get('path') != reducer.JOB_PATH or raw.get('bindings', {}).get('command', {}).get('description') != spec['operations'][1]['input'].get('description'):
            errors.append('invalid_pre_failure_binding')
        for key in ('bindings', 'stored_prefix', 'post_producer_state'):
            if not isinstance(raw.get(key), dict) or not raw[key]: errors.append('missing_pre_failure:' + key)
    if phase == 'final_read':
        required.add('consumer_api_loaded_bound_state' if raw.get('route', '').endswith('-api') else 'consumer_ui_loaded_bound_state')
        continued = raw.get('continuation', {})
        required.add('continuation_status' if continued.get('kind') == 'response' else 'continuation_submitted')
        if continued.get('kind') == 'response' and raw.get('route', '').endswith('-ui'):
            required.add('native_PUT_payload_matches_bound_intent')
    for key in required:
        if key not in checks: errors.append('missing_pre_failure_check:' + key)
    for key in old.GUARDS:
        if key in checks and checks[key].get('scope') == 'requirement' and checks[key].get('passed') is not True:
            errors.append('failed_native_payload_guard:' + key)
    if spec['operations'][0]['interface'] == 'ui':
        if not any(x.get('label') == 'producer_form' for x in raw.get('ui_forms', [])): errors.append('missing_pre_failure_producer_form')
        if not any(x.get('interface') == 'ui' and x.get('phase') == 'producer' and x.get('principal') == raw.get('api_actor') for x in raw.get('actors', [])): errors.append('missing_pre_failure_native_actor')
    # Missing post-failure observations are allowed only as partial evidence.
    allowed_exact = {'result_not_finished', 'run_not_finished', 'result_contains:error',
                     'execution_guard:worker_clean_exit', 'missing_or_unknown_continuation_kind',
                     'accepted_prefix_without_reached_continuation', 'missing_or_unregistered_bound_path',
                     'rejected_prefix_has_continuation_or_missing_stop_record'}
    allowed_prefixes = ('missing_required_check:', 'missing_accepted_prefix_evidence:',
                        'missing_native_form:', 'missing_native_actor_observation:', 'missing_request:')
    for issue in reduced['evidence_issues']:
        if issue in allowed_exact or issue.startswith(allowed_prefixes): continue
        if issue in ('missing_state_evidence:final_state', 'missing_required_state_hash:final_state', 'run_state_hash_mismatch:final_state'): continue
        if phase == 'producer_state' and issue == 'missing_state_evidence:post_producer_state': continue
        errors.append(issue)
    # Authenticate and associate the observed producer request, not merely its summary.
    producer_source = 'direct_api' if spec['operations'][0]['interface'] == 'api' else 'ui_network'
    requests = [x for x in trace if isinstance(x, dict)] if isinstance(trace, list) else []
    if not any(x.get('source') == 'direct_api' and x.get('path') == '/quartz-manager/auth/login' and x.get('status') == 200 for x in requests):
        errors.append('missing_successful_authentication')
    if not any(x.get('source') == 'direct_api' and x.get('path') == '/quartz-manager/auth/whoami' and x.get('status') == 200 and x.get('response') == raw.get('api_actor') for x in requests):
        errors.append('missing_authenticated_actor_trace')
    producer = raw.get('producer', {})
    if producer.get('kind') == 'response' and not any(x.get('source') == producer_source and x.get('method') == 'POST' and x.get('path') == reducer.JOB_PATH and x.get('request') == spec['operations'][0]['input'] and x.get('status') == producer.get('status') for x in requests):
        errors.append('missing_registered_producer_trace')
    return sorted(set(errors))


def classify_branch(raw, run, spec):
    if not cleanup_confirmed(run): return {'kind': 'cleanup_unconfirmed', 'issues': ['cleanup_not_confirmed']}
    if run.get('timed_out') is True: return {'kind': 'case_timeout', 'issues': ['case_deadline']}
    if raw.get('interruption') or run.get('status') == 'interrupted' or raw.get('status') == 'interrupted':
        return {'kind': 'interrupted', 'issues': ['interruption']}
    if not raw: return {'kind': 'missing_evidence', 'issues': ['missing_result']}
    if raw.get('status') == 'adapter_or_environment_error' or run.get('status') in ('runner_error', 'child_exit_error'):
        return {'kind': 'environment_failure', 'issues': ['adapter_or_runner_error']}
    if not transport_valid(raw, run): return {'kind': 'environment_failure', 'issues': ['unexpected_worker_exit']}
    # The pinned adapter intentionally exits 1 for completed non-pass controls.
    # Normalize only that transport guard; never alter stored raw evidence.
    normalized = deepcopy(run); normalized['child_exit'] = {'code': 0, 'signal': None}
    reduced = reducer.reduce_case(raw, normalized, spec, run_complete=True)
    if raw.get('status') == 'application_response_error':
        issues = partial_read_issues(raw, run, spec, reduced)
        return {'kind': 'missing_evidence' if issues else 'application_response_failure',
                'issues': issues, 'components': reduced, 'actual_child_exit': run['child_exit']}
    if not reduced['execution_evidence_complete']:
        environment = any(x.startswith(('execution_condition_check_failed:', 'execution_guard:', 'unresolved_browser_evidence:')) for x in reduced['evidence_issues'])
        return {'kind': 'environment_failure' if environment else 'missing_evidence', 'issues': reduced['evidence_issues'], 'components': reduced}
    guards = [c for p in reduced['components'].values() for c in p['checks'] if c['id'] in old.GUARDS and c['scope'] == 'requirement']
    if any(c['passed'] is False for c in guards): return {'kind': 'environment_failure', 'issues': ['native_payload_guard_failed'], 'components': reduced}
    failed = any(p['mismatch_observed'] for name,p in reduced['components'].items() if name not in ('environment_reset_cleanup', 'unresolved_policy'))
    kind = 'completed_mismatch' if failed else 'unresolved_policy' if reduced['policy_unresolved'] else 'clean_observation' if raw['accepted_prefix'] else 'matched_rejection'
    return {'kind': kind, 'issues': [], 'components': reduced, 'actual_child_exit': run['child_exit']}


def pair_terminal(job, branches, registered, evidence):
    classified = {c: classify_branch(raw, run, registered[c]) for c,(raw,run) in branches.items()}
    normalized = {}
    for c,(raw,run) in branches.items():
        r = deepcopy(run)
        if transport_valid(raw,run): r['child_exit'] = {'code':0,'signal':None}
        normalized[c] = (raw,r)
    result = old.pair_outcome(job, normalized, registered, run_complete=True)
    o = result['outcome']; o['cleanup_confirmed'] = bool(branches) and all(cleanup_confirmed(run) for raw,run in branches.values())
    kinds = [v['kind'] for v in classified.values()]
    # Policy-scoped guard observations do not invalidate otherwise complete pairs.
    completed_kinds = {'clean_observation','matched_rejection','completed_mismatch','unresolved_policy'}
    if set(branches) == {'api','ui'} and all(k in completed_kinds for k in kinds) and all(result['comparability'].values()) and o['prefix'] in ('accepted','rejected'):
        o['execution'] = 'complete'
        o['check_failure'] = 'completed_mismatch' in kinds
        o['channel_discrepancy'] = False
        if o['prefix'] == 'accepted':
            signals = [classified[c]['components']['components']['assigned_api_continuation' if c == 'api' else 'assigned_native_continuation']['mismatch_observed'] for c in ('api','ui')]
            o['channel_discrepancy'] = signals[0] != signals[1]
    precedence = ('cleanup_unconfirmed', 'interrupted', 'case_timeout', 'environment_failure', 'missing_evidence')
    kind = next((k for k in precedence if k in kinds), None)
    if kind is None and set(branches) != {'api','ui'}: kind = 'missing_evidence'
    if not o['cleanup_confirmed']: kind = 'cleanup_unconfirmed'
    if kind is None:
        gates = result['comparability']
        if not all(gates.get(k) for k in ('same_initial_state','same_actor','independent_jvm','same_observed_prefix_command')):
            kind = 'environment_failure'
        elif 'application_response_failure' in kinds: kind = 'application_response_failure'
        elif o['execution'] != 'complete': kind = 'incomparable_observation'
        elif o['check_failure'] or o['channel_discrepancy']: kind = 'completed_mismatch'
        elif 'unresolved_policy' in kinds: kind = 'unresolved_policy'
        else: kind = 'matched_rejection' if o['prefix'] == 'rejected' else 'clean_observation'
    if kind in ('application_response_failure','incomparable_observation'):
        o.update(execution='incomplete',check_failure=None,channel_discrepancy=None)
    # Include the failure response itself in variability signatures, without channel credit.
    o['observation_signature']['terminal_branches'] = {c: {'kind':v['kind'], 'error':branches[c][0].get('error')} for c,v in classified.items()}
    result['branch_classifications'] = classified
    result['terminal'] = terminal(o, kind, evidence)
    return result


def read_job(directory, job, registry, expected_runner_sha):
    directory = Path(directory)
    def read(p): return json.loads(p.read_bytes())
    def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
    summary = read(directory/'summary.json')
    require(bool(summary.get('ended_at')) and summary.get('status') in ('pass','completed_observations','incomplete'), 'Pair runner lacks terminal summary')
    evidence = {}
    for filename, expected in [('executed-adapter.mjs',reducer.ADAPTER_SHA256),('executed-registry.json',reducer.REGISTRY_SHA256),('executed-runner.mjs',expected_runner_sha)]:
        require(sha(directory/filename) == expected, 'Source mismatch: '+filename); evidence[filename] = expected
    require(read(directory/'executed-registry.json') == registry, 'Registry content differs')
    ids = [b['case_id'] for b in job['branches']]
    order = read(directory/'executed-case-order.json')
    require(order == {'schema_version':1,'scope':'quartz_repeat_pair','registry_sha256':reducer.REGISTRY_SHA256,'case_ids':ids}, 'Order differs')
    require(summary['ordering']['case_ids'] == ids and summary['case_count'] == 2 and sha(directory/'executed-case-order.json') == summary['ordering']['order_file_sha256'], 'Selection differs')
    require([e['case_id'] for e in summary['cases']] == ids[:len(summary['cases'])], 'Branch order differs')
    specs = {c['case_id']:c for c in registry['cases']}; branches = {}; registered = {b['continuation']:specs[b['case_id']] for b in job['branches']}; leaves = set()
    for entry in summary['cases']:
        leaf = Path(entry['evidence_directory']).name
        require(leaf not in leaves and leaf not in ('','.','..') and (directory/leaf).resolve().parent == directory.resolve(), 'Evidence path differs')
        leaves.add(leaf); run = read(directory/leaf/'run.json'); require(run == entry, 'Summary/run differs')
        p = directory/leaf/'result.json'; raw = read(p) if p.exists() else {}
        if p.exists(): evidence[leaf+'/result.json'] = sha(p)
        evidence[leaf+'/run.json'] = sha(directory/leaf/'run.json')
        channel = specs[entry['case_id']]['operations'][1]['interface']; require(channel not in branches, 'Duplicate channel')
        branches[channel] = (raw,run)
    evidence['summary.json'] = sha(directory/'summary.json')
    result = pair_terminal(job, branches, registered, evidence)
    if summary.get('interruption') and result['outcome']['cleanup_confirmed']:
        result['terminal'] = terminal(result['outcome'], 'interrupted', evidence)
    elif summary.get('classification_error') and result['outcome']['cleanup_confirmed']:
        result['terminal'] = terminal(result['outcome'], 'environment_failure', evidence)
        result['runner_classification_error'] = summary['classification_error']
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(); parser.add_argument('--branch',type=Path,required=True); parser.add_argument('--run',type=Path,required=True); parser.add_argument('--registry',type=Path,required=True)
    args = parser.parse_args(); run = json.loads(args.run.read_bytes()); raw = json.loads(args.branch.read_bytes()) if args.branch.exists() else {}
    require(hashlib.sha256(args.registry.read_bytes()).hexdigest() == reducer.REGISTRY_SHA256, 'Registry source differs')
    require(hashlib.sha256((ROOT/'scripts/quartz_generated_case_v3.mjs').read_bytes()).hexdigest() == reducer.ADAPTER_SHA256, 'Adapter source differs')
    spec = next(c for c in json.loads(args.registry.read_bytes())['cases'] if c['case_id'] == run['case_id'])
    result = classify_branch(raw,run,spec); print(json.dumps({'kind':result['kind'],'issues':result['issues'],'action':POLICY[result['kind']][0]}))
