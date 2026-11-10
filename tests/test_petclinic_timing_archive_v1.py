"""Retained timing evidence is verified without promoting pilot counts or performance."""
from copy import deepcopy
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from verify_petclinic_timing_archive_v1 import verify,read,MANIFEST

class PetClinicTimingArchiveTests(unittest.TestCase):
    def test_all_six_pairs_and_twelve_intervals_reconstruct(self):
        v=verify();self.assertEqual((v['pairs'],v['branches']),(6,12))
        self.assertEqual(v['status'],'completed_bounded_diagnostic');self.assertEqual(v['unstarted_slots'],[])
        self.assertEqual([r['terminal_kind'] for r in v['results']],['clean_observation','matched_rejection']*3)
        self.assertTrue(all(t>0 for r in v['results'] for t in r['branch_total_s'].values()))
        self.assertFalse(v['primary_freeze_complete']);self.assertEqual(v['new_primary_samples'],0)

    def test_rejected_prefixes_have_attempt_cost_without_continuation(self):
        root=ROOT/read(MANIFEST)['archive_root']/'petclinic-timing-v1'
        for slot in ('cost-001','cost-003','cost-005'):
            run=root/slot/'run';s=read(run/'summary.json')
            for branch in s['branches']:
                raw=read(run/branch['result']);cost=read(run/branch['cost_record'])
                self.assertFalse(raw['continuation_reachable'])
                self.assertEqual(cost['measurement_status'],'complete_interval')
                self.assertTrue(raw['context_cleanup_confirmed']);self.assertTrue(raw['backend_cleanup']['confirmed'])
                self.assertGreater(cost['branch_total_s'],0)

    def test_changed_cost_sidecar_hash_is_rejected(self):
        m=deepcopy(read(MANIFEST));key=next(k for k in m['files_sha256'] if k.endswith('-cost.json'))
        m['files_sha256'][key]='0'*64
        with self.assertRaises(ValueError):verify(m)
