"""Trace-bound measurement sidecars for source-qualified identity branches.

This module does not schedule jobs or replace the frozen terminal classifier.
Database observations from a different execution are deliberately not accepted.
"""
from copy import deepcopy
from mixed_interface.write_observations import measure
from realworld_identity_extract_v1 import (
    require, user, project, expected_user, encode, jskey, strict_json_equal,
    capture_integrity_issues,
)


def reconstruct(raw, spec, fixture, classified):
    require(raw['candidate_id'] == spec['candidate_id'] and raw['expectation'] == spec['expectation'],
            'Registration differs')
    require(raw['workflow'] == spec['workflow'] == 'profile-update-edit'
            and raw['prefix_interface'] == spec['prefix_interface'] == 'api', 'Workflow differs')
    channel = raw['continuation_interface']
    require(channel in ('api', 'ui') and channel in spec['continuations'], 'Consumer differs')
    require(raw['execution_status'] == 'completed' and not raw.get('error'), 'Incomplete adapter')
    require(not capture_integrity_issues(raw, required=True), 'Capture incomplete')
    require(raw['actor'] == {'email': 'pilot@example.com', 'stable_fixture_username': 'pilotresearch'},
            'Actor differs')
    trace = raw['trace']
    require([e['sequence'] for e in trace] == list(range(1, len(trace) + 1)), 'Trace sequence differs')
    require(not any(e['type'] in ('capture_error', 'page_error') for e in trace), 'Capture error')
    pending = None
    for e in trace:
        if e.get('source') not in ('api', 'state_probe') or e['type'] not in ('request', 'response'):
            continue
        key = tuple(e[k] for k in ('source', 'phase', 'method', 'path'))
        if e['type'] == 'request':
            require(pending is None, 'Overlapping direct requests'); pending = key
        else:
            require(pending == key, 'Unmatched response'); pending = None
    require(pending is None, 'Unfinished request')

    def exchange(phase, method, path, payload):
        events = [e for e in trace if e.get('source') == 'api' and e.get('phase') == phase
                  and e.get('method') == method and e.get('path') == path
                  and e['type'] in ('request', 'response')]
        require(len(events) == 2 and [e['type'] for e in events] == ['request', 'response'],
                'Missing or duplicate exchange')
        request, response = events
        require(strict_json_equal(request.get('payload'), payload), 'Command differs')
        require(type(response['status']) is int and 100 <= response['status'] <= 599, 'Invalid response')
        return request, response

    _, login = exchange('setup', 'POST', '/api/users/login',
                        {'user': {'email': 'pilot@example.com', 'password': '[REDACTED]'}})
    _, baseline_event = exchange('setup', 'GET', '/api/user', None)
    require(login['status'] == baseline_event['status'] == 200, 'Setup response failure')
    baseline = user(baseline_event['data']['user'])
    require(baseline['username'] == 'pilotresearch' and baseline['email'] == 'pilot@example.com',
            'Baseline actor differs')
    require(all(user(login['data']['user'])[k] == baseline[k] for k in ('username', 'email')),
            'Login actor differs')
    slugs = [fixture[k]['slug'] for k in ('base', 'duplicate_first', 'duplicate')]

    def snapshot(name, phase, principal):
        record = raw['identity'][name]
        expected = ['/api/user', '/api/articles?author=' + encode(principal['username']), '/api/tags']
        for slug in sorted(slugs, key=jskey):
            expected.extend(['/api/articles/' + encode(slug), '/api/articles/' + encode(slug) + '/comments'])
        reads = record['reads']
        require([r['path'] for r in reads] == expected, 'Missing, reordered or extra planned probe')
        requests = [e for e in trace if e.get('source') == 'state_probe' and e.get('phase') == phase
                    and e['type'] == 'request']
        responses = [e for e in trace if e.get('source') == 'state_probe' and e.get('phase') == phase
                     and e['type'] == 'response']
        require(len(requests) == len(responses) == len(reads), 'Probe inventory differs')
        for read, request, response in zip(reads, requests, responses):
            require(request['method'] == response['method'] == 'GET'
                    and request['path'] == response['path'] == read['path'], 'Probe command differs')
            require(request.get('payload') is None and request['sequence'] < response['sequence'],
                    'Probe request differs')
            require(type(response['status']) is int and 100 <= response['status'] <= 599,
                    'Invalid probe status')
            require(read['response_sequence'] == response['sequence']
                    and all(strict_json_equal(read[k], response[k]) for k in ('path', 'status', 'data')),
                    'Probe trace binding differs')
        return record, requests[0]['sequence'], responses[-1]['sequence']

    before, first_before, last_before = snapshot('before', 'setup', baseline)
    derived = project(before['reads'], baseline, slugs)
    require(before['readable'] is True and strict_json_equal(before['data'], derived), 'Baseline projection differs')
    require(strict_json_equal(derived['user'], baseline), 'Baseline user differs')
    require(strict_json_equal([r['article'] for r in derived['articles']],
                              sorted(fixture.values(), key=lambda a: jskey(a['slug']))), 'Fixture differs')
    request, response = exchange('prefix', 'PUT', '/api/user', {'user': spec['prefix_payload']})
    require(login['sequence'] < baseline_event['sequence'] < first_before
            and last_before < request['sequence'], 'Setup/write ordering differs')
    require(raw['observations']['prefix_status'] == response['status']
            and strict_json_equal(raw['observations']['prefix_response'], response['data']), 'Prefix summary differs')
    status = response['status']
    phase = 'prefix_readback' if status == 200 else 'failed_prefix_followup'
    principal = expected_user(baseline, spec['prefix_payload']) if status == 200 else baseline
    record, first_after, _ = snapshot('prefix' if status == 200 else 'after', phase, principal)
    require(response['sequence'] < first_after, 'Readback precedes write response')
    if status != 200:
        require(not any(e.get('phase') in ('continuation', 'continuation_auth', 'prefix_readback', 'shared_readback')
                        for e in trace), 'Unexpected continuation after failed prefix')
        require(not raw['observations']['api_continuation_started']
                and not raw['observations']['ui_continuation_started']
                and raw['observations']['continuation_outcome'] == 'not_executed_prefix_unsuccessful',
                'Continuation stop differs')
        require(all((e.get('source'), e.get('phase'), e.get('method'), e.get('path')) in
                    {('api', 'setup', 'POST', '/api/users/login'), ('api', 'prefix', 'PUT', '/api/user')}
                    for e in trace if e['type'] == 'request' and e.get('method') in ('POST', 'PUT', 'PATCH', 'DELETE')),
                'Unregistered write')
    # These runs have no independent committed-state reader. API bodies are not DB snapshots.
    absent = {'state': 'not_planned'}
    measurement = measure(status, absent, absent, absent, spec['prefix_payload'],
                          {phase + ':' + r['path']: {'state': 'response', 'status': r['status']}
                           for r in record['reads']})
    if status != 200:
        continuation = {'state': 'not_executed_prefix_unsuccessful', 'interface': channel}
    elif classified['kind'] in ('clean_observation', 'completed_mismatch', 'unresolved_policy'):
        continuation = {'state': 'observed', 'interface': channel, 'checks': deepcopy(classified['checks'])}
    else:
        continuation = {'state': 'unqualified', 'interface': channel}
    measurement['continuation'] = continuation
    return {'measurement': measurement, 'requirement_policy': deepcopy(spec['expectation']),
            'readback_scope': 'immediate producer readbacks only; continuation checks remain separate',
            'database_evidence': 'not captured for this execution'}


def extract(raw, spec, fixture, classified):
    try:
        return {'qualified': True, **reconstruct(raw, spec, fixture, classified)}
    except (ValueError, KeyError, TypeError, AttributeError, IndexError) as error:
        return {'qualified': False, 'issues': [str(error)]}
