"""Synthetic evidence fixtures for reducer contracts; no application execution.

The fixtures use registered inputs but are not experimental observations.
Historical full runs are checked separately; CI needs no ignored raw artifacts.
"""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest


PROJECT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('realworld_components', PROJECT/'scripts/summarize_realworld_oracle_components.py')
reducer = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(reducer)
REGISTRY = json.loads((PROJECT/'manifests/realworld-boundary-registry-v1.json').read_text())
GENERATED = json.loads((PROJECT/'manifests/realworld-article-generated-pool-v1.json').read_text())


def article(title='Fixture', body='Fixture body.', slug='fixture'):
    return dict(title=title, description='Fixture description', body=body, tagList=[], slug=slug, author={'username':'pilotresearch'})


def check(name, passed=True, **details):
    return dict(name=name, passed=passed, **details)


def positive(workflow='article-create-edit', consumer='api', generated=False):
    """Build structurally complete synthetic positive evidence for one branch."""
    ids = {'article-create-edit':'article-valid', 'article-update-comment':'article-update-unique-partial',
           'comment-create-delete':'comment-body-valid', 'profile-update-edit':'profile-bio-valid'}
    case = copy.deepcopy(next(c for c in REGISTRY['cases'] if c['candidate_id']==ids[workflow]))
    if generated:
        case = copy.deepcopy(next(c for c in GENERATED['cases'] if c['intervention']=='route_only'
                                 and [o['interface'] for o in c['operations']]==['api',consumer]))
    trace = []

    def call(source, method, path, payload, data, status=200):
        request_kind = 'declared_ui_request' if generated and source=='ui' else 'request'
        response_kind = 'ui_response' if generated and source=='ui' else 'response'
        trace.append(dict(sequence=len(trace)+1, phase='deliberately_nonsemantic', type=request_kind,
                          source=source, method=method, path=path, **({'payload':copy.deepcopy(payload)} if payload is not None else {})))
        trace.append(dict(sequence=len(trace)+1, phase='deliberately_nonsemantic', type=response_kind,
                          source=source, method=method, path=path, status=status, data=copy.deepcopy(data)))

    user = dict(username='pilotresearch',email='pilot@example.com',bio='Baseline profile biography.',image=None)
    call('api','POST','/api/users/login',{}, {'user':user})
    call('api','GET','/api/user',None, {'user':user})
    if consumer=='ui' or generated:
        call('ui','POST','/api/users/login',{}, {'user':user})
    fixture = {'base':article(), 'duplicate':article(slug='fixture-duplicate')}
    obs = dict(ui_continuation_started=consumer=='ui', api_continuation_started=consumer=='api',
               prefix_outcome='accepted',continuation_outcome='passed')
    result = dict(schema_version=1,candidate_id=case.get('candidate_id'),workflow=workflow,prefix_interface='api',
                  continuation_interface=consumer,expectation=case['expectation'],oracle_revision=2,
                  execution_status='completed',completed_at='synthetic-unit-fixture',observations=obs,trace=trace,checks=[])
    inputs = case['operations'][0]['input']['article'] if generated else case['prefix_payload']
    if workflow.startswith('article-'):
        create = workflow=='article-create-edit'
        a = article()
        a.update(inputs)
        a['slug']='created' if create else fixture['base']['slug']
        prefix_path='/api/articles' if create else '/api/articles/'+fixture['base']['slug']
        prefix_status=201 if create else 200
        call('api','POST' if create else 'PUT',prefix_path,{'article':inputs},{'article':a},prefix_status)
        obs.update(prefix_status=prefix_status,prefix_response={'article':copy.deepcopy(a)},consumer_read_status=200,continuation_write_status=200 if create else 201)
        result['prefix_state']=reducer.article_state(a,slug=True)
        if not create:
            call('api','GET',prefix_path,None,{'article':a})
            obs['original_reference_read']={'status':200,'article':reducer.article_state(a,slug=True)}
        path='/api/articles/'+a['slug']
        call(consumer,'GET',path,None,{'article':a})
        result['checks']=[check('producer_fields' if generated else 'prefix_fields_match_declared_input'),
                          check('consumer_loaded_state' if generated else 'consumer_loaded_prefix_fields')]
        if create:
            edit={k:a[k] for k in ('title','description','body','tagList')};edit['body']=reducer.EDIT_BODY
            final={**a,**edit}
            call(consumer,'PUT',path,{'article':edit},{'article':final})
            call('api','GET',path,None,{'article':final})
            result['checks'].append(check('persisted_business_state' if generated else 'persisted_continuation'))
            result['final_state']=reducer.article_state(final,generated=generated,slug=not generated)
            if generated:
                result.update(case_id=case['case_id'],route=['api',consumer],status='completed',finished_at='synthetic-unit-fixture',
                              prefix_status=201,accepted_producer=reducer.article_state(a,generated=True),resource_reference=a['slug'],
                              resolved_consumer_input={'article':edit},consumer_status=200,
                              coverage={'data_consumed':True,'state_consumed':True},application_outcome='passed')
                trace.append(dict(sequence=len(trace)+1,type='consumed_dependency',field='article.slug',interface=consumer,reference=a['slug'],status=200))
                if consumer=='ui':
                    result['checks'] += [check('native_form_loaded',observed={k:a[k] for k in ('title','description','body')}),
                                         check('consumer_actual_payload',expected=edit,observed=edit)]
                call('ui','GET',path,None,{'article':final})
                result['checks'] += [check('shared_ui_read'),check('shared_ui_render'),check('one_article')]
                call('api','GET','/api/articles?author=pilotresearch',None,{'articles':[],'articlesCount':0})
                call('api','GET','/api/articles?author=pilotresearch',None,{'articles':[final],'articlesCount':1})
        else:
            comment={'id':1,'body':reducer.COMMENT_BODY,'author':{'username':'pilotresearch'}}
            call(consumer,'POST',path+'/comments',{'comment':{'body':reducer.COMMENT_BODY}},{'comment':comment},201)
            call('api','GET',path+'/comments',None,{'comments':[comment]})
            call('api','GET',path,None,{'article':a})
            result['checks'] += [check('comment_relationship_persisted'),check('parent_article_preserved')]
    elif workflow=='comment-create-delete':
        path='/api/articles/fixture/comments'
        c={'id':1,'body':inputs['body'],'author':{'username':'pilotresearch'}}
        call('api','POST',path,{'comment':inputs},{'comment':c},201)
        obs.update(prefix_status=201,prefix_response={'comment':c},continuation_write_status=204)
        call(consumer,'GET',path,None,{'comments':[c]})
        call(consumer,'DELETE',path+'/1',None,{},204)
        call('api','GET',path,None,{'comments':[]})
        call('api','GET','/api/articles/fixture',None,{'article':fixture['base']})
        result['checks']=[check(n) for n in ('prefix_comment_matches_input','comment_loaded_in_parent','deletion_persisted','parent_article_preserved')]
    else:
        current={**user,**inputs}
        call('api','PUT','/api/user',{'user':inputs},{'user':current})
        call('api','GET','/api/user',None,{'user':current})
        obs.update(prefix_status=200,prefix_response={'user':current},continuation_write_status=200)
        result['prefix_state']=reducer.user_state(current)
        edit={k:current[k] for k in ('username','email')};edit['bio']=reducer.EDIT_BIO
        final={**current,**edit}
        call(consumer,'PUT','/api/user',{'user':edit},{'user':final})
        call('api','GET','/api/user',None,{'user':final})
        call('api','GET','/api/profiles/pilotresearch',None,{'profile':final})
        result['checks']=[check(n) for n in ('prefix_profile_matches_input','profile_edit_persisted','profile_reference_resolvable')]
        if consumer=='ui':result['checks'].append(check('fresh_ui_principal_matches'))
    run=dict(case_id=case['case_id'] if generated else case['candidate_id']+'-'+consumer+'-r1',
             candidate_id=case.get('candidate_id'),continuation=consumer,repetition=1,execution_status='completed',exit_code=0,
             prefix_status=obs.get('prefix_status'),status='completed',route=['api',consumer])
    return result,run,case,fixture


