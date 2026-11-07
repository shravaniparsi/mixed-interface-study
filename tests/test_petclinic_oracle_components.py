"""Self-contained synthetic-record tests; no application or raw archive needed."""
from copy import deepcopy
import hashlib
import importlib.util
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('petclinic_components', ROOT/'scripts/summarize_petclinic_oracle_components.py')
mod = importlib.util.module_from_spec(spec); spec.loader.exec_module(mod)
REGISTRY = json.loads((ROOT/'manifests/petclinic-candidates-v1.json').read_text())
CANDIDATES = {c['id']:c for c in REGISTRY['candidates']}
INITIAL = [{'id':i,'firstName':'Seed','lastName':str(i),'address':'Seed','city':'Seed','telephone':'5550100000','pets':[]} for i in range(1,11)]


def record(cid='owner_telephone_10', oracle='api_semantic', code=201, blocked=False):
    c=CANDIDATES[cid];template=c['template'];kind,change=mod.TEMPLATES[template]
    trace=[]
    def event(source,phase,method,path,request,response,status=200):
        trace.append({'source':source,'phase':phase,'method':method,'path':path,'request':deepcopy(request),'response':deepcopy(response),'status':status})
    event('direct_api','reset_verification','GET','/owners',None,INITIAL)
    owner={**REGISTRY['fixtures']['owner'],'id':11,'pets':[]}
    pet={**REGISTRY['fixtures']['pet'],'id':14,'ownerId':11,'visits':[]}
    visit={**REGISTRY['fixtures']['visit'],'id':5,'petId':14}
    graph=deepcopy(INITIAL)
    if template!='owner_address_edit':
        event('direct_api','prefix_setup','POST','/owners',REGISTRY['fixtures']['owner'],owner,201)
        if template=='visit_reschedule':
            event('direct_api','prefix_setup','POST','/owners/11/pets',REGISTRY['fixtures']['pet'],pet,201)
            owner['pets']=[pet]
        graph.append(owner)
    if kind=='owners':target={**deepcopy(c['payload']),'id':11,'pets':[]};prefixpath='/owners'
    elif kind=='pets':target={**deepcopy(c['payload']),'id':14,'ownerId':11,'visits':[]};prefixpath='/owners/11/pets'
    else:target={**deepcopy(c['payload']),'id':5,'petId':14};prefixpath='/owners/11/pets/14/visits'
    response=target if code==201 else {'status':code,'detail':'synthetic rejection'}
    event('direct_api','candidate_prefix','POST',prefixpath,c['payload'],response,code)
    if code==201:
        if kind=='owners':owner=deepcopy(target);graph.append(owner)
        elif kind=='pets':
            pet=deepcopy(target);owner['pets']=[pet];pet['visits']=[visit]
            event('direct_api','prefix_setup','POST','/owners/11/pets/14/visits',REGISTRY['fixtures']['visit'],visit,201)
        else:pet['visits']=[deepcopy(target)]
    event('direct_api','post_prefix_state','GET','/owners',None,graph)
    r={'candidate_id':cid,'template':template,'oracle':oracle,'actor':mod.ACTOR,
       'status':'prefix_rejected' if code!=201 else 'ui_blocked' if blocked else 'continuation_passed',
       'started_at':'2026-11-07T00:00:00Z','finished_at':'2026-11-07T00:00:01Z','backend_pid':101 if oracle=='api_semantic' else 102,
       'backend_start_seconds':.1,'trace':trace,'page_errors':[],'blocked_external_requests':[],
       'prefix_status':code,'prefix_response':deepcopy(response),'continuation_reachable':code==201,
       'initial_state_sha256':mod.digest(INITIAL),'post_prefix_state_sha256':mod.digest(graph),'post_prefix_graph':deepcopy(graph)}
    if code!=201:return r
    before=deepcopy(mod.locate(graph,kind,target['id'])[2]);path='/'+kind+'/'+str(target['id'])
    event('direct_api','continuation_read','GET',path,None,before);r['before']=before
    expected={**deepcopy(before),**change}
    if kind=='owners':payload={'id':target['id'],**{k:expected[k] for k in ('firstName','lastName','address','city','telephone')}}
    elif kind=='pets':payload={'id':target['id'],'name':expected['name'],'birthDate':expected['birthDate'],'type':expected['type']}
    else:payload={'id':target['id'],'pet':deepcopy(pet),'date':expected['date'],'description':expected['description']}
    if oracle=='api_semantic':
        if kind=='visits':event('direct_api','continuation_read','GET','/pets/14',None,pet)
        event('direct_api','continuation_edit','PUT',path,payload,None,204)
    else:
        event('ui_network','continuation','GET','/petclinic/api'+path,None,before)
        if kind in {'pets','visits'}:event('ui_network','continuation','GET','/petclinic/api/owners/11',None,owner)
        if kind=='pets':event('ui_network','continuation','GET','/petclinic/api/pettypes',None,[pet['type']])
        if kind=='visits':event('ui_network','continuation','GET','/petclinic/api/pets/14',None,pet)
        if kind=='owners':fields={k:before[k] for k in ('firstName','lastName','address','city','telephone')}
        elif kind=='pets':fields={'name':before['name'],'birthDate':before['birthDate'].replace('-','/'),'typeId':str(before['type']['id']),'owner_name':owner['firstName']+' '+owner['lastName']}
        else:fields={'date':before['date'].replace('-','/'),'description':before['description']}
        r.update(fresh_ui_read_observed=True,loaded_ui_fields=fields,ui_edit_intended=change,ui_submit_disabled=blocked)
        if not blocked:event('ui_network','continuation','PUT','/petclinic/api'+path,payload,None,204)
    if not blocked:r['continuation_http_status']=204
    after=before if blocked else expected;final_graph=deepcopy(graph)
    if not blocked:mod.locate(final_graph,kind,target['id'])[2].update(change)
    event('direct_api','continuation_readback','GET',path,None,after)
    event('direct_api','relationship_readback','GET','/owners',None,final_graph)
    r.update(after=deepcopy(after),final_graph=final_graph,final_state_sha256=mod.digest(final_graph))
    return r


