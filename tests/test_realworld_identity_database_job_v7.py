import json,sys,unittest
from pathlib import Path
from copy import deepcopy
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import test_identity_database_capture_v2 as fixtures
from realworld_identity_database_job_v7 import bound_measurement
from realworld_identity_extract_v1 import extract
from realworld_paired_database_plan_v7 import jobs,IDS


class DatabaseJobBindingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        fixtures.DatabaseCaptureIntegrationTests.setUpClass()
        cls.cases=fixtures.DatabaseCaptureIntegrationTests.cases
    @classmethod
    def tearDownClass(cls): fixtures.DatabaseCaptureIntegrationTests.tearDownClass()
    def observed(self,status):
        raw,directory,fixture,spec=self.cases[status]
        return bound_measurement(raw,directory,spec,fixture,extract(raw,spec,fixture))
    def test_committed_error_is_attached_to_same_branch(self):
        result=self.observed(500)
        self.assertEqual(result['measurement']['http']['status'],500)
        self.assertEqual(result['measurement']['persistence']['selected_change'],'requested_patch_observed')
        self.assertEqual(result['continuation_database']['state'],'not_executed')
        self.assertEqual(result['requirement_policy']['outcome'],'unknown')
        self.assertFalse(result['restart_observed'])
    def test_rejection_is_compared_using_actual_database(self):
        result=self.observed(422)
        self.assertEqual(result['measurement']['persistence']['selected_change'],'unchanged')
        self.assertEqual(len(result['snapshot_sha256']),2)
    def test_continuation_snapshot_is_separate_from_producer_snapshot(self):
        result=self.observed(200)
        self.assertEqual(result['measurement']['persistence']['immediate']['projection']['bio'],'old')
        self.assertEqual(result['continuation_database']['projection']['bio'],'Bio after meaningful continuation.')
        self.assertEqual(len(result['snapshot_sha256']),3)
    def test_wrong_branch_capture_directory_rejected(self):
        raw,_,fixture,spec=self.cases[500]
        with self.assertRaises(ValueError):
            bound_measurement(raw,self.cases[422][1],spec,fixture,extract(raw,spec,fixture))
    def test_trace_tampering_cannot_be_repaired_by_valid_database(self):
        original,directory,fixture,spec=self.cases[500];raw=deepcopy(original)
        raw['observations']['prefix_status']=422
        with self.assertRaises(ValueError):bound_measurement(raw,directory,spec,fixture,extract(raw,spec,fixture))
    def test_selection_is_exact_and_exposed(self):
        registry=json.loads((ROOT/'manifests/realworld-identity-controls-v1.json').read_bytes())
        self.assertEqual(tuple(j['pair_id'] for j in jobs(registry)),IDS)
        registry['cases'][0]['prefix_payload']['bio']='changed'
        with self.assertRaises(ValueError):jobs(registry)


if __name__=='__main__':unittest.main()
