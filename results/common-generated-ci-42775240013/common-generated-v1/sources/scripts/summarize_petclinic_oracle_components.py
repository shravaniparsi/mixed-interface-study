#!/usr/bin/env python3
"""Read-only, source-qualified reduction of PetClinic development evidence.

No applications run and no input files change. Component observations are not
fault labels, independent samples, or a completed primary evaluation freeze.
Exit 1 means the recorded evidence is incomplete/unsupported, not a defect.
"""
import argparse
from collections import Counter
from copy import deepcopy
import hashlib
import json
from pathlib import Path

RUNNER_SHA256 = 'ca662bb1750b47c6c1b0ca8d9895f9199413fd99feef9de1d44b59622223c625'
REGISTRY_SHA256 = '2c08ddeebdab4f3bd5594c85256831a569e2a381b4d1bad948b10572cd17a693'
JAR_SHA256 = '26f35f880229dfcae06a796574a930236361a9403c69355aa3efea9cce77fb65'
BACKEND_COMMIT = '5180cc9bd0163393c4e628bedc1bc4c27cfaab1b'
FRONTEND_COMMIT = 'fba8956cbdd04e09973f81eb39379955a825bfc3'
INITIAL_STATE_SHA256 = 'b3c3071604bd547f72384673b183f160d4f7bf43034d3638bf73b325ba5a143a'
ACTOR = 'anonymous native default'
POLICY_CASES = {'owner_city_whitespace', 'visit_description_whitespace'}
REPLAY_CASES = POLICY_CASES | {'owner_first_name_hyphen'}
COMPONENTS = ('immediate_response', 'prefix_state_reads', 'assigned_api_continuation',
              'assigned_native_continuation', 'shared_post_continuation_api_readback',
              'integrity', 'unresolved_policy')
TEMPLATES = {'owner_address_edit': ('owners', {'address': '2 Pilot Lane'}),
             'pet_rename': ('pets', {'name': 'Renamedpet'}),
             'visit_reschedule': ('visits', {'date': '2026-11-07'})}
PHASES = {'reset_verification', 'prefix_setup', 'candidate_prefix', 'post_prefix_state',
          'continuation_read', 'continuation_edit', 'continuation',
          'continuation_readback', 'relationship_readback'}
STATUSES = {'continuation_passed', 'ui_blocked', 'prefix_rejected', 'runner_or_assertion_failure'}


def canonical_bytes(value):
    """Match the pinned JS canonical hash for the recorded finite JSON domain."""
    if value is None or type(value) is bool or isinstance(value, str):
        return json.dumps(value, ensure_ascii=False, separators=(',', ':')).encode('utf-8')
    if type(value) is int and abs(value) <= 2**53 - 1:
        return str(value).encode('ascii')
    if isinstance(value, list):
        return b'[' + b','.join(canonical_bytes(x) for x in value) + b']'
    if isinstance(value, dict) and all(isinstance(k, str) for k in value):
        def index(k):
            return k.isascii() and k.isdecimal() and str(int(k)) == k and int(k) < 2**32-1
        keys = sorted((k for k in value if index(k)), key=int)
        keys += sorted((k for k in value if not index(k)), key=lambda x: x.encode('utf-16-be'))
        return b'{' + b','.join(canonical_bytes(k)+b':'+canonical_bytes(value[k]) for k in keys) + b'}'
    raise ValueError('unsupported_state_value:' + type(value).__name__)


def digest(value):
    return hashlib.sha256(canonical_bytes(value)).hexdigest()


def same(a, b):
    return canonical_bytes(a) == canonical_bytes(b)


def locate(graph, kind, identifier):
    if not isinstance(graph, list):
        return None
    found = []
    for owner in graph:
        if not isinstance(owner, dict):
            continue
        if kind == 'owners' and owner.get('id') == identifier:
            found.append((owner, None, owner))
        for pet in owner.get('pets', []):
            if kind == 'pets' and pet.get('id') == identifier:
                found.append((owner, pet, pet))
            for visit in pet.get('visits', []):
                if kind == 'visits' and visit.get('id') == identifier:
                    found.append((owner, pet, visit))
    return found[0] if len(found) == 1 else None