class ReductionTests(unittest.TestCase):
    def setUp(self):
        p=patch.object(mod,'INITIAL_STATE_SHA256',mod.digest(INITIAL));p.start();self.addCleanup(p.stop)

    def reduce(self,r):return mod.reduce_case(r,CANDIDATES[r['candidate_id']],REGISTRY)

    def test_three_workflows_both_branches_complete(self):
        for cid in ('owner_telephone_10','pet_valid','visit_valid'):
            for oracle in ('api_semantic','fresh_ui'):
                with self.subTest(cid=cid,oracle=oracle):
                    r=record(cid,oracle);o=self.reduce(r)
                    self.assertTrue(o['execution_evidence_complete'],o['evidence_issues'])
                    self.assertFalse(any(c['mismatch_observed'] for c in o['components'].values()))

    def test_shared_readback_failure_not_native_action_failure(self):
        r=record('owner_telephone_10','fresh_ui');r['after']['city']='lost'
        next(t for t in r['trace'] if t['phase']=='continuation_readback')['response']=deepcopy(r['after'])
        o=self.reduce(r)
        self.assertTrue(o['execution_evidence_complete'],o['evidence_issues'])
        self.assertTrue(o['components']['shared_post_continuation_api_readback']['mismatch_observed'])
        self.assertFalse(o['components']['assigned_native_continuation']['mismatch_observed'])

    def test_missing_readback_is_unavailable_not_known_state_mismatch(self):
        r=record();r.pop('after');r['trace']=[t for t in r['trace'] if t['phase']!='continuation_readback']
        o=self.reduce(r);self.assertFalse(o['execution_evidence_complete'])
        self.assertNotIn('final_target_preservation',o['components']['shared_post_continuation_api_readback']['failed_check_ids'])
        self.assertIn('final_target_preservation_missing_input',o['unavailable_evidence'])

    def test_disabled_submit_survives_aggregate_assertion_failure(self):
        r=record('owner_first_name_hyphen','fresh_ui',blocked=True);r.update(status='runner_or_assertion_failure',error='AssertionError: unexplained')
        o=self.reduce(r);self.assertFalse(o['execution_evidence_complete'])
        self.assertIn('native_submit_enabled',o['components']['assigned_native_continuation']['failed_check_ids'])
        self.assertEqual(o['historical_status'],'known_issue_reproduction_not_new_discovery')
        self.assertFalse(o['components']['assigned_native_continuation']['comparison_eligible'])

    def test_known_hyphen_has_native_observation_no_new_defect_claim(self):
        o=self.reduce(record('owner_first_name_hyphen','fresh_ui',blocked=True))
        self.assertTrue(o['execution_evidence_complete'],o['evidence_issues'])
        self.assertEqual(o['components']['assigned_native_continuation']['status'],'check_mismatch_observed')
        self.assertNotIn('defect',o);self.assertIn('not_new_discovery',o['historical_status'])

    def test_whitespace_block_is_policy_only(self):
        for cid in ('owner_city_whitespace','visit_description_whitespace'):
            o=self.reduce(record(cid,'fresh_ui',blocked=True))
            self.assertTrue(o['execution_evidence_complete'],o['evidence_issues'])
            self.assertFalse(o['components']['assigned_native_continuation']['mismatch_observed'])
            self.assertIn('native_submit_enabled',o['components']['unresolved_policy']['failed_check_ids'])
            self.assertFalse(o['components']['unresolved_policy']['comparison_eligible'])

    def test_500_and_422_are_distinct_and_no_downstream_signal(self):
        for code,category in ((500,'server_error'),(422,'client_rejection')):
            o=self.reduce(record('owner_telephone_9',code=code))
            self.assertTrue(o['execution_evidence_complete'],o['evidence_issues'])
            self.assertEqual(o['components']['immediate_response']['observations'][0]['response_class'],category)
            self.assertEqual(o['components']['immediate_response']['mismatch_observed'],code==500)
            self.assertEqual(o['components']['assigned_api_continuation']['status'],'not_reached_prefix_rejected')

    def test_failed_pet_prefix_does_not_invent_precandidate_snapshot(self):
        o=self.reduce(record('pet_omit_name',code=400))
        self.assertTrue(o['execution_evidence_complete'],o['evidence_issues'])
        self.assertTrue(any('pre_candidate_snapshot' in x for x in o['unavailable_evidence']))
        self.assertNotIn('failed_owner_create_graph_unchanged',[c['id'] for c in o['components']['prefix_state_reads']['checks']])

    def test_unknown_check_trace_and_missing_evidence_fail_closed(self):
        for alteration in ('check','phase','trace','actor','hash','pid','finish'):
            with self.subTest(alteration=alteration):
                r=record()
                if alteration=='check':r['checks']=[{'id':'invented','passed':True}]
                elif alteration=='phase':r['trace'][0]['phase']='invented'
                elif alteration=='trace':r['trace']=[]
                elif alteration=='actor':r['actor']='different actor'
                elif alteration=='hash':r['post_prefix_state_sha256']='0'*64
                elif alteration=='pid':r.pop('backend_pid')
                else:r.pop('finished_at')
                o=self.reduce(r);self.assertFalse(o['execution_evidence_complete'])
                self.assertFalse(any(c['comparison_eligible'] for c in o['components'].values()))

    def test_extra_mutation_and_crossroute_action_fail_closed(self):
        for oracle in ('api_semantic','fresh_ui'):
            r=record(oracle=oracle);r['trace'].append({'source':'ui_network','phase':'continuation','method':'DELETE','path':'/petclinic/api/owners/1','status':204,'request':None,'response':None})
            self.assertFalse(self.reduce(r)['execution_evidence_complete'])

    def test_native_pet_date_and_owner_display_audited(self):
        for key,value in [('birthDate','2024/02/10'),('owner_name','Wrong owner')]:
            r=record('pet_valid','fresh_ui');r['loaded_ui_fields'][key]=value;o=self.reduce(r)
            self.assertTrue(o['execution_evidence_complete'],o['evidence_issues'])
            self.assertIn('native_loaded_fields_match_projection',o['components']['assigned_native_continuation']['failed_check_ids'])

    def test_wrong_visit_binding_payload_and_final_graph_not_repaired(self):
        r=record('visit_valid');put=next(t for t in r['trace'] if t['method']=='PUT');put['request']['pet']['id']=99
        o=self.reduce(r);self.assertIn('assigned_payload_matches_bound_intent',o['components']['assigned_api_continuation']['failed_check_ids'])
        self.assertEqual(o['binding_audit']['bound_intended_request']['pet']['id'],14)
        self.assertFalse(o['execution_evidence_complete'])
        self.assertIn('api_payload_differs_from_bound_intent',o['evidence_issues'])
        self.assertFalse(o['components']['assigned_api_continuation']['comparison_eligible'])

    def test_accepted_input_response_predicate_is_immediate_not_persisted_state(self):
        r=record();r['prefix_response']['city']='response-only discrepancy'
        next(t for t in r['trace'] if t['phase']=='candidate_prefix')['response']=deepcopy(r['prefix_response'])
        o=self.reduce(r)
        self.assertIn('accepted_input_values_preserved',o['components']['immediate_response']['failed_check_ids'])
        self.assertNotIn('accepted_input_values_preserved',[c['id'] for c in o['components']['prefix_state_reads']['checks']])

    def test_native_payload_discrepancy_retains_observation_without_api_integrity_issue(self):
        r=record('visit_valid','fresh_ui');put=next(t for t in r['trace'] if t['method']=='PUT');put['request']['pet']['id']=99
        o=self.reduce(r)
        self.assertTrue(o['execution_evidence_complete'],o['evidence_issues'])
        self.assertIn('assigned_payload_matches_bound_intent',o['components']['assigned_native_continuation']['failed_check_ids'])
        self.assertNotIn('api_payload_differs_from_bound_intent',o['evidence_issues'])

    def test_rejected_prefix_stray_native_observation_is_not_downstream_signal(self):
        r=record('owner_telephone_9',code=422);r['ui_submit_disabled']=True;o=self.reduce(r)
        self.assertFalse(o['execution_evidence_complete'])
        self.assertFalse(o['components']['assigned_native_continuation']['mismatch_observed'])

    def test_safe_hash_domain_and_numeric_keys(self):
        self.assertEqual(mod.canonical_bytes({'10':1,'2':2,'a':True}),b'{"2":2,"10":1,"a":true}')
        for value in (float('nan'),1.5,2**53):
            with self.assertRaises(ValueError):mod.digest(value)


