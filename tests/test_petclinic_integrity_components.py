import copy,json,sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import summarize_petclinic_integrity_components as pc


class PetClinicComponentExtensionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory=ROOT/'results/petclinic-integrity-ci-20261107'
        cls.registry=pc.load(ROOT/'manifests/petclinic-candidates-v1.json')
        cls.selection=pc.load(ROOT/'manifests/petclinic-integrity-controls-v1.json')['cases']
    def record(self,candidate='visit_valid',oracle='api_semantic'):
        return pc.load(self.directory/'observations'/(candidate+'-'+oracle+'.json'))
    def reduce(self,r):
        return pc.reduce_control(r,next(c for c in self.registry['candidates'] if c['id']==r['candidate_id']),self.registry,next(c for c in self.selection if c['id']==r['candidate_id']))
    def test_all_twelve_archived_controls_qualify(self):
        report=pc.summarize_compact(self.directory);self.assertEqual(report['status'],'complete_observations');self.assertEqual(report['case_count'],12)
    def test_direct_pre_continuation_reads_are_shared_for_both_channels(self):
        for oracle in ('api_semantic','fresh_ui'):
            r=self.reduce(self.record(oracle=oracle));self.assertTrue(r['execution_evidence_complete'])
            shared={c['id'] for c in r['components']['prefix_state_reads']['checks']}
            self.assertTrue({'shared_target_read_200','shared_bound_pet_read_matches_prefix_graph','shared_bound_owner_read_matches_prefix_graph'}<=shared)
            self.assertFalse({'api_target_load_200','api_bound_pet_load'}&{c['id'] for c in r['components']['assigned_api_continuation']['checks']})
    def test_rejected_setup_state_is_observed_not_reported_missing(self):
        r=self.reduce(self.record('visit_omit_date'));self.assertFalse(r['accepted_prefix']);self.assertEqual(r['unavailable_evidence'],[])
        self.assertIn('pre_candidate_graph_unchanged_after_rejection',{c['id'] for c in r['components']['prefix_state_reads']['checks']})
    def test_projection_does_not_mutate_original_evidence(self):
        r=self.record();before=copy.deepcopy(r);self.reduce(r);self.assertEqual(r,before)
    def test_unknown_shared_binding_probe_is_not_silently_dropped(self):
        r=self.record();extra=copy.deepcopy(next(e for e in r['trace'] if e.get('phase')=='binding_read'));extra['path']='/owners/999';r['trace'].append(extra)
        with self.assertRaises(ValueError):pc.project_trace(r)
    def test_missing_native_capture_request_invalidates_extraction(self):
        r=self.record(oracle='fresh_ui');r['trace'].remove(next(e for e in r['trace'] if e['source']=='ui_request'))
        with self.assertRaises(ValueError):self.reduce(r)
    def test_historical_reducer_bytes_are_unchanged(self):
        self.assertEqual(pc.sha(ROOT/'scripts/summarize_petclinic_oracle_components.py'),pc.BASE_REDUCER)
