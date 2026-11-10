"""Retained application evidence must reconstruct, including common provenance."""
from copy import deepcopy
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from verify_common_generated_archive_v1 import verify,MANIFEST
from petclinic_timed_jobs_v4 import read

class CommonArchiveTests(unittest.TestCase):
    def test_raw_archive_reconstructs_two_exposed_pairs(self):
        v=verify();self.assertEqual((v['pairs'],v['branches']),(2,4))
        self.assertEqual([r['terminal_kind'] for r in v['results']],['clean_observation','clean_observation'])
        self.assertEqual(len({r['attempt_id'] for r in v['results']}),2)
        self.assertEqual(v['new_primary_samples'],0);self.assertFalse(v['primary_freeze_complete'])
    def test_manifest_scope_inventory_and_results_cannot_change(self):
        original=read(MANIFEST)
        for mode in ('scope','inventory','result','run'):
            with self.subTest(mode=mode):
                value=deepcopy(original)
                if mode=='scope':value['primary_freeze_complete']=True
                elif mode=='inventory':value['files_sha256'].pop(next(iter(value['files_sha256'])))
                elif mode=='result':value['verification']['results'][1]['terminal_kind']='matched_rejection'
                else:value['application_run']=1
                with self.assertRaises(ValueError):verify(value)
