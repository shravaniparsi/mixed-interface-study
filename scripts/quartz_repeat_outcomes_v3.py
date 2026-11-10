"""Translate pinned Quartz branch observations into the repeat planner contract."""
from pathlib import Path
import hashlib
import json
import summarize_quartz_oracle_components_v3 as reducer
from run_quartz_pairs import business

GUARDS = {'native_POST_payload_matches_bound_intent', 'native_PUT_payload_matches_bound_intent'}


def pair_outcome(job, branches, registered, run_complete=True):
    """Keep shared failures as repeat triggers, never exclusive channel signals."""
    reduced = {c: reducer.reduce_case(raw, run, registered[c], run_complete=run_complete)
               for c, (raw, run) in branches.items()}
    cleanup = len(branches) == 2 and all(all(run.get(k, {}).get('ok') is True for k in ('node_cleanup', 'java_cleanup', 'browser_cleanup'))
        and run.get('browser_process_absent') is True and run.get('application_port_released') is True for raw, run in branches.values())
    complete = set(branches) == {'api', 'ui'} and all(r['execution_evidence_complete'] for r in reduced.values())
    prefix = 'unobserved'; gates = {}; checks_failed = None; discrepancy = None
    if len(branches) == 2:
        a, u = (branches[c][0] for c in ('api', 'ui'))
        flags = [a.get('accepted_prefix'), u.get('accepted_prefix')]
        prefix = 'accepted' if flags == [True, True] else 'rejected' if flags == [False, False] else 'mixed'
        gates = {'same_initial_state': a.get('initial_state') is not None and a.get('initial_state') == u.get('initial_state'),
                 'same_actor': a.get('api_actor') is not None and a.get('api_actor') == u.get('api_actor'),
                 'independent_jvm': all(type(branches[c][1].get('server_pid')) is int for c in ('api','ui')) and branches['api'][1].get('server_pid') != branches['ui'][1].get('server_pid'),
                 'same_observed_prefix_command': a.get('producer', {}).get('request') == u.get('producer', {}).get('request') == registered['api']['operations'][0]['input'],
                 'same_prefix_response': (a.get('producer', {}).get('kind'), a.get('producer', {}).get('status')) == (u.get('producer', {}).get('kind'), u.get('producer', {}).get('status'))}
        if prefix == 'accepted':
            try:
                gates['same_prefix_business_state'] = business(a['stored_prefix']) == business(u['stored_prefix'])
            except (KeyError, ValueError, TypeError): gates['same_prefix_business_state'] = False
            gates['same_bound_intent'] = bool(a.get('bindings', {}).get('command')) and a.get('bindings') == u.get('bindings')
        complete = complete and all(gates.values()) and prefix != 'mixed'
        for r in reduced.values():
            if any(c['id'] in GUARDS and c['passed'] is False for part in r['components'].values() for c in part['checks']): complete = False
        if complete:
            checks_failed = any(c['passed'] is False for r in reduced.values() for name, part in r['components'].items()
                                if name not in ('environment_reset_cleanup', 'unresolved_policy') for c in part['checks'] if c['id'] not in GUARDS)
            discrepancy = False
            if prefix == 'accepted':
                assigned = [reduced[c]['components']['assigned_api_continuation' if c == 'api' else 'assigned_native_continuation']['mismatch_observed'] for c in ('api','ui')]
                discrepancy = assigned[0] != assigned[1]
    signature = {'branches': {c: {'prefix': r['producer_response'], 'continuation': r['continuation_response'],
                                  'checks': {n: [{'id': x['id'], 'passed': x['passed'], 'scope': x['scope']} for x in p['checks']] for n,p in r['components'].items()},
                                  'actor': branches[c][0].get('api_actor'), 'initial_state': branches[c][0].get('initial_state'),
                                  'producer_command': branches[c][0].get('producer', {}).get('request'),
                                  'bound_command': branches[c][0].get('bindings'),
                                  'stored_prefix': branches[c][0].get('stored_prefix'), 'final_job': branches[c][0].get('final_job')}
                              for c,r in reduced.items()}, 'comparability': gates}
    outcome = {'job_id': job['job_id'], 'execution': 'complete' if complete else 'incomplete', 'prefix': prefix,
               'channel_discrepancy': discrepancy, 'check_failure': checks_failed, 'cleanup_confirmed': cleanup,
               'observation_signature': signature}
    return {'outcome': outcome, 'components': reduced, 'comparability': gates,
            'interpretation': 'Source-check observations and repeat eligibility; no defect adjudication.'}


def read_job(directory, job, registry, expected_runner_sha):
    def read(p): return json.loads(p.read_bytes())
    def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
    directory = Path(directory)
    summary = read(directory/'summary.json')
    for filename, expected in [('executed-adapter.mjs', reducer.ADAPTER_SHA256), ('executed-registry.json', reducer.REGISTRY_SHA256), ('executed-runner.mjs', expected_runner_sha)]:
        if sha(directory/filename) != expected: raise ValueError('Source mismatch: '+filename)
    expected_ids = [b['case_id'] for b in job['branches']]
    if summary['ordering']['case_ids'] != expected_ids or summary['case_count'] != 2: raise ValueError('Dispatched selection differs')
    order_bytes = (directory/'executed-case-order.json').read_bytes()
    order = json.loads(order_bytes)
    if order != {'schema_version':1,'scope':'quartz_repeat_pair','registry_sha256':reducer.REGISTRY_SHA256,'case_ids':expected_ids} or hashlib.sha256(order_bytes).hexdigest() != summary['ordering']['order_file_sha256']: raise ValueError('Executed order differs')
    by_id = {c['case_id']:c for c in registry['cases']}
    if [e['case_id'] for e in summary['cases']] != expected_ids[:len(summary['cases'])]: raise ValueError('Case evidence reordered or duplicated')
    branches = {}; registered = {}; leaves = set()
    for entry in summary['cases']:
        leaf = Path(entry['evidence_directory']).name
        if leaf in leaves or leaf in ('', '.', '..') or (directory/leaf).resolve().parent != directory.resolve(): raise ValueError('Invalid evidence directory')
        leaves.add(leaf); raw = read(directory/leaf/'result.json'); run = read(directory/leaf/'run.json')
        if run != entry: raise ValueError('Summary/run record differs')
        spec = by_id[entry['case_id']]; channel = spec['operations'][1]['interface']
        branches[channel] = (raw, run); registered[channel] = spec
    # A missing branch is unresolved, not a clean pass. Source/selection errors raise.
    for b in job['branches']: registered[b['continuation']] = by_id[b['case_id']]
    result = pair_outcome(job, branches, registered, run_complete=summary.get('status') in ('pass','completed_observations') and summary.get('equal_initial_state_hashes') is True)
    result['summary_sha256'] = sha(directory/'summary.json')
    return result
