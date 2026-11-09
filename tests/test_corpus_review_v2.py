import json,unittest
from pathlib import Path
from copy import deepcopy
from mixed_interface.coverage_review_v2 import reconcile
ROOT=Path(__file__).resolve().parents[1]


class CorpusReviewTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        read=lambda p:json.loads((ROOT/p).read_bytes())
        cls.inputs=(read('manifests/retained-corpus-coverage-v1.json')['coverage'],
                    read('manifests/realworld-identity-controls-v1.json'),
                    read('manifests/realworld-paired-database-integration.json'),
                    read('manifests/realworld-identity-halted-integration.json'))
    def review(self):return reconcile(*deepcopy(self.inputs))
    def test_preserves_corpus_branches_references_and_exposure(self):
        value=self.review();base=self.inputs[0]
        self.assertEqual(len(value['rows']),75)
        for old,new in zip(base['rows'],value['rows']):
            for key in ('inventory_entry','branches','reference_control_pair_id','entry_kind'):
                self.assertEqual(old[key],new[key])
            self.assertFalse(new['primary_dispatch_ready'])
    def test_exact_identity_gaps_resolved_without_dispatch_promotion(self):
        value=self.review();rows={r['inventory_entry'].get('candidate_id'):r for r in value['rows']}
        for cid in ('profile-username-null','profile-username-length60','profile-username-length61'):
            self.assertIn('identity_primary_campaign_binding',rows[cid]['remaining_execution_requirements'])
            self.assertIn('realworld_v2_job_dispatch',rows[cid]['resolved_for_observed_path'])
        self.assertIn('identity_semantic_evidence_incomplete',rows['profile-username-length61']['retained_outcome_limits'])
        self.assertIn('identity_requirement_policy_unresolved',rows['profile-username-length60']['retained_outcome_limits'])
    def test_empty_username_does_not_inherit_database_evidence(self):
        row=next(r for r in self.review()['rows'] if r['inventory_entry'].get('candidate_id')=='profile-username-empty')
        self.assertFalse(row['observed_identity_path']['database_capture'])
        self.assertIn('unexpected_acceptance_normalization_and_continuation',row['remaining_execution_requirements'])
    def test_untouched_quartz_boundaries_stay_unexecuted(self):
        rows=[r for r in self.review()['rows'] if r['inventory_entry']['prior_exposure']=='source_inspected_boundary_not_executed']
        self.assertEqual(sum(len(r['branches']) for r in rows),40)
        self.assertTrue(all(not r['recorded_engineering_evidence'] for r in rows))
    def test_changed_payload_does_not_inherit_qualification(self):
        args=deepcopy(self.inputs);args[1]['cases'][1]['prefix_payload']['username']='different'
        with self.assertRaisesRegex(ValueError,'source case differs'):reconcile(*args)
    def test_changed_requirement_or_missing_channel_rejected(self):
        for variant in ('policy','channel'):
            args=deepcopy(self.inputs);m=args[2]['verification']['results'][0]['measurements']
            if variant=='policy':m['api']['requirement_policy']['outcome']='reject'
            else:del m['ui']
            with self.assertRaises(ValueError):reconcile(*args)
    def test_primary_flag_or_missing_row_rejected(self):
        for variant in ('flag','row'):
            args=deepcopy(self.inputs)
            if variant=='flag':args[0]['rows'][0]['primary_dispatch_ready']=True
            else:args[0]['rows'].pop()
            with self.assertRaises(ValueError):reconcile(*args)


if __name__=='__main__':unittest.main()
