#!/usr/bin/env python3
"""Source-qualified extraction for the prospective RealWorld control adapter.

The reduction logic is versioned separately from the historical reducer. File
loading admits only the archived control cohort; this is not boundary validation.
"""
from copy import deepcopy
import hashlib,json,sys
from pathlib import Path
from urllib.parse import quote
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'))
from mixed_interface.normalization import tag_response
from summarize_realworld_oracle_components import (
    capture_integrity_issues,execution_integrity_issues,COMPONENTS,GENERATED_CHECKS,
    LEGACY_CHECKS as HISTORICAL_CHECKS,ASSIGNED_CHECKS,FIXED_CHECKS as HISTORICAL_FIXED,
    NATIVE_CHECKS,WORKFLOWS,user_state,article_state,EDIT_BODY,COMMENT_BODY,EDIT_BIO)
LEGACY_CHECKS={k:set(v) for k,v in HISTORICAL_CHECKS.items()}
FIXED_CHECKS=dict(HISTORICAL_FIXED)
TAG_CHECKS={'prefix_tag_membership_matches','prefix_tag_response_representation'}
for workflow in ('article-create-edit','article-update-comment'):
    LEGACY_CHECKS[workflow]|=TAG_CHECKS
for name in TAG_CHECKS:FIXED_CHECKS[name]='immediate_response'
HISTORICAL_REDUCER_SHA256='46f84347c249007b5ce5f2fabbc8511053de5454a68115ce437073fe7f6513a4'

def reduce_case(result, run, registered, *, family='legacy', fixture=None, provenance_issues=()):
    """Extract one case after the loader qualifies immutable source/registry bytes.

    The pure function is useful for adversarial tests. Its result is not a
    standalone provenance certificate; use summarize_run for file-backed use.
    Existing booleans are retained with check details; independently recomputed
    input/binding consistency guards do not constitute an application re-test.
    """
    if family!='legacy':raise ValueError('This extension admits only the prospective control family')
    issues = list(provenance_issues) + capture_integrity_issues(result) + execution_integrity_issues(result)
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
        guard(result.get('oracle_revision') == 3, 'unsupported_oracle_revision')
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
        expected['tagList'] = tag_response(expected['tagList'])
        expect(*sorted(TAG_CHECKS))
        verify_check('prefix_tag_membership_matches',tag_response(a.get('tagList'))==expected['tagList'])
        verify_check('prefix_tag_response_representation',a.get('tagList')==expected['tagList'])
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
                    finals=require_event('api', 'GET', comments_path, response=True)
                    final=finals[-1] if finals else {}
                    comments=final.get('data',{}).get('comments',[])
                    verify_check('comment_relationship_persisted',write_status==201 and final.get('status')==200 and len(comments)==1 and comments[0].get('body')==COMMENT_BODY)
                    parents=require_event('api', 'GET', path, response=True)
                    parent=parents[-1] if parents else {}
                    verify_check('parent_article_preserved',parent.get('status')==200 and article_state(parent.get('data',{}).get('article'),slug=True)==article_state(loaded,slug=True))
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
        loaded=loads[0] if loads else {}
        verify_check('comment_loaded_in_parent',loaded.get('status')==200 and any(c.get('id')==cid and c.get('body')==comment.get('body') for c in loaded.get('data',{}).get('comments',[])))
        finals=require_event('api', 'GET', prefix_path, response=True)
        final=finals[-1] if finals else {}
        verify_check('deletion_persisted',write_status==204 and final.get('status')==200 and final.get('data',{}).get('comments')==[])
        parents=require_event('api', 'GET', prefix_path.removesuffix('/comments'), response=True)
        parent=parents[-1] if parents else {}
        verify_check('parent_article_preserved',parent.get('status')==200 and article_state(parent.get('data',{}).get('article'),slug=True)==article_state(fixture.get('base'),slug=True))
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
            profiles=require_event('api', 'GET', '/api/profiles/' + quote(current.get('username', ''), safe="~()*!.'-"), response=True)
            profile=profiles[-1] if profiles else {}
            verify_check('profile_reference_resolvable',profile.get('status')==200 and profile.get('data',{}).get('profile',{}).get('bio')==EDIT_BIO)
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
        if workflow=='profile-update-edit' and consumer=='ui' and accepted:
            verify_check('fresh_ui_principal_matches',bool(native_auth) and user_state(native_auth[-1].get('data',{}).get('user'))==result.get('prefix_state'))
    for name in sorted(expected_checks - seen.keys()):
        issues.append('missing_required_check:' + name)
    for name in sorted(seen.keys() - expected_checks):
        issues.append('unexpected_check_for_branch:' + name)
    finished = result.get('status' if generated else 'execution_status') == 'completed'
    guard(finished and bool(result.get('finished_at' if generated else 'completed_at')), 'case_not_finished')
    guard(run.get('status') == 'passed', 'run_case_not_finished')
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
    integrity = result.get('integrity')
    if isinstance(integrity, dict):
        for item in integrity.get('guards', []):
            component = ('environment_reset_cleanup' if item.get('stage') == 'setup' else
                         'shared_post_continuation_api_readback' if item.get('stage') == 'shared_readback' else
                         assigned if item.get('stage') == 'continuation' else
                         'producer_native_controls' if item.get('source') == 'ui' else 'immediate_response')
            add(component, 'integrity:' + item.get('name', 'unknown'), item.get('passed'), item,
                'execution_comparability_observation_not_adjudicated_defect')
        rejection = integrity.get('rejection')
        if isinstance(rejection, dict):
            value = rejection.get('status')
            parts['prefix_state_reads']['observations'].append({'id': 'full_observable_rejection_state', 'classification': value,
                'before': integrity.get('before'), 'after': rejection.get('after')})
            if value in ('unchanged', 'changed'):
                add('prefix_state_reads', 'full_observable_rejection_state_unchanged', value == 'unchanged',
                    {'classification': value}, 'bounded_api_visible_state_not_database_atomicity')
            parts['prefix_state_reads']['limitations'] = ['Snapshot covers current-user public fields, all listed own articles, global tag membership and their comments; excludes auth tokens and unobserved database state.']
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



