#!/usr/bin/env python3
"""Read-only, source-qualified RealWorld observation extraction.

Accepts saved legacy boundary runs and the validation stratum of generated
integration runs. It does not execute applications, infer faults from aggregate
statuses, compare pairs, or assign defects. Exit 1 means incomplete evidence.
Async trace phases never determine component attribution. Source-pinned check
names, request source/method/path, registered inputs and explicit bindings do.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
from urllib.parse import quote


LEGACY_ADAPTERS = {
    '40beb4cdc41915bdd40bbae09fead202b3654ccb54ddd9f054cb827ea32b1a5f',
    'bf0407de703d30a425dce3cfde3c218ee8096f7747e75e8ecd57f27e12b144d5',
}
GENERATED_ADAPTER = 'c3a0ef4806fd0f245a7cd783568c4286ea1462648d1f1224f9495777d847c7f1'
CAPTURE_HELPER = 'e47c6c4e6e6db85ef129c4b5aa49f97922c795c1269ef88eb6f6214209b3e8be'
CAPTURE_LEGACY_ADAPTER = 'b991ca9652e6e09c0b8836bcbc57d0966eb54072b036a06ac60058daddbbde3b'
CAPTURE_GENERATED_ADAPTER = '0c1883dcbd8eaa383111f814c00c1c7f942fa25c472b380d9983792028701172'
CAPTURE_ADAPTERS = {CAPTURE_LEGACY_ADAPTER, CAPTURE_GENERATED_ADAPTER}
LEGACY_ADAPTERS.add(CAPTURE_LEGACY_ADAPTER)
GENERATED_ADAPTERS = {GENERATED_ADAPTER, CAPTURE_GENERATED_ADAPTER}
LEGACY_REGISTRIES = {
    'dee2fee441d71283eddd68e1c5b23396d95d7a8c184d0e24468a1c5f7e1deab2',
    '05545a7ee5682348d111518ff40656dc4ae203cf95752018c496bfd54046eb66',
}
GENERATED_REGISTRY = 'e30df6147de81937de728f743607b250755f3b6438d9f1518d0898272b121acc'
COMPONENTS = (
    'immediate_response', 'producer_native_controls', 'prefix_state_reads',
    'assigned_api_continuation', 'assigned_native_continuation',
    'shared_post_continuation_api_readback', 'shared_final_native_read',
    'environment_reset_cleanup', 'unresolved_policy',
)
FIXED_CHECKS = {
    'prefix_fields_match_declared_input': 'immediate_response',
    'prefix_comment_matches_input': 'immediate_response',
    'producer_fields': 'immediate_response',
    'producer_actual_payload': 'producer_native_controls',
    'prefix_profile_matches_input': 'prefix_state_reads',
    'failed_prefix_observable_state_unchanged': 'prefix_state_reads',
    'fresh_ui_principal_matches': 'environment_reset_cleanup',
    'persisted_continuation': 'shared_post_continuation_api_readback',
    'comment_relationship_persisted': 'shared_post_continuation_api_readback',
    'parent_article_preserved': 'shared_post_continuation_api_readback',
    'deletion_persisted': 'shared_post_continuation_api_readback',
    'profile_edit_persisted': 'shared_post_continuation_api_readback',
    'profile_reference_resolvable': 'shared_post_continuation_api_readback',
    'persisted_business_state': 'shared_post_continuation_api_readback',
    'one_article': 'shared_post_continuation_api_readback',
    'shared_ui_read': 'shared_final_native_read',
    'shared_ui_render': 'shared_final_native_read',
}
ASSIGNED_CHECKS = {'consumer_loaded_prefix_fields', 'comment_loaded_in_parent',
                   'consumer_loaded_state', 'native_form_loaded', 'consumer_actual_payload'}
NATIVE_CHECKS = {'native_form_loaded', 'consumer_actual_payload', 'fresh_ui_principal_matches'}
WORKFLOWS = {'article-create-edit', 'article-update-comment', 'comment-create-delete', 'profile-update-edit'}
LEGACY_CHECKS = {
    'article-create-edit': {'prefix_fields_match_declared_input', 'consumer_loaded_prefix_fields', 'persisted_continuation'},
    'article-update-comment': {'prefix_fields_match_declared_input', 'consumer_loaded_prefix_fields', 'comment_relationship_persisted', 'parent_article_preserved'},
    'comment-create-delete': {'prefix_comment_matches_input', 'comment_loaded_in_parent', 'deletion_persisted', 'parent_article_preserved'},
    'profile-update-edit': {'prefix_profile_matches_input', 'fresh_ui_principal_matches', 'profile_edit_persisted', 'profile_reference_resolvable'},
}
GENERATED_CHECKS = {'producer_fields', 'producer_actual_payload', 'consumer_loaded_state', 'native_form_loaded',
                    'consumer_actual_payload', 'persisted_business_state', 'shared_ui_read', 'shared_ui_render', 'one_article'}
EDIT_BODY = 'Body after meaningful continuation.'
EDIT_BIO = 'Bio after meaningful continuation.'
COMMENT_BODY = 'Comment after article update.'


def sha(data):
    return hashlib.sha256(data).hexdigest()


def article_state(value, *, generated=False, slug=False):
    if not isinstance(value, dict):
        return None
    state = {key: value.get(key) for key in ('title', 'description', 'body', 'tagList')}
    state['author'] = value.get('author', {}).get('username')
    if generated and isinstance(state['tagList'], list):
        state['tagList'] = sorted(set(state['tagList']))
    if slug:
        state = {'slug': value.get('slug'), **state}
    return state


def user_state(value):
    return {k: value.get(k) for k in ('username', 'email', 'bio', 'image')} if isinstance(value, dict) else None


def capture_integrity_issues(result, *, required=False):
    """Check request-to-body accounting for the revised capture source only."""
    capture = result.get('capture_integrity')
    if capture is None:
        return ['missing_capture_integrity'] if required else []
    if not isinstance(capture, dict):
        return ['malformed_capture_integrity']
    issues = []

    def guard(ok, label):
        if not ok:
            issues.append(label)

    guard(capture.get('version') == 1 and capture.get('helper_sha256') == CAPTURE_HELPER,
          'unsupported_capture_helper')
    guard(capture.get('complete') is True, 'capture_integrity_failed')
    contexts = capture.get('contexts')
    trace = result.get('trace')
    if not isinstance(contexts, list) or not isinstance(trace, list):
        return issues + ['malformed_capture_contexts_or_trace']
    context_ids, requests, responses = set(), {}, {}
    for event in trace:
        if not isinstance(event, dict):
            issues.append('malformed_capture_event')
            continue
        is_request = event.get('type') == 'ui_request' or (event.get('type') == 'request' and event.get('source') == 'ui')
        is_response = event.get('type') == 'ui_response' or (event.get('type') == 'response' and event.get('source') == 'ui')
        if is_request or is_response:
            keys = ('capture_request_id', 'context_id', 'method', 'path', 'request_phase')
            if any(not isinstance(event.get(k), str) or not event[k] for k in keys):
                issues.append('missing_capture_request_metadata')
                continue
            destination = requests if is_request else responses
            identifier = event['capture_request_id']
            guard(identifier not in destination, 'duplicate_capture_request_or_response')
            destination[identifier] = {k: event[k] for k in keys}
        if event.get('type') == 'capture_error':
            issues.append('capture_error_recorded')
    guard(requests == responses, 'capture_request_response_accounting_mismatch')
    for context in contexts:
        if not isinstance(context, dict) or not isinstance(context.get('context_id'), str):
            issues.append('malformed_capture_context')
            continue
        cid = context['context_id']
        guard(cid not in context_ids, 'duplicate_capture_context')
        context_ids.add(cid)
        guard(context.get('complete') is True and context.get('timed_out') is False
              and context.get('outstanding') == [] and context.get('failures') == 0,
              'capture_context_incomplete')
        count = sum(r['context_id'] == cid for r in requests.values())
        guard(type(context.get('admitted')) is int and type(context.get('completed')) is int
              and context['admitted'] == context['completed'] == count,
              'capture_context_count_mismatch')
        drains = [e for e in trace if isinstance(e, dict) and e.get('type') == 'capture_drain' and e.get('context_id') == cid]
        guard(len(drains) == 1 and all(drains[0].get(k) == v for k, v in context.items()),
              'capture_drain_record_mismatch')
    guard(all(r['context_id'] in context_ids for r in requests.values()), 'unclosed_capture_context')
    return sorted(set(issues))


def reduce_case(result, run, registered, *, family='legacy', fixture=None, provenance_issues=()):
    """Extract one case after the loader qualifies immutable source/registry bytes.

    The pure function is useful for adversarial tests. Its result is not a
    standalone provenance certificate; use summarize_run for file-backed use.
    Existing booleans are retained with check details; independently recomputed
    input/binding consistency guards do not constitute an application re-test.
    """
    issues = list(provenance_issues) + capture_integrity_issues(result)
    parts = {name: {'checks': [], 'failed_check_ids': [], 'observations': []} for name in COMPONENTS}
    expected_checks = set()
    generated = family == 'generated'
    workflow = 'article-create-edit' if generated else registered.get('workflow')
    operations = registered.get('operations', [])
    route = result.get('route') if generated else [result.get('prefix_interface'), result.get('continuation_interface')]
    if not isinstance(route, list) or len(route) != 2 or any(x not in {'api', 'ui'} for x in route):
        issues.append('invalid_route')
        route = ['unknown', 'unknown']
    producer, consumer = route
    assigned = 'assigned_api_continuation' if consumer == 'api' else 'assigned_native_continuation'
    observation = result if generated else result.get('observations', {})
    status = observation.get('prefix_status')
    accepted = type(status) is int and (status == 201 if generated else 200 <= status < 300)
    expectation = registered.get('expectation', {})
    unknown_policy = expectation.get('category') == 'unresolved'
    trace = result.get('trace', [])
    if not isinstance(trace, list) or any(not isinstance(x, dict) for x in trace):
        trace = []
        issues.append('malformed_trace')
    if [x.get('sequence') for x in trace] != list(range(1, len(trace) + 1)):
        issues.append('trace_sequence_missing_or_noncontiguous')
    if any(x.get('type') in {'capture_error', 'page_error'} for x in trace):
        issues.append('unresolved_capture_or_page_error')
        parts['environment_reset_cleanup']['observations'].append({'id': 'unresolved_trace_errors',
            'events': [x for x in trace if x.get('type') in {'capture_error', 'page_error'}]})

    def guard(passed, label):
        if not passed:
            issues.append(label)

    def add(component, name, passed, evidence=None, scope='recorded_source_observation'):
        item = {'id': name, 'passed': passed, 'scope': scope}
        if evidence is not None:
            item['evidence'] = evidence
        parts[component]['checks'].append(item)
        if passed is False:
            parts[component]['failed_check_ids'].append(name)

    def events(source, method, path, *, response=False):
        if generated and source == 'ui':
            kind = 'ui_response' if response else 'declared_ui_request'
            return [x for x in trace if x.get('type') == kind and x.get('method') == method and x.get('path') == path]
        return [x for x in trace if x.get('type') == ('response' if response else 'request')
                and (x.get('source'), x.get('method'), x.get('path')) == (source, method, path)]

    def require_event(source, method, path, *, response=False, predicate=None):
        found = events(source, method, path, response=response)
        if predicate:
            found = [x for x in found if predicate(x)]
        guard(bool(found), 'missing_trace_evidence:' + ':'.join((source, method, path, 'response' if response else 'request')))
        return found

    def payload(source, method, path, expected, *, position=0):
        matches = events(source, method, path)
        guard(len(matches) > position, 'missing_operation_request:' + method + ':' + path)
        if len(matches) > position:
            guard(matches[position].get('payload') == expected, 'actual_payload_differs_from_bound_intent:' + method + ':' + path)

    checks = result.get('checks', [])
    if not isinstance(checks, list):
        checks = []
        issues.append('checks_not_array')
    seen = {}
    unclassified = []
    allowed_checks = GENERATED_CHECKS if generated else LEGACY_CHECKS.get(workflow, set()) | {'failed_prefix_observable_state_unchanged'}
    for check in checks:
        if not isinstance(check, dict) or not isinstance(check.get('name'), str):
            issues.append('malformed_check')
            continue
        name = check['name']
        if name in seen:
            issues.append('duplicate_check:' + name)
        seen[name] = check
        target = assigned if name in ASSIGNED_CHECKS else FIXED_CHECKS.get(name)
        if target is None or name not in allowed_checks or type(check.get('passed')) is not bool:
            issues.append('unknown_or_malformed_check:' + name)
            unclassified.append(check)
            continue
        if (name in NATIVE_CHECKS and consumer != 'ui') or (name == 'producer_actual_payload' and producer != 'ui'):
            issues.append('native_check_on_wrong_route:' + name)
            unclassified.append(check)
            continue
        if not accepted and (name in ASSIGNED_CHECKS or target.startswith('shared_')):
            issues.append('downstream_check_after_unsuccessful_prefix:' + name)
            unclassified.append(check)
            continue
        add(target, name, check['passed'], check)
        if name == 'fresh_ui_principal_matches' and not check['passed']:
            issues.append('execution_integrity_check_failed:' + name)

    def expect(*names):
        expected_checks.update(names)

    def verify_check(name, calculated):
        if name in seen:
            guard(seen[name].get('passed') is calculated, 'check_value_not_supported_by_recorded_state:' + name)

    login = require_event('api', 'POST', '/api/users/login', response=True)
    guard(any(x.get('status') == 200 and x.get('data', {}).get('user', {}).get('email') == 'pilot@example.com'
              and x.get('data', {}).get('user', {}).get('username') == 'pilotresearch' for x in login), 'fixture_actor_unverified')
    if generated:
        guard(result.get('case_id') == registered.get('case_id') == run.get('case_id'), 'case_id_mismatch')
        guard(len(operations) == 2 and route == [o.get('interface') for o in operations], 'registered_route_mismatch')
        guard(run.get('route') == route, 'run_route_mismatch')
        inputs = operations[0]['input']['article'] if len(operations) == 2 else {}
    else:
        guard(workflow in WORKFLOWS, 'unknown_workflow')
        guard(result.get('candidate_id') == run.get('candidate_id') == registered.get('candidate_id'), 'case_id_mismatch')
        guard(result.get('workflow') == workflow and producer == registered.get('prefix_interface')
              and consumer == run.get('continuation') and consumer in registered.get('continuations', []), 'registered_route_or_workflow_mismatch')
        guard(result.get('expectation') == expectation, 'registered_expectation_mismatch')
        guard(result.get('oracle_revision') == 2, 'unsupported_oracle_revision')
        guard(run.get('prefix_status') == status, 'run_prefix_status_mismatch')
        inputs = registered.get('prefix_payload', {})
    guard(type(status) is int, 'missing_prefix_status')
    parts['immediate_response']['observations'].append({'id': 'producer_http_status', 'status': status,
        'classification': 'server_error' if type(status) is int and status >= 500 else 'accepted' if accepted else 'not_accepted'})
    if type(status) is int and status >= 500:
        add('immediate_response', 'producer_server_error', False, {'status': status}, 'http_observation_not_adjudicated_defect')
    if unknown_policy:
        parts['unresolved_policy']['observations'].append({'expectation': expectation, 'actual_status': status})
    elif type(status) is int:
        # The registry predicts acceptance/rejection, not a blanket 4xx status
        # contract. Keep a 5xx server-error observation independent of this test.
        met = accepted if expectation.get('outcome') == 'accept' else not accepted
        add('immediate_response', 'declared_acceptance_expectation', met, {'expectation': expectation, 'actual_status': status}, expectation.get('category'))

    fixture = fixture or {}
    target = fixture.get(registered.get('target_fixture'), {}) if not generated else {}
    if workflow == 'article-create-edit':
        prefix_method, prefix_path, envelope = 'POST', '/api/articles', 'article'
    elif workflow == 'article-update-comment':
        prefix_method, prefix_path, envelope = 'PUT', '/api/articles/' + target.get('slug', ''), 'article'
    elif workflow == 'comment-create-delete':
        prefix_method, prefix_path, envelope = 'POST', '/api/articles/' + fixture.get('base', {}).get('slug', '') + '/comments', 'comment'
    else:
        prefix_method, prefix_path, envelope = 'PUT', '/api/user', 'user'
    prefix_requests = require_event(producer, prefix_method, prefix_path)
    prefix_responses = require_event(producer, prefix_method, prefix_path, response=True)
    prefix_event = prefix_responses[0] if prefix_responses else {}
    prefix_data = prefix_event.get('data', {})
    guard(prefix_event.get('status') == status, 'prefix_response_status_mismatch')
    parts['immediate_response']['observations'].append({'id': 'producer_response', 'source': producer,
        'method': prefix_method, 'path': prefix_path, 'status': prefix_event.get('status'), 'data': prefix_data})
    if not generated:
        guard(observation.get('prefix_response') == prefix_data, 'prefix_response_copy_mismatch')
    if workflow == 'profile-update-edit' and producer == 'ui':
        baseline_events = events('api', 'GET', '/api/user', response=True)
        baseline = user_state(baseline_events[0].get('data', {}).get('user')) if baseline_events else None
        prefix_payload = {k: v for k, v in (baseline or {}).items() if v is not None}
        prefix_payload.update(inputs)
    else:
        prefix_payload = inputs
    payload(producer, prefix_method, prefix_path, {envelope: prefix_payload})
    if generated and producer == 'ui':
        expect('producer_actual_payload')
        verify_check('producer_actual_payload', bool(prefix_requests) and prefix_requests[0].get('payload') == {'article': inputs})

    reached = False
    if not accepted:
        follow = observation.get('failed_prefix_followup' if generated else 'failed_prefix_api_followup')
        guard(isinstance(follow, dict) and type(follow.get('status')) is int, 'missing_failed_prefix_followup')
        parts['prefix_state_reads']['observations'].append({'id': 'failed_prefix_followup', 'evidence': follow})
        if isinstance(follow, dict) and follow.get('status') != 200:
            add('prefix_state_reads', 'failed_prefix_followup_unreadable', False, follow, 'http_observation_not_proof_of_state_change')
        if generated:
            guard(result.get('coverage', {}).get('data_consumed') is False and result.get('coverage', {}).get('state_consumed') is False,
                  'unsuccessful_prefix_has_downstream_coverage')
            parts['prefix_state_reads']['limitations'] = ['The pinned generated adapter records followup but has no unchanged-state predicate. Rejection does not establish rollback.']
        else:
            expect('failed_prefix_observable_state_unchanged')
            guard(observation.get('ui_continuation_started') is False and observation.get('api_continuation_started') is False,
                  'unsuccessful_prefix_has_continuation')
        path = '/api/user' if workflow == 'profile-update-edit' else prefix_path if workflow == 'comment-create-delete' else '/api/articles?author=pilotresearch'
        require_event('api', 'GET', path, response=True, predicate=lambda x: x.get('status') == (follow or {}).get('status') and x.get('data') == (follow or {}).get('data'))
    elif workflow.startswith('article-'):
        a = prefix_data.get('article', {})
        slug = a.get('slug')
        expected = {k: inputs.get(k, target.get(k)) for k in ('title', 'description', 'body')}
        expected.update(tagList=inputs.get('tagList', target.get('tagList', [])), author='pilotresearch')
        if generated:
            expected['tagList'] = sorted(set(expected['tagList']))
        prefix_check = 'producer_fields' if generated else 'prefix_fields_match_declared_input'
        expect(prefix_check)
        verify_check(prefix_check, article_state(a, generated=generated) == expected)
        guard(isinstance(slug, str), 'missing_returned_article_reference')
        guard((result.get('accepted_producer') == article_state(a, generated=True) and result.get('resource_reference') == slug) if generated
              else result.get('prefix_state') == article_state(a, slug=True), 'recorded_prefix_state_mismatch')
        if target:
            original = observation.get('original_reference_read')
            guard(isinstance(original, dict), 'missing_original_reference_diagnostic')
            parts['prefix_state_reads']['observations'].append({'id': 'original_reference_read', 'evidence': original})
        if not slug:
            add('immediate_response', 'returned_reference_empty', False, {'slug': slug}, 'reference_observation_not_adjudicated_defect')
        else:
            path = '/api/articles/' + quote(slug, safe="~()*!.'-")
            loads = require_event(consumer, 'GET', path, response=True)
            if generated:
                bindings = [x for x in trace if x.get('type') == 'consumed_dependency' and x.get('field') == 'article.slug']
                guard(len(bindings) == 1 and bindings[0].get('interface') == consumer and bindings[0].get('reference') == slug,
                      'missing_or_incorrect_consumed_reference')
                read_status = bindings[0].get('status') if bindings else None
                guard(result.get('coverage', {}).get('data_consumed') is True, 'missing_data_consumption_record')
            else:
                read_status = observation.get('consumer_read_status')
            guard(any(x.get('status') == read_status for x in loads), 'consumer_read_status_without_trace')
            reached = bool(loads)
            add(assigned, 'consumer_read_http_status', read_status == 200, {'status': read_status, 'path': path}, 'http_observation')
            if read_status == 200:
                load_check = 'consumer_loaded_state' if generated else 'consumer_loaded_prefix_fields'
                expect(load_check)
                loaded = next((x.get('data', {}).get('article') for x in loads if x.get('status') == 200), None)
                verify_check(load_check, article_state(loaded, generated=True) == expected if generated else article_state(loaded, slug=True) == article_state(a, slug=True))
                if workflow == 'article-create-edit':
                    edit = {'title': a.get('title'), 'description': a.get('description'), 'body': operations[1]['input']['article']['body'] if generated else EDIT_BODY, 'tagList': a.get('tagList')}
                    if generated:
                        guard(result.get('resolved_consumer_input') == {'article': edit}, 'resolved_consumer_binding_mismatch')
                    payload(consumer, 'PUT', path, {'article': edit})
                    writes = require_event(consumer, 'PUT', path, response=True)
                    write_status = observation.get('consumer_status' if generated else 'continuation_write_status')
                    guard(any(x.get('status') == write_status for x in writes), 'consumer_write_status_without_trace')
                    add(assigned, 'consumer_write_http_status', write_status == 200, {'status': write_status}, 'http_observation')
                    if generated and consumer == 'ui':
                        expect('native_form_loaded', 'consumer_actual_payload')
                        form = seen.get('native_form_loaded', {}).get('observed')
                        verify_check('native_form_loaded', form == {k: a.get(k) for k in ('title', 'description', 'body')})
                        submitted = seen.get('consumer_actual_payload', {})
                        verify_check('consumer_actual_payload', submitted.get('expected') == edit and submitted.get('observed') == edit)
                    if write_status == 200:
                        expect('persisted_business_state' if generated else 'persisted_continuation')
                        written = next((x.get('data', {}).get('article', {}) for x in writes if x.get('status') == 200), {})
                        final_path = '/api/articles/' + quote(written.get('slug', ''), safe="~()*!.'-")
                        finals = require_event('api', 'GET', final_path, response=True)
                        final = finals[-1] if finals else {}
                        check_name = 'persisted_business_state' if generated else 'persisted_continuation'
                        verify_check(check_name, final.get('status') == 200 and article_state(final.get('data', {}).get('article'), generated=generated) == {**expected, 'body': edit['body']})
                        if generated:
                            expect('shared_ui_read', 'shared_ui_render', 'one_article')
                            native_final = require_event('ui', 'GET', final_path, response=True)
                            if native_final:
                                verify_check('shared_ui_read', native_final[-1].get('status') == 200 and article_state(native_final[-1].get('data', {}).get('article'), generated=True) == {**expected, 'body': edit['body']})
                            counts = require_event('api', 'GET', '/api/articles?author=pilotresearch', response=True)
                            guard(len(counts) >= 2, 'missing_final_article_count_probe')
                            if len(counts) >= 2:
                                verify_check('one_article', counts[-1].get('status') == 200 and counts[-1].get('data', {}).get('articlesCount') == 1)
                else:
                    comments_path = path + '/comments'
                    payload(consumer, 'POST', comments_path, {'comment': {'body': COMMENT_BODY}})
                    writes = require_event(consumer, 'POST', comments_path, response=True)
                    write_status = observation.get('continuation_write_status')
                    guard(any(x.get('status') == write_status for x in writes), 'consumer_write_status_without_trace')
                    add(assigned, 'consumer_write_http_status', write_status == 201, {'status': write_status}, 'http_observation')
                    expect('comment_relationship_persisted', 'parent_article_preserved')
                    require_event('api', 'GET', comments_path, response=True)
                    require_event('api', 'GET', path, response=True)
    elif workflow == 'comment-create-delete':
        comment = prefix_data.get('comment', {})
        cid = comment.get('id')
        guard(type(cid) is int, 'missing_returned_comment_id')
        expect('prefix_comment_matches_input', 'comment_loaded_in_parent', 'deletion_persisted', 'parent_article_preserved')
        verify_check('prefix_comment_matches_input', comment.get('body') == inputs.get('body') and comment.get('author', {}).get('username') == 'pilotresearch')
        loads = require_event(consumer, 'GET', prefix_path, response=True)
        reached = bool(loads)
        require_event(consumer, 'DELETE', prefix_path + '/' + str(cid))
        writes = require_event(consumer, 'DELETE', prefix_path + '/' + str(cid), response=True)
        write_status = observation.get('continuation_write_status')
        guard(any(x.get('status') == write_status for x in writes), 'consumer_write_status_without_trace')
        add(assigned, 'consumer_write_http_status', write_status == 204, {'status': write_status}, 'http_observation')
        require_event('api', 'GET', prefix_path, response=True)
        require_event('api', 'GET', prefix_path.removesuffix('/comments'), response=True)
    elif workflow == 'profile-update-edit':
        users = events('api', 'GET', '/api/user', response=True)
        guard(len(users) >= 2, 'missing_post_prefix_user_read')
        current = users[1].get('data', {}).get('user') if len(users) >= 2 else None
        parts['prefix_state_reads']['observations'].append({'id': 'current_user_read_status', 'status': users[1].get('status') if len(users) >= 2 else None})
        if len(users) >= 2 and users[1].get('status') == 200:
            expect('prefix_profile_matches_input', 'profile_edit_persisted', 'profile_reference_resolvable')
            expected = {**(user_state(users[0].get('data', {}).get('user')) or {}), **inputs}
            for key in ('bio', 'image'):
                if expected.get(key) == '':
                    expected[key] = None
            verify_check('prefix_profile_matches_input', user_state(current) == expected)
            guard(result.get('prefix_state') == user_state(current), 'recorded_prefix_state_mismatch')
            edit = {k: current[k] for k in ('username', 'email')}
            edit['bio'] = EDIT_BIO
            if current.get('image') is not None:
                edit['image'] = current['image']
            payload(consumer, 'PUT', '/api/user', {'user': edit}, position=1 if consumer == producer else 0)
            writes = events(consumer, 'PUT', '/api/user', response=True)
            reached = len(writes) > (1 if consumer == producer else 0)
            write_status = observation.get('continuation_write_status')
            guard(bool(writes) and writes[-1].get('status') == write_status, 'consumer_write_status_without_trace')
            add(assigned, 'consumer_write_http_status', write_status == 200, {'status': write_status}, 'http_observation')
            guard(len(users) >= 3, 'missing_profile_final_readback')
            if len(users) >= 3:
                verify_check('profile_edit_persisted', write_status == 200 and users[-1].get('status') == 200 and user_state(users[-1].get('data', {}).get('user')) == {**expected, 'bio': EDIT_BIO})
            require_event('api', 'GET', '/api/profiles/' + quote(current.get('username', ''), safe="~()*!.'-"), response=True)
            if consumer == 'ui':
                expect('fresh_ui_principal_matches')
        else:
            add('prefix_state_reads', 'current_user_unreadable', False, {'status': users[1].get('status') if len(users) >= 2 else None}, 'http_observation')

    if not generated:
        guard(observation.get(consumer + '_continuation_started') is reached, 'continuation_started_flag_mismatch')
        guard(observation.get(('ui' if consumer == 'api' else 'api') + '_continuation_started') is False, 'other_interface_started_flag')
    if producer == 'ui' or consumer == 'ui' and reached or generated and 'shared_ui_read' in seen:
        native_auth = require_event('ui', 'POST', '/api/users/login', response=True)
        guard(bool(native_auth) and all(x.get('status') == 200 and x.get('data', {}).get('user', {}).get('email') == 'pilot@example.com' for x in native_auth),
              'native_principal_unverified')
    for name in sorted(expected_checks - seen.keys()):
        issues.append('missing_required_check:' + name)
    for name in sorted(seen.keys() - expected_checks):
        issues.append('unexpected_check_for_branch:' + name)
    finished = result.get('status' if generated else 'execution_status') == 'completed'
    guard(finished and bool(result.get('finished_at' if generated else 'completed_at')), 'case_not_finished')
    guard(run.get('status' if generated else 'execution_status') == 'completed', 'run_case_not_finished')
    if not generated:
        guard(run.get('exit_code') == 0, 'nonzero_worker_exit')
    if result.get('error'):
        issues.append('unclassified_adapter_assertion_or_execution_error')
        parts['environment_reset_cleanup']['observations'].append({'id': 'unclassified_error', 'evidence': result['error'], 'classification': 'not_automatically_application_block_or_defect'})
    for check_name in ('producer_actual_payload', 'consumer_actual_payload'):
        if check_name in seen and seen[check_name].get('passed') is False:
            issues.append('unclassified_native_payload_discrepancy:' + check_name)
    parts['shared_post_continuation_api_readback']['assigned_action_interface'] = consumer if accepted else None
    parts['shared_post_continuation_api_readback']['observation_mechanism'] = 'Direct API readback after assigned action; not native-only detection.'
    issues = sorted(set(issues))
    for name, part in parts.items():
        observed = bool(part['checks'] or part['observations'])
        part['mismatch_observed'] = bool(part['failed_check_ids'])
        part['comparison_eligible'] = observed and not issues and name != 'unresolved_policy'
        if name == 'unresolved_policy':
            part['status'] = 'policy_observations_only' if observed else 'not_applicable'
        elif name.startswith('assigned_') and name != assigned:
            part['status'] = 'not_assigned'
        elif (name.startswith('assigned_') or name.startswith('shared_')) and not accepted:
            part['status'] = 'not_reached_prefix_unsuccessful'
        elif not observed:
            part['status'] = 'incomplete_or_unobserved' if any(FIXED_CHECKS.get(c) == name or (c in ASSIGNED_CHECKS and name == assigned) for c in expected_checks) else 'not_reached_or_not_applicable'
        else:
            part['status'] = ('incomplete_or_invalid_evidence' if issues else 'check_mismatch_observed' if part['mismatch_observed']
                              else 'no_check_mismatch_observed' if part['checks'] else 'observations_without_registered_predicate')
            if not part['checks']:
                part['comparison_eligible'] = False
    return {'case_id': run.get('case_id'), 'candidate_id': registered.get('candidate_id', registered.get('case_id')),
            'workflow': workflow, 'route': '-'.join(route), 'accepted_prefix': accepted,
            'assigned_continuation_reached': reached, 'execution_evidence_complete': not issues,
            'evidence_issues': issues, 'components': parts, 'policy_unresolved': unknown_policy,
            'unclassified_checks': unclassified,
            'interpretation': 'Recorded source-check/HTTP observations only; no defect, root-cause, pair-validity or detection-overlap conclusion.'}


def summarize_run(directory):
    directory = Path(directory).resolve()
    summary_bytes = (directory / 'summary.json').read_bytes()
    summary = json.loads(summary_bytes)
    generated = summary.get('kind') == 'generated_registry_runtime_integration'
    # Older integration summaries use the following exact kind.
    if 'original_pool_sha256' in summary and 'validation' in summary:
        generated = True
    family = 'generated' if generated else 'legacy'
    adapter = 'realworld_generated_case.mjs' if generated else 'realworld_boundary_case.mjs'
    registry_name = 'original-pool.json' if generated else 'registered-candidates.json'
    expected_registry = summary.get('original_pool_sha256' if generated else 'registry_sha256')
    supported = {GENERATED_REGISTRY} if generated else LEGACY_REGISTRIES
    issues = []
    hashes = {}

    def read(relative):
        path = (directory / relative).resolve()
        if not path.is_relative_to(directory):
            raise ValueError('evidence_path_escapes_run:' + str(relative))
        data = path.read_bytes()
        hashes[str(relative)] = sha(data)
        return data

    registry = json.loads(read(registry_name))
    if expected_registry not in supported or hashes[registry_name] != expected_registry:
        issues.append('unsupported_or_changed_registry_bytes')
    source_dir = Path('sources') if generated else Path()
    source_hash = summary.get('source_sha256', {}).get(adapter)
    if source_hash not in (GENERATED_ADAPTERS if generated else LEGACY_ADAPTERS):
        issues.append('unsupported_adapter_hash')
    if source_hash in CAPTURE_ADAPTERS and summary.get('source_sha256', {}).get('response_capture.mjs') != CAPTURE_HELPER:
        issues.append('missing_or_unsupported_capture_helper_source')
    for name, expected in summary.get('source_sha256', {}).items():
        try:
            data = read(source_dir / name)
            if sha(data) != expected:
                issues.append('executed_source_bytes_mismatch:' + name)
        except OSError:
            issues.append('missing_executed_source:' + name)
    if adapter not in summary.get('source_sha256', {}):
        issues.append('missing_executed_adapter')
    if summary.get('status') != 'completed' or not summary.get('finished_at'):
        issues.append('containing_run_incomplete')
    key = 'case_id' if generated else 'candidate_id'
    cases = {c[key]: c for c in registry['cases']}
    entries = summary.get('validation' if generated else 'branches', [])
    if generated:
        wanted = {cid for cid, case in cases.items() if case['intervention'] == 'route_only'} if summary.get('phase') == 'controls' else set(cases)
        if summary.get('phase') == 'controls' and source_hash not in CAPTURE_ADAPTERS:
            issues.append('unsupported_control_subset_source')
        identifiers = [x.get('case_id') for x in entries]
    else:
        subset = summary.get('candidate_subset') or list(cases)
        wanted = {f'{cid}-{branch}-r{rep}' for cid in subset for branch in cases[cid]['continuations']
                  for rep in range(1, summary.get('repetitions_per_branch', 0) + 1)}
        identifiers = [x.get('case_id') for x in entries]
    if len(identifiers) != len(set(identifiers)) or set(identifiers) != wanted:
        issues.append('missing_duplicate_or_unregistered_branches')
    fixture = None if generated else json.loads(read('fixture-references.json'))
    loaded = []
    for entry in entries:
        try:
            registered = cases[entry[key]]
            own_issues = []
            if generated:
                leaf = Path(entry['details']['evidence'])
                raw = read(leaf / 'observation.json')
                if sha(raw) != entry['details'].get('observation_sha256'):
                    own_issues.append('observation_hash_mismatch')
                if json.loads(read(leaf / 'generated-case.json')) != registered:
                    own_issues.append('executed_candidate_differs_from_registry')
                reset = json.loads(read(leaf / 'reset.json'))
                if reset.get('sha256') != summary.get('resources', {}).get('fixture_sha256') or reset.get('independent_offline_reset') is not True:
                    own_issues.append('independent_reset_not_confirmed')
                for file in ('cleanup.json', 'parent-browser-cleanup.json'):
                    cleanup = json.loads(read(leaf / file))
                    if cleanup.get('ok') is not True or cleanup.get('worker_process_cleanup_errors'):
                        own_issues.append('cleanup_not_confirmed:' + file)
            else:
                raw = read(entry['evidence'])
                expected_id = f"{registered['candidate_id']}-{entry['continuation']}-r{entry['repetition']}"
                if entry['case_id'] != expected_id or entry['evidence'] != expected_id + '.json':
                    own_issues.append('legacy_branch_identity_mismatch')
                if not summary.get('fixture_sha256') or entry.get('reset_sha256') != summary['fixture_sha256']:
                    own_issues.append('reset_hash_mismatch')
            result = json.loads(raw)
            if source_hash in CAPTURE_ADAPTERS:
                own_issues.extend(capture_integrity_issues(result, required=True))
            loaded.append((result, entry, registered, own_issues))
        except (OSError, ValueError, KeyError, TypeError) as error:
            issues.append('unreadable_case_evidence:' + str(entry.get('case_id')) + ':' + type(error).__name__)
    observations = [reduce_case(result, entry, registered, family=family, fixture=fixture,
                               provenance_issues=issues + own) for result, entry, registered, own in loaded]
    complete = not issues and len(observations) == len(wanted) and all(x['execution_evidence_complete'] for x in observations)
    return {'schema_version': 1, 'kind': 'realworld_component_observations',
            'status': 'complete_observations' if complete else 'incomplete_or_invalid_evidence',
            'input_directory': str(directory), 'family': family, 'scope': 'validation_only' if generated else 'registered_legacy_branches',
            'source_adapter_sha256': source_hash, 'registry_sha256': expected_registry,
            'input_summary_sha256': sha(summary_bytes), 'input_artifact_sha256': hashes,
            'reducer_sha256': sha(Path(__file__).read_bytes()), 'run_issues': sorted(set(issues)),
            'case_count': len(observations), 'cases': observations,
            'component_status_counts': {name: dict(Counter(x['components'][name]['status'] for x in observations)) for name in COMPONENTS},
            'limitations': [
                'Source-pinned extraction, not an independent application-oracle re-execution or primary freeze.',
                'Legacy traces have no independent recorded trace hash or verified parent cleanup record; reset hashes are recorded assertions, not retained database rehashes.',
                'Generated extraction covers validation only; calibration, timed sessions and interruption attempts are not silently pooled.',
                'Shared API readback retains action-interface metadata; supplementary native UI checks never become API-semantic detection.',
                'Native action timeouts/assertions lack sufficient control-state evidence to distinguish blocked application from harness error; remain unclassified.',
                'Declared implementation expectations are source controls, not independent defect truth; unresolved acceptance policy does not erase other HTTP/state observations.',
                'No pair equality, human adjudication, root-cause grouping, prevalence or efficacy is computed.',
            ]}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('run_directory', type=Path)
    args = parser.parse_args()
    try:
        output = summarize_run(args.run_directory)
    except (OSError, ValueError, KeyError, TypeError, AttributeError) as error:
        output = {'kind': 'realworld_component_observations', 'status': 'incomplete_or_invalid_evidence',
                  'run_issues': ['unreadable_or_malformed_run:' + type(error).__name__ + ':' + str(error)], 'cases': []}
    print(json.dumps(output, indent=2, ensure_ascii=False))
    return 0 if output['status'] == 'complete_observations' else 1


if __name__ == '__main__':
    raise SystemExit(main())
