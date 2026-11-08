"""Extraction controls and synthetic counterexamples; no applications executed."""
from copy import deepcopy
import hashlib,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import summarize_realworld_paired_components as extension
from mixed_interface.attribution import normalize_case,compare_pair,GATES

class ProspectiveComponentTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory=ROOT/'results/realworld-paired-controls-ci-20261107'
        read=lambda name:json.loads((cls.directory/name).read_bytes())
        cls.summary=read('summary.json');cls.registry=read('registered-candidates.json');cls.fixture=read('fixture-references.json')
        cls.branch=cls.summary['branches'][0];cls.raw=read(cls.branch['evidence']);cls.spec=cls.registry['cases'][0]
        cls.rules=json.loads((ROOT/'manifests/realworld-paired-component-mapping-v1.json').read_bytes())['rules']
    def reduce(self,raw=None):return extension.reduce_case(raw or self.raw,self.branch,self.spec,fixture=self.fixture)
    def test_all_fourteen_controls_are_complete(self):
        for branch in self.summary['branches']:
            raw=json.loads((self.directory/branch['evidence']).read_bytes())
            spec=next(c for c in self.registry['cases'] if c['candidate_id']==branch['candidate_id'])
            self.assertTrue(extension.reduce_case(raw,branch,spec,fixture=self.fixture)['execution_evidence_complete'])
    def test_new_tag_checks_are_immediate_response_observations(self):
        result=self.reduce()
        self.assertTrue(extension.TAG_CHECKS <= {c['id'] for c in result['components']['immediate_response']['checks']})
        self.assertFalse(extension.TAG_CHECKS & {c['id'] for c in result['components']['assigned_api_continuation']['checks']})
    def test_historical_reducer_bytes_unchanged(self):
        self.assertEqual(hashlib.sha256((ROOT/'scripts/summarize_realworld_oracle_components.py').read_bytes()).hexdigest(),extension.HISTORICAL_REDUCER_SHA256)
    def test_unknown_check_fails_closed(self):
        raw=deepcopy(self.raw);raw['checks'].append({'name':'unregistered_check','passed':True})
        self.assertFalse(self.reduce(raw)['execution_evidence_complete'])
    def test_missing_new_tag_check_is_incomplete(self):
        raw=deepcopy(self.raw);raw['checks']=[c for c in raw['checks'] if c['name']!='prefix_tag_membership_matches']
        self.assertFalse(self.reduce(raw)['execution_evidence_complete'])
    def test_forged_tag_verdict_is_recomputed(self):
        raw=deepcopy(self.raw)
        next(c for c in raw['checks'] if c['name']=='prefix_tag_response_representation')['passed']=False
        self.assertIn('check_value_not_supported_by_recorded_state:prefix_tag_response_representation',self.reduce(raw)['evidence_issues'])
    def test_missing_guard_is_incomplete(self):
        raw=deepcopy(self.raw);raw['integrity']['guards']=[]
        self.assertFalse(self.reduce(raw)['execution_evidence_complete'])
    def test_legacy_revision_does_not_acquire_new_qualification(self):
        raw=deepcopy(self.raw);raw['oracle_revision']=2
        self.assertIn('unsupported_oracle_revision',self.reduce(raw)['evidence_issues'])
    def test_reduction_preserves_raw_record(self):
        saved=deepcopy(self.raw);self.reduce();self.assertEqual(saved,self.raw)
    def test_unknown_timing_phase_rejected(self):
        raw=deepcopy(self.raw);raw['timing']['spans'][0]['phase']='unknown'
        with self.assertRaises(ValueError):extension.validate_timing(raw,self.branch)
    def test_phase_reallocation_cannot_hide_behind_unchanged_total(self):
        raw=deepcopy(self.raw);totals=raw['timing']['totals_s'];names=list(totals)
        totals[names[0]]+=.001;totals[names[1]]-=.001
        with self.assertRaises(ValueError):extension.validate_timing(raw,self.branch)
    def test_shared_mismatch_never_becomes_exclusive_detection(self):
        # Synthetic component counterexample, not a claimed application execution.
        a=self.reduce();u=deepcopy(a);u['route']='api-ui'
        u['components']['assigned_native_continuation']=deepcopy(u['components']['assigned_api_continuation'])
        u['components']['assigned_api_continuation']={'checks':[],'observations':[],'status':'not_assigned','comparison_eligible':False}
        for c in u['components']['shared_post_continuation_api_readback']['checks']:
            if c['id']=='persisted_continuation':c['passed']=False
        na=normalize_case(a,'realworld_prospective_controls',self.rules,record_id='synthetic-api')
        nu=normalize_case(u,'realworld_prospective_controls',self.rules,record_id='synthetic-ui')
        pair=compare_pair(na,nu,{k:True for k in GATES},pair_id='synthetic',catalog='synthetic',workflow='article-create-edit')
        self.assertEqual(pair['assigned_signal_overlap'],'neither');self.assertTrue(pair['shared_mismatches'])
    def test_timing_retains_parent_child_hierarchy(self):
        timing=extension.validate_timing(self.raw,self.branch)
        self.assertGreater(timing['branch_total_s'],timing['adapter_timing']['total_s'])
        self.assertIn('not pure diagnostic-component cost',timing['scope'])