def reduce_fixture(data,generated=False):
    result,run,case,fixture=data
    return reducer.reduce_case(result,run,case,fixture=fixture,family='generated' if generated else 'legacy')


class AttributionTests(unittest.TestCase):
    def test_rejected_prefix_and_server_error_are_separate_observations(self):
        for status in (422,500):
            with self.subTest(status=status):
                result,run,case,fixture=positive()
                case=copy.deepcopy(next(c for c in REGISTRY['cases'] if c['candidate_id']=='article-body-empty'))
                prefix=next(t for t in result['trace'] if t.get('type')=='request' and t.get('path')=='/api/articles')
                response=result['trace'][prefix['sequence']]
                prefix['payload']={'article':case['prefix_payload']}
                response.update(status=status,data={'errors':['synthetic rejection']})
                result['trace']=result['trace'][:response['sequence']]
                follow={'status':200,'data':{'articles':[],'articlesCount':3}}
                for kind,extra in [('request',{}),('response',follow)]:
                    result['trace'].append(dict(sequence=len(result['trace'])+1,type=kind,source='api',method='GET',path='/api/articles?author=pilotresearch',**extra))
                result.update(candidate_id=case['candidate_id'],expectation=case['expectation'],checks=[check('failed_prefix_observable_state_unchanged')])
                result['observations']=dict(prefix_status=status,prefix_response=response['data'],api_continuation_started=False,
                                            ui_continuation_started=False,failed_prefix_api_followup=follow)
                run.update(candidate_id=case['candidate_id'],case_id=case['candidate_id']+'-api-r1',prefix_status=status)
                out=reduce_fixture((result,run,case,fixture))
                self.assertTrue(out['execution_evidence_complete'],out['evidence_issues'])
                self.assertFalse(out['accepted_prefix'])
                self.assertEqual(out['components']['assigned_api_continuation']['status'],'not_reached_prefix_unsuccessful')
                expectation=next(c for c in out['components']['immediate_response']['checks'] if c['id']=='declared_acceptance_expectation')
                self.assertTrue(expectation['passed'])
                self.assertEqual('producer_server_error' in out['components']['immediate_response']['failed_check_ids'],status==500)

    def test_empty_returned_slug_is_not_a_native_continuation(self):
        data=positive(consumer='ui');result,run,case,fixture=data
        response=next(t for t in result['trace'] if t.get('type')=='response' and t.get('method')=='POST' and t.get('path')=='/api/articles')
        response['data']['article']['slug']=''
        result['trace']=result['trace'][:response['sequence']]
        result['observations'].update(prefix_response=response['data'],ui_continuation_started=False,api_continuation_started=False)
        result['prefix_state']['slug']=''
        result['checks']=[check('prefix_fields_match_declared_input')]
        out=reduce_fixture(data)
        self.assertTrue(out['execution_evidence_complete'],out['evidence_issues'])
        self.assertFalse(out['assigned_continuation_reached'])
        self.assertFalse(out['components']['assigned_native_continuation']['mismatch_observed'])
        self.assertIn('returned_reference_empty',out['components']['immediate_response']['failed_check_ids'])

    def test_generated_returned_reference_http_failure_is_assigned(self):
        data=positive(generated=True);result,run,case,fixture=data
        read=next(t for t in result['trace'] if t.get('type')=='response' and t.get('method')=='GET' and t.get('path')=='/api/articles/created')
        read.update(status=404,data={'detail':'synthetic absent reference'})
        result['trace']=result['trace'][:read['sequence']]
        result['trace'].append(dict(sequence=len(result['trace'])+1,type='consumed_dependency',field='article.slug',interface='api',reference='created',status=404))
        result['checks']=[check('producer_fields')]
        out=reduce_fixture(data,True)
        self.assertTrue(out['execution_evidence_complete'],out['evidence_issues'])
        self.assertTrue(out['assigned_continuation_reached'])
        self.assertEqual(out['components']['assigned_api_continuation']['failed_check_ids'],['consumer_read_http_status'])
        self.assertFalse(out['components']['shared_final_native_read']['mismatch_observed'])

    def test_four_workflows_both_continuations(self):
        for workflow in reducer.WORKFLOWS:
            for consumer in ('api','ui'):
                with self.subTest(workflow=workflow,consumer=consumer):
                    out=reduce_fixture(positive(workflow,consumer))
                    self.assertTrue(out['execution_evidence_complete'],out['evidence_issues'])

    def test_generated_checks_are_partitioned(self):
        for consumer in ('api','ui'):
            out=reduce_fixture(positive(consumer=consumer,generated=True),True)
            self.assertTrue(out['execution_evidence_complete'],out['evidence_issues'])
            self.assertEqual(out['components']['shared_post_continuation_api_readback']['assigned_action_interface'],consumer)
            self.assertEqual({c['id'] for c in out['components']['shared_final_native_read']['checks']},{'shared_ui_read','shared_ui_render'})

    def test_final_ui_failure_cannot_be_api_detection(self):
        data=positive(generated=True)
        next(c for c in data[0]['checks'] if c['name']=='shared_ui_render')['passed']=False
        out=reduce_fixture(data,True)
        self.assertTrue(out['execution_evidence_complete'])
        self.assertFalse(out['components']['assigned_api_continuation']['mismatch_observed'])
        self.assertEqual(out['components']['shared_final_native_read']['failed_check_ids'],['shared_ui_render'])

    def test_shared_api_failure_after_ui_is_not_native_only(self):
        data=positive(consumer='ui')
        for event in data[0]['trace']:
            if event['type']=='response' and event['source']=='api' and event['method']=='GET' and event['path']=='/api/articles/created':
                event['data']['article']['body']='unexpected persisted body'
        next(c for c in data[0]['checks'] if c['name']=='persisted_continuation')['passed']=False
        out=reduce_fixture(data)
        self.assertTrue(out['execution_evidence_complete'],out['evidence_issues'])
        self.assertFalse(out['components']['assigned_native_continuation']['mismatch_observed'])
        self.assertEqual(out['components']['shared_post_continuation_api_readback']['failed_check_ids'],['persisted_continuation'])

    def test_late_ui_error_keeps_api_observation_but_no_clean_case(self):
        data=positive(generated=True)
        data[0]['checks']=[c for c in data[0]['checks'] if c['name'] not in {'shared_ui_render','one_article'}]
        data[0].update(status='adapter_error',error={'phase':'oracle','name':'TimeoutError','message':'synthetic timeout'})
        out=reduce_fixture(data,True)
        self.assertFalse(out['execution_evidence_complete'])
        self.assertFalse(out['components']['assigned_api_continuation']['mismatch_observed'])
        self.assertIn('unclassified_adapter_assertion_or_execution_error',out['evidence_issues'])
        self.assertIn('missing_required_check:one_article',out['evidence_issues'])

    def test_phase_and_aggregate_outcome_never_assign_signals(self):
        data=positive(consumer='ui',generated=True)
        before=reduce_fixture(data,True)
        for event in data[0]['trace']:event['phase']='misleading_final_phase'
        data[0]['application_outcome']='fabricated_aggregate_failure'
        self.assertEqual(before,reduce_fixture(data,True))

    def test_unknown_missing_duplicate_and_wrong_route_checks_fail_closed(self):
        for mode in ('unknown','missing','duplicate','wrong_route'):
            with self.subTest(mode=mode):
                data=positive()
                if mode=='unknown':data[0]['checks'].append(check('future_check'))
                if mode=='missing':data[0]['checks'].pop()
                if mode=='duplicate':data[0]['checks'].append(copy.deepcopy(data[0]['checks'][0]))
                if mode=='wrong_route':data[0]['checks'].append(check('native_form_loaded',False))
                out=reduce_fixture(data)
                self.assertFalse(out['execution_evidence_complete'])
                self.assertFalse(out['components']['assigned_api_continuation']['comparison_eligible'])

    def test_generated_check_on_legacy_family_is_unclassified(self):
        data=positive();data[0]['checks'].append(check('shared_ui_read',False))
        out=reduce_fixture(data)
        self.assertFalse(out['execution_evidence_complete'])
        self.assertFalse(out['components']['shared_final_native_read']['mismatch_observed'])
        self.assertEqual(out['unclassified_checks'],[check('shared_ui_read',False)])

    def test_mutated_payload_and_returned_binding_fail_closed(self):
        for mode in ('prefix','consumer','binding','check_boolean','actor'):
            with self.subTest(mode=mode):
                data=positive(generated=True);result=data[0]
                if mode=='binding':result['resource_reference']='wrong'
                elif mode=='check_boolean':result['checks'][0]['passed']=False
                else:
                    event=next(x for x in result['trace'] if (x.get('method'),x.get('type'))==({'prefix':('POST','request'),'consumer':('PUT','request'),'actor':('POST','response')}[mode])
                               and (mode!='prefix' or x.get('path')=='/api/articles'))
                    if mode=='actor':event['data']['user']['email']='different@example.com'
                    else:event['payload']['article']['body']='altered'
                self.assertFalse(reduce_fixture(data,True)['execution_evidence_complete'])

    def test_policy_unknown_does_not_erase_unrelated_failed_check(self):
        data=positive(generated=True);data[2]['expectation']={'category':'unresolved','outcome':'unknown'}
        next(c for c in data[0]['checks'] if c['name']=='shared_ui_render')['passed']=False
        out=reduce_fixture(data,True)
        self.assertTrue(out['policy_unresolved'])
        self.assertTrue(out['components']['shared_final_native_read']['mismatch_observed'])
        self.assertEqual(out['components']['unresolved_policy']['status'],'policy_observations_only')

    def test_deleted_trace_evidence_and_nonzero_exit_are_not_clean(self):
        for mode in ('trace','exit','unfinished'):
            data=positive()
            if mode=='trace':data[0]['trace']=[]
            if mode=='exit':data[1]['exit_code']=1
            if mode=='unfinished':data[0]['execution_status']='runner_or_unadjudicated_error'
            self.assertFalse(reduce_fixture(data)['execution_evidence_complete'])