def reduce_case(result, registered, registry, *, source_qualified=True):
    """Preserve observations on invalid evidence; never convert a catch into a bug."""
    issues, unavailable = [], []
    components = {k: {'checks': [], 'observations': [], 'failed_check_ids': []} for k in COMPONENTS}
    oracle = result.get('oracle')
    assigned = 'assigned_api_continuation' if oracle == 'api_semantic' else 'assigned_native_continuation'
    route = 'api-' + ('api' if oracle == 'api_semantic' else 'ui' if oracle == 'fresh_ui' else 'unknown')
    template = registered.get('template')
    kind, change = TEMPLATES.get(template, ('unknown', {}))
    accepted = result.get('prefix_status') == 201
    policy = registered.get('id') in POLICY_CASES
    trace = result.get('trace', [])
    if not isinstance(trace, list):
        trace = []; issues.append('trace_not_a_list')
    for event in trace:
        if (not isinstance(event, dict) or event.get('source') not in {'direct_api', 'ui_network'}
                or event.get('phase') not in PHASES or type(event.get('status')) is not int
                or not isinstance(event.get('path'), str)
                or any(k not in event for k in ('request', 'response', 'method'))):
            issues.append('malformed_or_unknown_trace_event')
    trace = [x for x in trace if isinstance(x, dict)]
    if result.get('checks'):
        issues.append('unsupported_check_vocabulary_in_pinned_runner_output')

    def check(component, name, passed, detail=None, policy_scope=False):
        target = 'unresolved_policy' if policy_scope else component
        item = {'id': name, 'passed': bool(passed), 'origin_component': component,
                'scope': 'unresolved_policy' if policy_scope else 'recorded_source_predicate'}
        if detail is not None:
            item['detail'] = detail
        components[target]['checks'].append(item)
        if not passed:
            components[target]['failed_check_ids'].append(name)
        return bool(passed)

    def integrity(name, passed):
        check('integrity', name, passed)
        if not passed:
            issues.append('integrity_mismatch:' + name)

    def events(source, phase, method, path=None):
        return [x for x in trace if (x.get('source'), x.get('phase'), x.get('method')) == (source, phase, method)
                and (path is None or x.get('path') == path)]

    def one(source, phase, method, path=None):
        found = events(source, phase, method, path)
        if len(found) != 1:
            issues.append('missing_or_duplicate_trace:' + ':'.join((source, phase, method, path or '*')))
            return None
        return found[0]

    def state(name, value, expected_hash):
        if not isinstance(value, list):
            issues.append('missing_graph:' + name); return
        try:
            actual = digest(value)
            integrity(name + '_hash', isinstance(expected_hash, str) and actual == expected_hash)
        except (ValueError, UnicodeError) as error:
            issues.append('unverifiable_graph:' + name + ':' + str(error))

    if not source_qualified:
        issues.append('containing_run_incomplete_or_unsupported')
    integrity('registered_candidate_identity', result.get('candidate_id') == registered.get('id') and result.get('template') == template)
    integrity('recorded_actor', result.get('actor') == ACTOR)
    if oracle not in {'api_semantic', 'fresh_ui'} or template not in TEMPLATES:
        issues.append('unknown_oracle_or_template')
    if result.get('status') not in STATUSES:
        issues.append('unknown_aggregate_status')
    if result.get('status') == 'runner_or_assertion_failure' or result.get('error'):
        issues.append('unexplained_runner_or_assertion_failure')
    for key in ('started_at', 'finished_at'):
        if not isinstance(result.get(key), str) or not result[key]:
            issues.append('missing_timestamp:' + key)
    if type(result.get('backend_pid')) is not int or result.get('backend_pid', 0) <= 1:
        issues.append('missing_backend_pid')
    for key in ('page_errors', 'blocked_external_requests'):
        if result.get(key) != []:
            issues.append('unresolved_browser_evidence:' + key)
    if type(result.get('continuation_reachable')) is not bool or result['continuation_reachable'] != accepted:
        issues.append('prefix_continuation_reachability_mismatch')

    reset = one('direct_api', 'reset_verification', 'GET', '/owners')
    initial = reset.get('response') if reset else None
    if reset:
        integrity('reset_response_200', reset['status'] == 200)
    state('initial_state', initial, result.get('initial_state_sha256'))
    integrity('pinned_initial_graph', result.get('initial_state_sha256') == INITIAL_STATE_SHA256
              and isinstance(initial, list) and len(initial) == 10)
    prefix = one('direct_api', 'candidate_prefix', 'POST')
    if prefix:
        integrity('registered_prefix_payload', same(prefix.get('request'), registered.get('payload')))
        integrity('prefix_response_record', prefix.get('status') == result.get('prefix_status')
                  and same(prefix.get('response'), result.get('prefix_response')))
    code = result.get('prefix_status')
    response_class = ('accepted_201' if code == 201 else 'server_error' if type(code) is int and 500 <= code < 600
                      else 'client_rejection' if type(code) is int and 400 <= code < 500 else 'other_or_missing_response')
    components['immediate_response']['observations'].append({'id': 'candidate_http_response', 'status': code, 'response_class': response_class,
        'response': result.get('prefix_response'), 'interpretation': 'A 5xx response is not a clean validation rejection.'})
    if type(code) is int:
        check('immediate_response', 'prefix_not_server_error', not 500 <= code < 600)
    else:
        issues.append('missing_prefix_http_status')

    setup = events('direct_api', 'prefix_setup', 'POST')
    owner = pet = None
    target = result.get('prefix_response') if accepted else None
    if template != 'owner_address_edit':
        owner_event = next((x for x in setup if x.get('path') == '/owners'), None)
        if not owner_event:
            issues.append('missing_owner_setup')
        else:
            integrity('owner_setup', owner_event['status'] == 201 and same(owner_event['request'], registry['fixtures']['owner']))
            owner = owner_event.get('response')
        if not isinstance(owner, dict) or type(owner.get('id')) is not int:
            issues.append('missing_bound_owner'); owner = None
    if template == 'owner_address_edit':
        expected_prefix_path = '/owners'; expected_setup_paths = []
        owner = target if isinstance(target, dict) else None
    elif owner:
        if template == 'pet_rename':
            expected_prefix_path = f"/owners/{owner['id']}/pets"
            pet = target if isinstance(target, dict) else None
            expected_setup_paths = ['/owners']
            if accepted and pet and type(pet.get('id')) is int:
                visit_path = f"/owners/{owner['id']}/pets/{pet['id']}/visits"
                expected_setup_paths.append(visit_path)
                linked = [x for x in setup if x.get('path') == visit_path]
                integrity('linked_visit_setup', len(linked) == 1 and linked[0]['status'] == 201
                          and same(linked[0]['request'], registry['fixtures']['visit']))
        else:
            pet_path = f"/owners/{owner['id']}/pets"
            pet_events = [x for x in setup if x.get('path') == pet_path]
            integrity('pet_setup', len(pet_events) == 1 and pet_events[0]['status'] == 201
                      and same(pet_events[0]['request'], registry['fixtures']['pet']))
            pet = pet_events[0].get('response') if len(pet_events) == 1 else None
            expected_setup_paths = ['/owners', pet_path]
            expected_prefix_path = f"{pet_path}/{pet['id']}/visits" if isinstance(pet, dict) and type(pet.get('id')) is int else None
    else:
        expected_prefix_path = None; expected_setup_paths = []
    integrity('prefix_resource_binding', prefix is not None and expected_prefix_path is not None and prefix.get('path') == expected_prefix_path)
    integrity('setup_operation_bundle', [x.get('path') for x in setup] == expected_setup_paths)
    post = one('direct_api', 'post_prefix_state', 'GET', '/owners')
    graph = result.get('post_prefix_graph')
    state('post_prefix_state', graph, result.get('post_prefix_state_sha256'))
    if post:
        integrity('post_prefix_graph_record', post['status'] == 200 and same(post['response'], graph))
        components['prefix_state_reads']['observations'].append({'id':'post_prefix_graph_read','status':post['status'],'recorded_graph_sha256':result.get('post_prefix_state_sha256')})
    if not accepted:
        downstream = [x for x in trace if x.get('phase') in {'continuation_read', 'continuation_edit', 'continuation', 'continuation_readback', 'relationship_readback'}]
        if downstream or any(k in result for k in ('before', 'after', 'final_graph', 'ui_submit_disabled')):
            issues.append('rejected_prefix_has_downstream_evidence')
        if template == 'owner_address_edit' and isinstance(graph, list) and isinstance(initial, list):
            check('prefix_state_reads', 'failed_owner_create_graph_unchanged', same(initial, graph))
        else:
            unavailable.append('pre_candidate_snapshot_after_valid_setup_not_recorded; failed-prefix rollback not established')
        if result.get('status') not in {'prefix_rejected', 'runner_or_assertion_failure'}:
            issues.append('aggregate_status_inconsistent_with_rejected_prefix')
        audit = {'producer_request': prefix.get('request') if prefix else None, 'continuation_request': None}
    else:
        if not isinstance(target, dict) or type(target.get('id')) is not int:
            issues.append('missing_returned_target_identity'); target = {}
        target_id = target.get('id'); path = '/' + kind + '/' + str(target_id)
        found = locate(graph, kind, target_id)
        if not found:
            issues.append('missing_or_duplicate_target_in_prefix_graph')
            graph_owner = graph_pet = graph_target = None
        else:
            graph_owner, graph_pet, graph_target = found
        before_event = one('direct_api', 'continuation_read', 'GET', path)
        before = result.get('before')
        if not isinstance(before, dict):
            issues.append('missing_loaded_target'); before = {}
        if before_event:
            integrity('shared_before_record', before_event['status'] == 200 and same(before_event['response'], before))
        if isinstance(graph, list) and before:
            check('prefix_state_reads', 'target_read_matches_prefix_graph', graph_target is not None and same(before, graph_target))
        else:
            unavailable.append('target_prefix_graph_comparison_missing_input')
        supplied = registered['payload']
        if target:
            check('immediate_response', 'accepted_input_values_preserved', all(k in target and same(target[k], v) for k, v in supplied.items()))
        else:
            unavailable.append('accepted_input_value_comparison_missing_response')
        bindings_ok = owner is not None and graph_owner is not None and owner.get('id') == graph_owner.get('id') and before.get('id') == target_id
        if template == 'pet_rename':
            bindings_ok = bindings_ok and before.get('ownerId') == owner.get('id')
        elif template == 'visit_reschedule':
            bindings_ok = bindings_ok and isinstance(pet, dict) and before.get('petId') == pet.get('id') and graph_pet is not None and graph_pet.get('ownerId') == owner.get('id')
        check('prefix_state_reads', 'returned_relationship_bindings', bindings_ok)
        expected = {**before, **change}
        if kind == 'owners':
            payload = {'id': target_id, **{k: expected.get(k) for k in ('firstName','lastName','address','city','telephone')}}
        elif kind == 'pets':
            payload = {'id': target_id, 'name': expected.get('name'), 'birthDate': expected.get('birthDate'), 'type': expected.get('type')}
        else:
            payload = {'id': target_id, 'pet': graph_pet, 'date': expected.get('date'), 'description': expected.get('description')}
        disabled = result.get('ui_submit_disabled') is True and oracle == 'fresh_ui'
        if oracle == 'fresh_ui':
            reads = events('ui_network', 'continuation', 'GET', '/petclinic/api' + path)
            if not reads or result.get('fresh_ui_read_observed') is not True:
                issues.append('missing_fresh_native_target_read')
            else:
                check(assigned, 'native_target_load_matches_bound_state', any(x['status'] == 200 and same(x['response'], before) for x in reads))
            if kind in {'pets', 'visits'} and graph_owner:
                owner_reads = events('ui_network', 'continuation', 'GET', '/petclinic/api/owners/' + str(graph_owner['id']))
                if not owner_reads:
                    issues.append('missing_native_bound_owner_read')
                else:
                    check(assigned, 'native_bound_owner_load', any(x['status'] == 200 and same(x['response'], graph_owner) for x in owner_reads))
            if kind == 'visits' and graph_pet:
                pet_reads = events('ui_network', 'continuation', 'GET', '/petclinic/api/pets/' + str(before.get('petId')))
                if not pet_reads:
                    issues.append('missing_native_bound_pet_read')
                else:
                    check(assigned, 'native_bound_pet_load', any(x['status'] == 200 and same(x['response'], graph_pet) for x in pet_reads))
            if kind == 'pets':
                types = events('ui_network', 'continuation', 'GET', '/petclinic/api/pettypes')
                if not types:
                    issues.append('missing_native_pet_type_choices')
                else:
                    check(assigned, 'native_type_choice_matches_bound_type', any(x['status'] == 200 and isinstance(x['response'], list) and any(same(t, before.get('type')) for t in x['response']) for x in types))
            fields = result.get('loaded_ui_fields')
            if kind == 'owners':
                expected_fields = {k: before.get(k) for k in ('firstName','lastName','address','city','telephone')}
            elif kind == 'pets':
                expected_fields = {'name': before.get('name'), 'birthDate': str(before.get('birthDate')).replace('-', '/'),
                                   'typeId': str(before.get('type', {}).get('id')),
                                   'owner_name': (str(graph_owner.get('firstName'))+' '+str(graph_owner.get('lastName'))) if graph_owner else None}
            else:
                expected_fields = {'date': str(before.get('date')).replace('-', '/'), 'description': before.get('description')}
            if not isinstance(fields, dict) or set(fields) != set(expected_fields):
                issues.append('missing_or_unknown_native_loaded_fields')
            else:
                check(assigned, 'native_loaded_fields_match_projection', same(fields, expected_fields))
            if result.get('ui_edit_intended') != change:
                issues.append('missing_or_wrong_native_edit_intent')
            if type(result.get('ui_submit_disabled')) is not bool:
                issues.append('missing_native_submit_state')
            else:
                check(assigned, 'native_submit_enabled', not disabled, {'disabled': disabled}, policy_scope=policy)
                components[assigned]['observations'].append({'id':'native_submission_state','disabled':disabled,'aggregate_status':result.get('status')})
            puts = events('ui_network', 'continuation', 'PUT', '/petclinic/api' + path)
            if events('direct_api', 'continuation_edit', 'PUT'):
                issues.append('api_action_in_native_branch')
            if disabled and puts:
                issues.append('disabled_native_submit_has_put')
            if disabled and 'continuation_http_status' in result:
                issues.append('disabled_native_submit_has_response_status')
        else:
            puts = events('direct_api', 'continuation_edit', 'PUT', path)
            if events('ui_network', 'continuation', 'PUT') or any(k in result for k in ('ui_submit_disabled','loaded_ui_fields','fresh_ui_read_observed')):
                issues.append('native_action_evidence_in_api_branch')
            if before_event:
                check(assigned, 'api_target_load_200', before_event['status'] == 200)
            if kind == 'visits' and graph_pet:
                extra = one('direct_api', 'continuation_read', 'GET', '/pets/' + str(before.get('petId')))
                if extra:
                    check(assigned, 'api_bound_pet_load', extra['status'] == 200 and same(extra['response'], graph_pet))
        if not disabled:
            if len(puts) != 1:
                issues.append('missing_or_duplicate_assigned_put')
            else:
                payload_matches = check(assigned, 'assigned_payload_matches_bound_intent', same(puts[0]['request'], payload))
                if oracle == 'api_semantic' and not payload_matches:
                    issues.append('api_payload_differs_from_bound_intent')
                check(assigned, 'assigned_update_status_204', puts[0]['status'] == 204)
                integrity('assigned_response_status_record', result.get('continuation_http_status') == puts[0]['status'])
        after_event = one('direct_api', 'continuation_readback', 'GET', path)
        graph_event = one('direct_api', 'relationship_readback', 'GET', '/owners')
        after = result.get('after'); final_graph = result.get('final_graph')
        if not isinstance(after, dict):
            issues.append('missing_final_target')
        if after_event:
            check('shared_post_continuation_api_readback', 'target_readback_status_200', after_event['status'] == 200)
            integrity('final_target_record', after_event['status'] == 200 and same(after_event['response'], after))
        if graph_event:
            check('shared_post_continuation_api_readback', 'graph_readback_status_200', graph_event['status'] == 200)
            integrity('final_graph_record', graph_event['status'] == 200 and same(graph_event['response'], final_graph))
        state('final_state', final_graph, result.get('final_state_sha256'))
        if isinstance(after, dict) and before:
            check('shared_post_continuation_api_readback', 'final_target_preservation', same(after, before if disabled else expected))
        else:
            unavailable.append('final_target_preservation_missing_input')
        expected_graph = deepcopy(graph)
        final_target = locate(expected_graph, kind, target_id)
        if final_target and not disabled:
            final_target[2].update(change)
        if isinstance(graph, list) and isinstance(final_graph, list):
            check('shared_post_continuation_api_readback', 'complete_graph_preservation', final_target is not None and same(final_graph, expected_graph))
        else:
            unavailable.append('complete_graph_preservation_missing_input')
        if result.get('status') not in ({'ui_blocked','runner_or_assertion_failure'} if disabled else {'continuation_passed','runner_or_assertion_failure'}):
            issues.append('aggregate_status_inconsistent_with_assigned_action')
        audit = {'producer_request': prefix.get('request') if prefix else None, 'continuation_request': puts[0]['request'] if len(puts)==1 else None,
                 'bound_intended_request': payload, 'target_id':target_id,'owner_id':owner.get('id') if owner else None,
                 'pet_id':graph_pet.get('id') if graph_pet else None}
    # The source-pinned runner emits only this finite operation vocabulary.
    allowed_direct = {('reset_verification','GET','/owners'), ('post_prefix_state','GET','/owners')}
    if expected_prefix_path:
        allowed_direct.add(('candidate_prefix','POST',expected_prefix_path))
    allowed_direct.update(('prefix_setup','POST',p) for p in expected_setup_paths)
    allowed_native = set()
    if accepted:
        allowed_direct.update({('continuation_read','GET',path), ('continuation_readback','GET',path), ('relationship_readback','GET','/owners')})
        if oracle == 'api_semantic':
            allowed_direct.add(('continuation_edit','PUT',path))
            if kind == 'visits' and graph_pet:
                allowed_direct.add(('continuation_read','GET','/pets/'+str(before.get('petId'))))
        else:
            allowed_native.add(('continuation','GET','/petclinic/api'+path))
            allowed_native.add(('continuation','PUT','/petclinic/api'+path))
            if graph_owner:
                allowed_native.add(('continuation','GET','/petclinic/api/owners/'+str(graph_owner['id'])))
            if graph_pet:
                allowed_native.add(('continuation','GET','/petclinic/api/pets/'+str(graph_pet['id'])))
            if kind == 'pets':
                allowed_native.add(('continuation','GET','/petclinic/api/pettypes'))
    for event in trace:
        event_key=(event.get('phase'),event.get('method'),event.get('path'))
        if event_key not in (allowed_direct if event.get('source')=='direct_api' else allowed_native):
            issues.append('unregistered_trace_operation:'+str(event_key))
    issues = sorted(set(issues))
    for name, component in components.items():
        component['mismatch_observed'] = bool(component['failed_check_ids'])
        applicable = bool(component['checks'] or component['observations'])
        if name.startswith('assigned_'):
            applicable = accepted and name == assigned
        if name == 'shared_post_continuation_api_readback':
            applicable = accepted
            component['assigned_action_interface'] = route.split('-')[-1] if accepted else None
            component['observation_mechanism'] = 'Shared direct API target/graph readback; not native-only detection.'
        component['comparison_eligible'] = applicable and not issues and name != 'unresolved_policy'
        component['status'] = ('policy_observations_only' if name == 'unresolved_policy' and applicable else
            'not_reached_prefix_rejected' if not accepted and (name.startswith('assigned_') or name == 'shared_post_continuation_api_readback') else
            'not_applicable' if not applicable else 'incomplete_or_invalid_evidence' if issues else
            'check_mismatch_observed' if component['mismatch_observed'] else 'no_check_mismatch_observed')
    return {'case_id':result.get('candidate_id'),'route':route,'template':template,
        'accepted_prefix':accepted,'execution_evidence_complete':not issues,'evidence_issues':issues,
        'unavailable_evidence':unavailable,'policy_unresolved':policy,'components':components,'binding_audit':audit,
        'initial_state_sha256':result.get('initial_state_sha256'),'post_prefix_state_sha256':result.get('post_prefix_state_sha256'),
        'final_state_sha256':result.get('final_state_sha256'), 'backend_pid':result.get('backend_pid'),
        'historical_status':'known_issue_reproduction_not_new_discovery' if registered['id']=='owner_first_name_hyphen' else 'development_only',
        'interpretation':'Source-qualified recorded predicates; no defect/root-cause or detection-overlap verdict. Unexplained assertions remain unresolved.'}


