"""Synthetic response counterexamples, plus replay of actual qualified controls."""
from copy import deepcopy
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import petclinic_prefix_outcomes_v3 as bridge
import test_petclinic_terminal_outcomes as fixtures
from mixed_interface.campaign_v2 import drive
from mixed_interface.terminal_outcomes import terminal
from petclinic_terminal_campaign import contract

class PetClinicPrefixTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.PetClinicTerminalTests.setUpClass();cls.fixture=fixtures.PetClinicTerminalTests()
        cls.registry=bridge.load(ROOT/'manifests/petclinic-candidates-v1.json')
    def spec(self,cid):return next(c for c in self.registry['candidates'] if c['id']==cid)
    def classify(self,raw,cleanup=True):return bridge.classify_branch(raw,self.spec(raw['candidate_id']),self.registry,cleanup_confirmed=cleanup)
    def pair(self,a,u):return bridge.pair_terminal('fixture',{'api':a,'ui':u},self.spec(a['candidate_id']),self.registry,cleanup_confirmed=True,evidence={'synthetic':'b'*64})
    def remap(self,raw,cid):
        spec=self.spec(cid);raw['candidate_id']=cid
        e=next(e for e in raw['trace'] if e.get('phase')=='candidate_prefix');e['request']=deepcopy(spec['payload'])
        for g in raw['integrity']['guards']:
            if g['name']=='candidate_prefix_command':
                g['expected']['payload']=deepcopy(spec['payload']);g['observed']['payload']=deepcopy(spec['payload'])
        return raw
    def rejected(self,cid,code=400,oracle='fresh_ui'):
        original={'owner_address_edit':'owner_omit_firstName','pet_rename':'pet_omit_name','visit_reschedule':'visit_omit_date'}[self.spec(cid)['template']]
        raw=self.remap(self.fixture.record(original,oracle),cid);raw['prefix_status']=code
        raw['status']='prefix_server_error' if code>=500 else 'prefix_rejected'
        next(e for e in raw['trace'] if e.get('phase')=='candidate_prefix')['status']=code
        return raw
    def test_six_actual_control_pairs_keep_outcomes(self):
        for case in self.fixture.selection:
            a=self.fixture.record(case['id'],'api_semantic');u=self.fixture.record(case['id'],'fresh_ui')
            result=self.pair(a,u)
            self.assertEqual(result['terminal']['kind'],'clean_observation' if case['prefix_status']==201 else 'matched_rejection',result)
    def test_all_eighteen_registered_policies_have_explicit_rejection_behavior(self):
        for c in self.registry['candidates']:
            _,policy=bridge.policy_for(c,self.registry)
            expected={'accept':'completed_mismatch','reject':'matched_rejection','unresolved':'unresolved_policy'}[policy['prefix_requirement']]
            with self.subTest(candidate=c['id']):self.assertEqual(self.classify(self.rejected(c['id']))['kind'],expected)
    def test_unexpected_acceptance_requires_full_continuation_evidence(self):
        raw=self.remap(self.fixture.record(),'owner_omit_firstName')
        self.assertEqual(self.classify(raw)['kind'],'completed_mismatch')
        del raw['after']
        self.assertEqual(self.classify(raw)['kind'],'missing_evidence')
    def test_unexpected_validation_rejection_is_shared_mismatch(self):
        result=self.pair(self.rejected('owner_telephone_10',oracle='api_semantic'),self.rejected('owner_telephone_10'))
        self.assertEqual(result['terminal']['kind'],'completed_mismatch');self.assertFalse(result['terminal']['outcome']['channel_discrepancy'])
        self.assertTrue(result['terminal']['outcome']['check_failure'])
    def test_changed_rejection_status_is_not_missing_evidence(self):
        self.assertEqual(self.classify(self.rejected('owner_omit_firstName',422))['kind'],'matched_rejection')
    def test_server_auth_rate_limit_and_unsupported_success_are_not_matched_rejections(self):
        for code in (200,202,204,301,401,403,404,409,429,500,503):
            with self.subTest(code=code):self.assertEqual(self.classify(self.rejected('owner_omit_firstName',code))['kind'],'application_response_failure')
    def test_server_failure_pair_is_incomplete_and_repeat_eligible(self):
        result=self.pair(self.rejected('owner_omit_firstName',500,'api_semantic'),self.rejected('owner_omit_firstName',500))
        self.assertEqual(result['terminal']['kind'],'application_response_failure');self.assertEqual(result['terminal']['outcome']['execution'],'incomplete')
        from mixed_interface.terminal_outcomes import decision
        self.assertTrue(decision(result['terminal'])['repeat']);self.assertFalse(decision(result['terminal'])['semantic_evidence_complete'])
    def test_unreadable_state_after_server_error_halts(self):
        raw=self.rejected('owner_omit_firstName',500);raw['integrity']['rejection']['after']['readable']=False
        self.assertEqual(self.classify(raw)['kind'],'missing_evidence')
    def test_http_response_trace_disagreement_halts(self):
        raw=self.rejected('owner_omit_firstName',500);next(e for e in raw['trace'] if e.get('phase')=='candidate_prefix')['status']=400
        self.assertEqual(self.classify(raw)['kind'],'missing_evidence')
    def test_status_tag_disagreement_halts(self):
        raw=self.rejected('owner_omit_firstName',500);raw['status']='prefix_rejected'
        self.assertEqual(self.classify(raw)['kind'],'missing_evidence')
    def test_invalid_status_type_and_range_halt(self):
        for code in (True,0,600,'400',None):
            raw=self.rejected('owner_omit_firstName');raw['prefix_status']=code
            self.assertEqual(self.classify(raw)['kind'],'missing_evidence')
    def test_no_write_allowed_after_non201_response(self):
        raw=self.rejected('owner_omit_firstName',500);raw['trace'].append({'method':'PUT'})
        self.assertEqual(self.classify(raw)['kind'],'missing_evidence')
    def test_cleanup_precedes_response_and_runner_error(self):
        raw=self.rejected('owner_omit_firstName',500);raw['error']='synthetic'
        self.assertEqual(self.classify(raw,False)['kind'],'cleanup_unconfirmed')
        self.assertEqual(self.classify(raw)['kind'],'environment_failure')
    def test_registry_substitution_halts(self):
        raw=self.fixture.record();registry=deepcopy(self.registry);registry['fixtures']['owner']['city']='changed'
        self.assertEqual(bridge.classify_branch(raw,self.spec(raw['candidate_id']),registry,cleanup_confirmed=True)['kind'],'missing_evidence')
    def test_mixed_prefix_outcomes_are_incomparable(self):
        result=self.pair(self.fixture.record(oracle='api_semantic'),self.rejected('owner_telephone_10'))
        self.assertEqual(result['terminal']['kind'],'incomparable_observation')
    def test_raw_server_failure_evidence_unchanged(self):
        raw=self.rejected('owner_omit_firstName',500);before=deepcopy(raw);self.classify(raw);self.assertEqual(raw,before)
    def test_partial_response_repeats_cannot_be_stable_semantic_evidence(self):
        plan=contract()['plan'];seen=[]
        def execute(job):
            cid=job['pair_id'];failure=cid=='owner_omit_firstName'
            a=self.rejected(cid,500,'api_semantic') if failure else self.fixture.record(cid,'api_semantic')
            u=self.rejected(cid,500) if failure else self.fixture.record(cid,'fresh_ui')
            result=self.pair(a,u)['terminal'];result['outcome']['job_id']=job['job_id'];seen.append(job)
            return result
        state=drive(plan,execute,lambda _:None)
        self.assertEqual(len(state['repeated']),4);self.assertEqual(state['repeat_summary']['pairs'][0]['status'],'unresolved_execution')
        self.assertEqual([j['pair_id'] for j in seen[6:]],['owner_omit_firstName','owner_telephone_10']*2)
    def accepted_variation(self,cid,oracle,blocked=False):
        base,old,new={'owner_first_name_hyphen':('owner_telephone_10','Alice','Anne-Marie'),'owner_city_whitespace':('owner_telephone_10','Testville',' '),'visit_description_whitespace':('visit_valid','Pilot routine check',' ')}[cid]
        raw=self.fixture.blocked(base) if blocked else self.fixture.record(base,oracle)
        raw=self.remap(raw,cid)
        def replace(v):
            if isinstance(v,dict):return {k:replace(x) for k,x in v.items()}
            if isinstance(v,list):return [replace(x) for x in v]
            return new if v==old else v
        raw=replace(raw)
        raw['post_prefix_state_sha256']=bridge.v2.digest(raw['post_prefix_graph'])
        raw['final_state_sha256']=bridge.v2.digest(raw['final_graph'])
        return raw
    def test_hyphenated_name_keeps_native_specific_signal(self):
        a=self.accepted_variation('owner_first_name_hyphen','api_semantic');u=self.accepted_variation('owner_first_name_hyphen','fresh_ui',True)
        result=self.pair(a,u)
        self.assertEqual(result['terminal']['kind'],'completed_mismatch',result)
        self.assertTrue(result['terminal']['outcome']['channel_discrepancy'])
    def test_whitespace_blocks_remain_unresolved_policy(self):
        for cid in ('owner_city_whitespace','visit_description_whitespace'):
            a=self.accepted_variation(cid,'api_semantic');u=self.accepted_variation(cid,'fresh_ui',True)
            result=self.pair(a,u)
            self.assertEqual(result['terminal']['kind'],'unresolved_policy',result)
            self.assertFalse(result['terminal']['outcome']['channel_discrepancy'])