class RunIntegrityTests(unittest.TestCase):
    def setUp(self):
        p=patch.object(mod,'INITIAL_STATE_SHA256',mod.digest(INITIAL));p.start();self.addCleanup(p.stop)
        self.temp=tempfile.TemporaryDirectory();self.addCleanup(self.temp.cleanup);self.folder=Path(self.temp.name)
        shutil.copyfile(ROOT/'tests/fixtures/petclinic_boundary_adapter.mjs',self.folder/'executed_boundary_slice.mjs')
        shutil.copyfile(ROOT/'manifests/petclinic-candidates-v1.json',self.folder/'registered-candidates.json')
        self.summary={'subject':'petclinic','kind':'development_boundary_slice','runner_sha256':mod.RUNNER_SHA256,'registry_sha256':mod.REGISTRY_SHA256,
            'jar_sha256':mod.JAR_SHA256,'backend_commit':mod.BACKEND_COMMIT,'frontend_commit':mod.FRONTEND_COMMIT,
            'independent_process_reset_per_branch':True,'source_modified':False,'backend_stopped':True,'finished_at':'2026-11-07T00:00:00Z','branches':[],'pairs':[]}
        for cid in sorted(mod.REPLAY_CASES):
            results=[]
            for oracle in ('api_semantic','fresh_ui'):
                r=record(cid,oracle,blocked=oracle=='fresh_ui');results.append(r);name=f'{cid}-{oracle}.json'
                (self.folder/name).write_text(json.dumps(r));self.summary['branches'].append({k:r[k] for k in ('candidate_id','oracle','status','prefix_status')}|{'result':name})
            self.summary['pairs'].append({'candidate_id':cid,'template':CANDIDATES[cid]['template'],'initial_state_equal':True,'post_prefix_state_equal':True,'final_state_equal':False,'api_status':results[0]['status'],'ui_status':results[1]['status']})
        self.save()
    def save(self): (self.folder/'summary.json').write_text(json.dumps(self.summary))

    def test_source_qualified_replay(self):
        o=mod.summarize_run(self.folder);self.assertEqual(o['status'],'complete_observations',o['run_issues']);self.assertEqual(o['case_count'],6)
        self.assertFalse(o['primary_freeze_complete'])

    def test_changed_source_missing_branch_and_pair_mismatch_fail_closed(self):
        for change in ('source','branch','pair','pid'):
            with self.subTest(change=change):
                if change=='source':
                    p=self.folder/'executed_boundary_slice.mjs';original=p.read_bytes();p.write_bytes(original+b'\n');o=mod.summarize_run(self.folder);p.write_bytes(original)
                elif change=='branch':
                    removed=self.summary['branches'].pop();self.save();o=mod.summarize_run(self.folder);self.summary['branches'].append(removed);self.save()
                elif change=='pair':
                    self.summary['pairs'][0]['post_prefix_state_equal']=False;self.save();o=mod.summarize_run(self.folder);self.summary['pairs'][0]['post_prefix_state_equal']=True;self.save()
                else:
                    p=self.folder/(self.summary['pairs'][0]['candidate_id']+'-fresh_ui.json');r=json.loads(p.read_text());r['backend_pid']=101;p.write_text(json.dumps(r));o=mod.summarize_run(self.folder)
                self.assertEqual(o['status'],'incomplete_or_invalid_evidence')
                self.assertFalse(any(c['execution_evidence_complete'] for c in o['cases']))


if __name__=='__main__':unittest.main()