def summarize_run(directory):
    directory = Path(directory).resolve()
    raw_summary = (directory/'summary.json').read_bytes(); summary = json.loads(raw_summary)
    issues = []; hashes = {}
    for name, pin in [('executed_boundary_slice.mjs',RUNNER_SHA256),('registered-candidates.json',REGISTRY_SHA256)]:
        path=directory/name
        if not path.is_file(): issues.append('missing_pinned_artifact:'+name); continue
        data=path.read_bytes();hashes[name]=hashlib.sha256(data).hexdigest()
        if hashes[name]!=pin: issues.append('unsupported_pinned_artifact:'+name)
    registry=json.loads((directory/'registered-candidates.json').read_bytes())
    candidates={c['id']:c for c in registry['candidates']}
    if registry.get('oracles')!=['api_semantic','fresh_ui'] or registry.get('actor')!=ACTOR:
        issues.append('unsupported_registry_oracle_or_actor')
    for name,pin in [('runner_sha256',RUNNER_SHA256),('registry_sha256',REGISTRY_SHA256),('jar_sha256',JAR_SHA256),('backend_commit',BACKEND_COMMIT),('frontend_commit',FRONTEND_COMMIT)]:
        if summary.get(name)!=pin:issues.append('summary_pin_mismatch:'+name)
    for name,expected in [('independent_process_reset_per_branch',True),('source_modified',False),('backend_stopped',True)]:
        if summary.get(name) is not expected:issues.append('run_guard:'+name)
    if not summary.get('finished_at') or summary.get('stopped_after_harness_or_pair_failure'):
        issues.append('run_not_completed')
    entries=summary.get('branches',[]);keys=[(x.get('candidate_id'),x.get('oracle')) for x in entries]
    ids={k[0] for k in keys}
    scope='full_development_sweep' if ids==set(candidates) else 'diagnostic_replay' if ids==REPLAY_CASES else 'unsupported_or_partial_selection'
    if scope=='unsupported_or_partial_selection' or len(keys)!=len(set(keys)) or set(keys)!={(c,o) for c in ids for o in ['api_semantic','fresh_ui']}:
        issues.append('missing_duplicate_or_unregistered_branches')
    loaded=[]
    for entry in entries:
        cid,oracle=entry.get('candidate_id'),entry.get('oracle');name=entry.get('result')
        if cid not in candidates or oracle not in {'api_semantic','fresh_ui'} or name!=f'{cid}-{oracle}.json':
            issues.append('invalid_branch_identity_or_path');continue
        path=directory/name
        if path.resolve().parent!=directory:issues.append('branch_path_escapes_run');continue
        try:
            data=path.read_bytes();result=json.loads(data)
        except (OSError,ValueError):issues.append('unreadable_branch:'+name);continue
        hashes[name]=hashlib.sha256(data).hexdigest()
        for key in ('candidate_id','oracle','status','prefix_status'):
            if result.get(key)!=entry.get(key):issues.append('summary_branch_mismatch:'+name+':'+key)
        loaded.append((result,candidates[cid]))
    observations=[]
    for result,candidate in loaded:
        try: observations.append(reduce_case(result,candidate,registry,source_qualified=not issues))
        except (KeyError,TypeError,ValueError,AttributeError,UnicodeError) as error:
            observations.append({'case_id':result.get('candidate_id'),'route':'api-'+('api' if result.get('oracle')=='api_semantic' else 'ui'),
                'accepted_prefix':result.get('prefix_status')==201,'execution_evidence_complete':False,
                'evidence_issues':['malformed_branch:'+type(error).__name__], 'components':{},'interpretation':'Malformed evidence; no clean comparison.'})
    by_key={(o['case_id'],o['route']):o for o in observations};pair_rows=[]
    raw_by_key={(r.get('candidate_id'),r.get('oracle')):r for r,_ in loaded}
    reported=summary.get('pairs',[])
    if len(reported)!=len(ids) or len({p.get('candidate_id') for p in reported})!=len(reported):issues.append('missing_or_duplicate_pair_records')
    for cid in sorted(ids):
        a=by_key.get((cid,'api-api'));u=by_key.get((cid,'api-ui'))
        if not a or not u:issues.append('missing_pair:'+str(cid));continue
        reported_pair=[p for p in reported if p.get('candidate_id')==cid]
        initial=a.get('initial_state_sha256')==u.get('initial_state_sha256') and bool(a.get('initial_state_sha256'))
        post=a.get('post_prefix_state_sha256')==u.get('post_prefix_state_sha256') and bool(a.get('post_prefix_state_sha256'))
        final=a.get('final_state_sha256')==u.get('final_state_sha256') and bool(a.get('final_state_sha256'))
        if not initial or not post or a.get('backend_pid')==u.get('backend_pid'):issues.append('independent_pair_reset_or_prefix_mismatch:'+str(cid))
        if len(reported_pair)!=1 or any(reported_pair[0].get(k)!=v for k,v in [('initial_state_equal',initial),('post_prefix_state_equal',post),('final_state_equal',final)]):issues.append('pair_summary_mismatch:'+str(cid))
        if len(reported_pair)==1:
            pair=reported_pair[0]
            expected_metadata={'template':candidates[cid]['template'],
                'api_status':raw_by_key[(cid,'api_semantic')].get('status'),
                'ui_status':raw_by_key[(cid,'fresh_ui')].get('status')}
            if any(pair.get(k)!=v for k,v in expected_metadata.items()):
                issues.append('pair_metadata_mismatch:'+str(cid))
        ar=a.get('binding_audit',{}).get('continuation_request');ur=u.get('binding_audit',{}).get('continuation_request')
        pair_rows.append({'case_id':cid,'initial_states_equal':initial,'post_prefix_states_equal':post,
            'independent_backend_pids':a.get('backend_pid')!=u.get('backend_pid'),
            'both_continuation_payloads_available':ar is not None and ur is not None,
            'continuation_payloads_equal':same(ar,ur) if ar is not None and ur is not None else None,
            'final_states_equal':final,'defect_or_detection_overlap_classification':'not_performed'})
    if issues:
        for observation in observations:
            observation['execution_evidence_complete']=False
            observation['evidence_issues']=sorted(set(observation['evidence_issues']+['containing_run_incomplete_or_unsupported']))
            for component in observation['components'].values():
                component['comparison_eligible']=False
                if component.get('status') not in {'not_applicable','not_reached_prefix_rejected','policy_observations_only'}:component['status']='incomplete_or_invalid_evidence'
    complete=not issues and len(observations)==len(entries) and all(o['execution_evidence_complete'] for o in observations)
    return {'schema_version':1,'kind':'petclinic_component_observations','status':'complete_observations' if complete else 'incomplete_or_invalid_evidence',
        'scope':scope,'input_directory':str(directory),'input_summary_sha256':hashlib.sha256(raw_summary).hexdigest(),'input_file_sha256':hashes,
        'reducer_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),'supported_runner_sha256':RUNNER_SHA256,'supported_registry_sha256':REGISTRY_SHA256,
        'primary_freeze_complete':False,'derived_checks_are_retrospective':True,
        'derivation_sources':{
            'runtime_predicates':'executed_boundary_slice.mjs at supported_runner_sha256',
            'native_pet_display':'https://github.com/spring-petclinic/spring-petclinic-angular/blob/'+FRONTEND_COMMIT+'/src/app/pets/pet-edit/pet-edit.component.html#L29',
            'native_pet_serialization':'https://github.com/spring-petclinic/spring-petclinic-angular/blob/'+FRONTEND_COMMIT+'/src/app/pets/pet-edit/pet-edit.component.ts#L88-L98',
            'native_visit_serialization':'https://github.com/spring-petclinic/spring-petclinic-angular/blob/'+FRONTEND_COMMIT+'/src/app/visits/visit-edit/visit-edit.component.ts#L89-L98'},'run_issues':sorted(set(issues)),'case_count':len(observations),'candidate_pairs':pair_rows,'cases':observations,
        'component_status_counts':{k:dict(Counter(o['components'].get(k,{}).get('status','missing_component') for o in observations)) for k in COMPONENTS},
        'limitations':['Completeness is for extraction of the pinned development record, not primary execution readiness.',
            'Actor is the recorded anonymous native configuration, not independently authenticated identity evidence.',
            'Per-branch exit and owned-browser cleanup confirmations were not recorded; backend_stopped is only a run-level declaration.',
            'No pre-candidate snapshot exists after valid pet/visit setup; failed-prefix rollback is unavailable there.',
            'Shared API readback remains separate from native loading/submission observations; no overlap/root-cause adjudication performed.',
            'Whitespace policy remains unresolved; hyphenated-name observation is a known historical reproduction, not new discovery.',
            'Derived field/binding checks audit already recorded values; they do not add executions, samples or previously frozen runtime assertions.']}


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('run_directory',type=Path);args=parser.parse_args()
    try:output=summarize_run(args.run_directory)
    except (OSError,ValueError,KeyError,TypeError,AttributeError,UnicodeError) as error:
        output={'kind':'petclinic_component_observations','status':'incomplete_or_invalid_evidence','run_issues':['unreadable_or_malformed_run:'+type(error).__name__+':'+str(error)],'cases':[],'primary_freeze_complete':False}
    print(json.dumps(output,indent=2,ensure_ascii=False));return 0 if output['status']=='complete_observations' else 1


if __name__=='__main__':raise SystemExit(main())