def validate_timing(result, branch):
    """Validate operational timing without attributing it to diagnostic checks."""
    from validate_realworld_paired_controls import timeline
    import math
    timing=result['timing'];timeline(timing['spans'],timing['total_s']);timeline(branch['timing'],branch['total_s'])
    allowed={'adapter_initialization','authentication_session','prefix_state_inspection','producer',
             'assigned_continuation','shared_verification','evidence_finalization','browser_teardown'}
    totals={}
    for span in timing['spans']:
        if span['phase'] not in allowed:raise ValueError('Unknown operational timing phase')
        totals[span['phase']]=totals.get(span['phase'],0)+span['end_s']-span['start_s']
    if set(totals)!=set(timing['totals_s']) or any(not math.isfinite(timing['totals_s'][k]) or abs(v-timing['totals_s'][k])>1e-9 for k,v in totals.items()):
        raise ValueError('Per-phase timing totals differ from exclusive spans')
    process=[s for s in branch['timing'] if s['phase']=='adapter_process']
    if len(process)!=1:raise ValueError('Missing/duplicate parent process interval')
    residual=process[0]['end_s']-process[0]['start_s']-timing['total_s']
    if residual<0 or abs(residual-branch['adapter_uninstrumented_process_s'])>1e-9:raise ValueError('Timing hierarchy differs')
    return {'scope':'Operational phase ledger; not pure diagnostic-component cost or selector calibration',
            'parent_spans':deepcopy(branch['timing']),'branch_total_s':branch['total_s'],
            'adapter_timing':deepcopy(timing),'uninstrumented_process_s':residual}


