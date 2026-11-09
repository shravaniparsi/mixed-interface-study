"""Historical control replay plus synthetic counterexamples; no new applications."""
from copy import deepcopy
from pathlib import Path
import json,sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import petclinic_terminal_outcomes as bridge


class PetClinicTerminalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory=ROOT/'results/petclinic-integrity-ci-20261107'
        cls.registry=bridge.load(ROOT/'manifests/petclinic-candidates-v1.json')
        cls.selection=bridge.load(ROOT/'manifests/petclinic-integrity-controls-v1.json')['cases']

    def record(self,cid='owner_telephone_10',oracle='fresh_ui'):
        return bridge.load(self.directory/'observations'/(cid+'-'+oracle+'.json'))

    def classify(self,raw,cleanup=True):
        spec=next(c for c in self.registry['candidates'] if c['id']==raw['candidate_id'])
        expected=next(c for c in self.selection if c['id']==raw['candidate_id'])
        return bridge.classify_branch(raw,spec,self.registry,expected,cleanup_confirmed=cleanup)

    def pair(self,a,u,cleanup=True):
        spec=next(c for c in self.registry['candidates'] if c['id']==a['candidate_id'])
        expected=next(c for c in self.selection if c['id']==a['candidate_id'])
        return bridge.pair_terminal('synthetic',{'api':a,'ui':u},spec,self.registry,expected,cleanup_confirmed=cleanup,evidence={'synthetic':'a'*64})

    def blocked(self,cid="owner_telephone_10"):
        raw=self.record(cid);raw.update(status='ui_blocked',ui_submit_disabled=True)
        raw.pop('continuation_http_status')
        raw['trace']=[e for e in raw['trace'] if e.get('method')!='PUT']
        raw['integrity']['guards']=[g for g in raw['integrity']['guards'] if g['name']!='continuation_edit_command']
        for context in raw['capture_integrity']['contexts']:
            context['admitted']-=1;context['completed']-=1
        raw['after']=deepcopy(raw['before']);raw['final_graph']=deepcopy(raw['post_prefix_graph'])
        raw['final_state_sha256']=bridge.digest(raw['final_graph'])
        for e in raw['trace']:
            if e.get('phase')=='continuation_readback':e['response']=deepcopy(raw['after'])
            if e.get('phase')=='relationship_readback':e['response']=deepcopy(raw['final_graph'])
        return raw

    def changed_rejection(self,oracle):
        raw=self.record('owner_omit_firstName',oracle)
        raw['post_prefix_graph'][0]['address']='Synthetic unexpected address'
        raw['post_prefix_state_sha256']=bridge.digest(raw['post_prefix_graph'])
        raw['integrity']['rejection']['status']='changed'
        raw['integrity']['rejection']['after']['data']=deepcopy(raw['post_prefix_graph'])
        for e in raw['trace']:
            if e.get('phase')=='post_prefix_state':e['response']=deepcopy(raw['post_prefix_graph'])
        return raw

    def test_all_twelve_archived_controls(self):
        for case in self.selection:
            for oracle in ('api_semantic','fresh_ui'):
                with self.subTest(case=case['id'],oracle=oracle):
                    result=self.classify(self.record(case['id'],oracle))
                    self.assertEqual(result['kind'],'clean_observation' if case['prefix_status']==201 else 'matched_rejection',result)

    def test_full_source_qualified_archive_replay(self):
        result=bridge.replay_archive(self.directory)
        self.assertEqual(result['pair_count'],6)
        self.assertEqual(result['application_executions_added'],0)
        self.assertFalse(result['per_job_dispatch_qualified'])

    def test_native_block_is_completed_mismatch(self):
        for cid in ('owner_telephone_10','pet_valid','visit_valid'):
            with self.subTest(candidate=cid):
                result=self.classify(self.blocked(cid))
                self.assertEqual(result['kind'],'completed_mismatch',result)
                self.assertTrue(result['components']['execution_evidence_complete'])
                self.assertTrue(result['components']['components']['assigned_native_continuation']['mismatch_observed'])

    def test_blocked_native_pair_keeps_exclusive_signal(self):
        result=self.pair(self.record(oracle='api_semantic'),self.blocked())
        self.assertEqual(result['terminal']['kind'],'completed_mismatch',result)
        self.assertTrue(result['terminal']['outcome']['channel_discrepancy'])

    def test_graph_change_after_rejection_is_not_an_execution_failure(self):
        result=self.classify(self.changed_rejection('api_semantic'))
        self.assertEqual(result['kind'],'completed_mismatch',result)
        self.assertFalse(result['components']['accepted_prefix'])

    def test_shared_rejection_change_has_no_exclusive_signal(self):
        result=self.pair(self.changed_rejection('api_semantic'),self.changed_rejection('fresh_ui'))
        self.assertEqual(result['terminal']['kind'],'completed_mismatch')
        self.assertFalse(result['terminal']['outcome']['channel_discrepancy'])

    def test_unreadable_rejected_state_halts(self):
        raw=self.record('owner_omit_firstName');raw['integrity']['rejection']['after']['readable']=False
        self.assertEqual(self.classify(raw)['kind'],'missing_evidence')

    def test_forged_rejected_state_verdict_halts(self):
        raw=self.changed_rejection('fresh_ui');raw['integrity']['rejection']['status']='unchanged'
        self.assertEqual(self.classify(raw)['kind'],'missing_evidence')

    def test_fake_block_with_put_is_incomplete(self):
        raw=self.record();raw.update(status='ui_blocked',ui_submit_disabled=True);raw.pop('continuation_http_status')
        self.assertEqual(self.classify(raw)['kind'],'missing_evidence')

    def test_wrong_blocked_intent_is_incomplete(self):
        raw=self.blocked();raw['ui_edit_intended']={'address':'Different action'}
        self.assertEqual(self.classify(raw)['kind'],'missing_evidence')

    def test_missing_native_capture_invalidates_observation(self):
        raw=self.record();raw['trace'].remove(next(e for e in raw['trace'] if e['source']=='ui_request'))
        self.assertEqual(self.classify(raw)['kind'],'missing_evidence')

    def test_cleanup_precedes_error(self):
        raw=self.record();raw['error']='synthetic error'
        self.assertEqual(self.classify(raw,False)['kind'],'cleanup_unconfirmed')

    def test_unknown_assertion_is_not_a_completed_mismatch(self):
        raw=self.record();raw.update(status='runner_or_assertion_failure',error='AssertionError')
        self.assertEqual(self.classify(raw)['kind'],'environment_failure')

    def test_changed_helper_hash_is_not_admitted(self):
        raw=self.record();raw['integrity']['helper_sha256']='0'*64
        self.assertEqual(self.classify(raw)['kind'],'missing_evidence')

    def test_backend_reuse_prevents_pair_comparison(self):
        a=self.record(oracle='api_semantic');u=self.record();u['backend_pid']=a['backend_pid'];u['backend_cleanup']['pid']=a['backend_pid']
        self.assertEqual(self.pair(a,u)['terminal']['kind'],'incomparable_observation')

    def test_reduction_preserves_raw_evidence(self):
        raw=self.blocked();before=deepcopy(raw);self.classify(raw);self.assertEqual(raw,before)

    def test_blocked_label_cannot_hide_changed_relationship_graph(self):
        raw=self.blocked();raw['final_graph'][0]['address']='Synthetic change'
        raw['final_state_sha256']=bridge.digest(raw['final_graph'])
        for event in raw['trace']:
            if event.get('phase')=='relationship_readback':event['response']=deepcopy(raw['final_graph'])
        self.assertEqual(self.classify(raw)['kind'],'missing_evidence')
