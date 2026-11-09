import sys,json,unittest
from pathlib import Path
from copy import deepcopy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from realworld_identity_campaign import plan_for,validate_job
from realworld_identity_bridge_v1 import pair_result
from test_realworld_identity_extract_v1 import synthetic
from mixed_interface.terminal_outcomes import decision


class IdentityCampaignTests(unittest.TestCase):
    def setUp(self):
        self.registry=json.loads((ROOT/'manifests/realworld-identity-controls-v1.json').read_bytes())
        self.plan=plan_for(self.registry)
    def pair(self,status=200,unknown=True):
        branches={}
        for c in ('api','ui'):
            raw,spec,fixture=synthetic(c,status=status,unknown=unknown)
            branches[c]=(raw,{'status':'completed','exit_code':0,'backend_exit_confirmed':True,'reset_sha256':'a'*64,'case_id':c,'evidence':c+'.json'})
        return branches,spec,fixture
    def reduce(self,branches,spec,fixture,cleanup=True):
        return pair_result({'job_id':'initial-000'},branches,spec,fixture,'a'*64,cleanup,{'fixture':'a'*64})['terminal']
    def test_exact_exposed_selection_and_reference_binding(self):
        source=json.loads((ROOT/'manifests/realworld-boundary-registry-v1.json').read_bytes())
        self.assertEqual(len(self.registry['cases']),5)
        for c in self.registry['cases']:self.assertEqual(c,next(x for x in source['cases'] if x['candidate_id']==c['candidate_id']))
        for pair in self.plan['schedule']['pairs']:self.assertEqual(pair['reference_control'],'profile-bio-valid')
    def test_mutated_registry_rejected(self):
        changed=deepcopy(self.registry);changed['cases'][3]['prefix_payload']['username']='changed'
        with self.assertRaises(ValueError):plan_for(changed)
    def test_reordered_job_rejected(self):
        job=deepcopy(self.plan['schedule']['initial_jobs'][0]);job['branches'].reverse()
        with self.assertRaises(ValueError):validate_job(job,self.registry)
    def test_known_accepted_pair_is_clean(self):
        t=self.reduce(*self.pair(unknown=False));self.assertEqual(t['kind'],'clean_observation');self.assertFalse(decision(t)['repeat'])
    def test_unknown_pair_does_not_gain_semantic_completeness(self):
        t=self.reduce(*self.pair());self.assertEqual(t['kind'],'unresolved_policy');self.assertFalse(decision(t)['semantic_evidence_complete']);self.assertFalse(decision(t)['repeat'])
    def test_matched_validation_rejections_are_complete(self):
        t=self.reduce(*self.pair(status=422,unknown=False));self.assertEqual(t['kind'],'matched_rejection')
    def test_server_error_remains_incomplete_and_repeat_eligible(self):
        t=self.reduce(*self.pair(status=500,unknown=False));self.assertEqual(t['kind'],'application_response_failure');self.assertEqual(t['outcome']['execution'],'incomplete');self.assertTrue(decision(t)['repeat'])
    def test_reset_difference_prevents_comparison(self):
        branches,spec,fixture=self.pair();branches['ui'][1]['reset_sha256']='b'*64
        self.assertEqual(self.reduce(branches,spec,fixture)['kind'],'incomparable_observation')
    def test_reused_branch_evidence_prevents_comparison(self):
        branches,spec,fixture=self.pair();branches['ui'][1]['evidence']='api.json'
        self.assertEqual(self.reduce(branches,spec,fixture)['kind'],'incomparable_observation')
    def test_channel_swap_is_missing_evidence(self):
        branches,spec,fixture=self.pair();branches['ui'][0]['continuation_interface']='api'
        self.assertEqual(self.reduce(branches,spec,fixture)['kind'],'missing_evidence')
    def test_cleanup_failure_takes_precedence(self):
        branches,spec,fixture=self.pair();branches['ui'][1]['backend_exit_confirmed']=False
        t=self.reduce(branches,spec,fixture);self.assertEqual(t['kind'],'cleanup_unconfirmed');self.assertEqual(decision(t)['action'],'halt')
    def test_missing_branch_halts(self):
        branches,spec,fixture=self.pair();del branches['ui']
        self.assertEqual(self.reduce(branches,spec,fixture)['kind'],'missing_evidence')
    def test_known_preservation_failure_precedes_unknown_acceptance_policy(self):
        branches,spec,fixture=self.pair();raw=branches['ui'][0]
        next(e for e in raw['trace'] if e['type']=='response' and e.get('path','').startswith('/api/profiles/'))['data']['profile']['bio']='lost'
        next(c for c in raw['checks'] if c['name']=='profile_reference_resolvable')['passed']=False
        raw['observations']['continuation_outcome']='state_mismatch'
        t=self.reduce(branches,spec,fixture);self.assertEqual(t['kind'],'completed_mismatch');self.assertTrue(t['outcome']['channel_discrepancy']);self.assertTrue(t['outcome']['observation_signature']['branches']['ui']['policy_unresolved'])
    def test_archived_registry_loader_uses_identity_filename(self):
        import tempfile
        from validate_realworld_identity_campaign import read_selection
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/'sources/manifests';p.mkdir(parents=True)
            (p/'realworld-identity-controls-v1.json').write_text(json.dumps(self.registry))
            self.assertEqual(read_selection(d),self.registry)