def build():
    from mixed_interface.attribution import normalize_case,compare_pair,counts
    from validate_realworld_paired_controls import validate
    def read(p):return json.loads(p.read_bytes())
    def digest(p):return hashlib.sha256(p.read_bytes()).hexdigest()
    certificate=read(ROOT/'manifests/realworld-paired-component-source-v1.json')
    for name,pin in certificate['dependencies_sha256'].items():
        if digest(ROOT/name)!=pin:raise ValueError('Changed extraction dependency '+name)
    if digest(ROOT/'scripts/summarize_realworld_oracle_components.py')!=HISTORICAL_REDUCER_SHA256:raise ValueError('Historical reducer changed')
    archive=ROOT/certificate['archive_directory'];qualification=read(ROOT/certificate['qualification_manifest'])
    for name,pin in qualification['input_sha256'].items():
        if digest(archive/name)!=pin:raise ValueError('Changed archived evidence '+name)
    verified=validate(archive)
    if verified!=read(archive/'validation.json'):raise ValueError('Hosted validation no longer reproduces')
    summary=read(archive/'summary.json');registry=read(archive/'registered-candidates.json');fixture=read(archive/'fixture-references.json')
    if summary['source_commit']!=certificate['executing_commit']:raise ValueError('Unexpected executing commit')
    mapping=read(ROOT/'manifests/realworld-paired-component-mapping-v1.json')['rules']
    reduced=[];normalized={};raws={};branches={};timings={}
    for branch in summary['branches']:
        raw=read(archive/branch['evidence']);spec=next(c for c in registry['cases'] if c['candidate_id']==branch['candidate_id'])
        result=reduce_case(raw,branch,spec,fixture=fixture)
        if not result['execution_evidence_complete']:raise ValueError('Incomplete component record '+branch['case_id']+': '+str(result['evidence_issues']))
        key='realworld_prospective_controls::'+branch['case_id']
        reduced.append(result);normalized[key]=normalize_case(result,'realworld_prospective_controls',mapping,record_id=key)
        raws[key]=raw;branches[key]=branch;timings[key]=validate_timing(raw,branch)
    pairs=[]
    def command(raw,stage,field):
        values=[g[field] for g in raw['integrity']['guards'] if g['name']=='submitted_command' and g['stage']==stage]
        if len(values)!=1:raise ValueError('Missing or ambiguous command')
        return values[0]
    for spec in registry['cases']:
        keys={channel:'realworld_prospective_controls::'+spec['candidate_id']+'-'+channel+'-r1' for channel in ('api','ui')}
        a,u=(raws[keys[c]] for c in ('api','ui'));ab,ub=(branches[keys[c]] for c in ('api','ui'))
        gates={'same_declared_prefix':a['prefix_interface']==u['prefix_interface']==spec['prefix_interface'],
          'same_initial_state':ab['reset_sha256']==ub['reset_sha256']==summary['fixture_sha256'],
          'same_pre_candidate_state':a['integrity']['before']['readable'] and u['integrity']['before']['readable'] and a['integrity']['before']['data']==u['integrity']['before']['data'],
          'same_observed_prefix_command':command(a,'prefix','observed')==command(u,'prefix','observed'),
          'same_prefix_outcome':a['observations']['prefix_status']==u['observations']['prefix_status'],
          'independent_reset_evidence':ab['backend_exit_confirmed'] and ub['backend_exit_confirmed'] and ab['evidence']!=ub['evidence'],
          'same_accepted_prefix_state':a['prefix_state']==u['prefix_state'],
          'same_intended_consumer_command':command(a,'continuation','expected')==command(u,'continuation','expected')}
        pairs.append(compare_pair(normalized[keys['api']],normalized[keys['ui']],gates,pair_id=spec['candidate_id'],catalog='realworld_prospective_controls',workflow=spec['workflow']))
    paths=['scripts/summarize_realworld_paired_components.py','manifests/realworld-paired-component-source-v1.json','manifests/realworld-paired-component-mapping-v1.json']
    return {'kind':'source_qualified_prospective_control_components','primary_freeze_complete':False,
            'scope':'Separate engineering control cohort; do not pool with the overlapping historical control catalogs.',
            'counts':counts(pairs,normalized,[]),'components':reduced,'records':list(normalized.values()),'pairs':pairs,
            'timing_ledger':timings,'common_fixture_frontend_setup_s':summary['common_fixture_frontend_setup_s'],
            'reset_evidence_scope':'Pinned runner offline-copy/hash records and confirmed backend exits; not interruption qualification.',
            'source_sha256':{p:digest(ROOT/p) for p in paths}}


def main():
    import argparse
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    result=build();path=ROOT/'results/realworld-paired-components-20261107/analysis.json'
    if args.verify:
        if json.loads(path.read_bytes())!=result:raise ValueError('Saved component analysis differs')
    else:
        path.parent.mkdir(exist_ok=True);path.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result['counts'],indent=2))
if __name__=='__main__':main()