def attach_capture(result):
    """Add synthetic request-lifetime evidence; never experimental observations."""
    count = 0
    active = {}
    for event in result['trace']:
        if event.get('source') != 'ui':
            continue
        key = (event.get('method'), event.get('path'))
        if event['type'] == 'request':
            count += 1
            active[key] = {'capture_request_id': f'page-1:{count}', 'context_id': 'page-1',
                           'request_phase': 'synthetic'}
            event.update(active[key])
        elif event['type'] == 'response':
            event.update(active.pop(key))
    assert not active
    contexts = []
    if count:
        context = dict(context_id='page-1', admitted=count, completed=count, failures=0,
                       timed_out=False, outstanding=[], complete=True, reason='final_shutdown')
        contexts.append(context)
        result['trace'].append(dict(sequence=len(result['trace']) + 1, type='capture_drain', **context))
    result['capture_integrity'] = dict(version=1, helper_sha256=reducer.CAPTURE_HELPER, complete=True, contexts=contexts)
    return result


class CaptureIntegrityTests(unittest.TestCase):
    def test_current_adapter_and_helper_source_pins(self):
        for name, expected in [('response_capture.mjs', reducer.CAPTURE_HELPER),
                               ('realworld_boundary_case.mjs', reducer.CAPTURE_LEGACY_ADAPTER),
                               ('realworld_generated_case.mjs', reducer.CAPTURE_GENERATED_ADAPTER)]:
            self.assertEqual(reducer.sha((PROJECT/'scripts'/name).read_bytes()), expected)

    def test_matched_request_response_and_drain_accounting(self):
        for consumer in ('api', 'ui'):
            result = attach_capture(positive(consumer=consumer)[0])
            self.assertEqual(reducer.capture_integrity_issues(result, required=True), [])

    def test_missing_capture_is_legacy_optional_but_revised_source_requires_it(self):
        self.assertEqual(reducer.capture_integrity_issues({}), [])
        self.assertIn('missing_capture_integrity', reducer.capture_integrity_issues({}, required=True))

    def test_missing_or_mismatched_response_metadata_is_incomplete(self):
        for mode in ('missing', 'phase', 'duplicate'):
            result = attach_capture(positive(consumer='ui')[0])
            response = next(x for x in result['trace'] if x.get('source') == 'ui' and x['type'] == 'response')
            if mode == 'missing': result['trace'].remove(response)
            elif mode == 'phase': response['request_phase'] = 'other'
            else: result['trace'].append(copy.deepcopy(response))
            self.assertTrue(reducer.capture_integrity_issues(result, required=True), mode)

    def test_failed_timeout_or_tampered_counts_cannot_qualify(self):
        for key, value in [('complete', False), ('failures', 1), ('timed_out', True), ('completed', 999), ('outstanding', [{}])]:
            result = attach_capture(positive(consumer='ui')[0])
            result['capture_integrity']['contexts'][0][key] = value
            self.assertTrue(reducer.capture_integrity_issues(result, required=True), key)

    def test_unknown_helper_and_unclosed_context_are_incomplete(self):
        result = attach_capture(positive(consumer='ui')[0])
        result['capture_integrity']['helper_sha256'] = 'f' * 64
        self.assertIn('unsupported_capture_helper', reducer.capture_integrity_issues(result))
        result['capture_integrity']['contexts'] = []
        self.assertIn('unclosed_capture_context', reducer.capture_integrity_issues(result))


class FileProvenanceTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='realworld-component-test-');self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)
        shutil.copyfile(PROJECT/'scripts/realworld_boundary_case.mjs',self.path/'realworld_boundary_case.mjs')
        shutil.copyfile(PROJECT/'scripts/response_capture.mjs',self.path/'response_capture.mjs')
        shutil.copyfile(PROJECT/'manifests/realworld-boundary-registry-v1.json',self.path/'registered-candidates.json')
        self.summary={'status':'completed','finished_at':'synthetic-unit-fixture','kind':'exploratory_boundary_and_continuation_pilot',
                      'registry_sha256':reducer.sha((self.path/'registered-candidates.json').read_bytes()),
                      'source_sha256':{'realworld_boundary_case.mjs':reducer.sha((self.path/'realworld_boundary_case.mjs').read_bytes()),
                                       'response_capture.mjs':reducer.CAPTURE_HELPER},
                      'candidate_subset':['article-valid'],'repetitions_per_branch':1,'fixture_sha256':'a'*64,'branches':[]}
        for consumer in ('api','ui'):
            result,run,case,fixture=positive(consumer=consumer)
            attach_capture(result)
            run.update(evidence=run['case_id']+'.json',reset_sha256='a'*64)
            (self.path/run['evidence']).write_text(json.dumps(result))
            self.summary['branches'].append(run)
        (self.path/'fixture-references.json').write_text(json.dumps(fixture))
        self.save()

    def save(self):
        (self.path/'summary.json').write_text(json.dumps(self.summary))

    def test_pinned_source_registry_and_relocated_records(self):
        out=reducer.summarize_run(self.path)
        self.assertEqual(out['status'],'complete_observations',out)
        self.assertEqual(out['case_count'],2)

    def test_changed_source_registry_or_missing_branch_is_not_clean(self):
        for mode in ('source','registry','branch','reset'):
            with self.subTest(mode=mode):
                if mode in ('source','registry'):
                    p=self.path/('realworld_boundary_case.mjs' if mode=='source' else 'registered-candidates.json')
                    old=p.read_bytes();p.write_bytes(old+b'\n')
                    self.assertEqual(reducer.summarize_run(self.path)['status'],'incomplete_or_invalid_evidence')
                    p.write_bytes(old)
                else:
                    old=copy.deepcopy(self.summary)
                    if mode=='branch':self.summary['branches'].pop()
                    else:self.summary['branches'][0]['reset_sha256']='b'*64
                    self.save();self.assertEqual(reducer.summarize_run(self.path)['status'],'incomplete_or_invalid_evidence')
                    self.summary=old;self.save()

    def test_case_path_escape_is_rejected(self):
        self.summary['branches'][0]['evidence']='../outside.json';self.save()
        out=reducer.summarize_run(self.path)
        self.assertEqual(out['status'],'incomplete_or_invalid_evidence')
        self.assertTrue(any('unreadable_case_evidence' in x for x in out['run_issues']))

    def test_repaired_source_cannot_qualify_without_its_archived_helper(self):
        (self.path/'response_capture.mjs').unlink()
        out = reducer.summarize_run(self.path)
        self.assertEqual(out['status'], 'incomplete_or_invalid_evidence')
        self.assertIn('missing_executed_source:response_capture.mjs', out['run_issues'])


if __name__=='__main__':
    unittest.main()
