"""Retained mutation outcomes stay source-qualified and separate from primary samples."""
from copy import deepcopy
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from verify_realworld_generated_mutations_archive import verify,read,MANIFEST

class GeneratedArchiveTests(unittest.TestCase):
    def test_live_mutation_attempt_reconstructs(self):
        value=verify();self.assertEqual((value['completed_jobs'],value['branches']),(8,16))
        self.assertEqual(value['status'],'halted_terminal_outcome')
        self.assertEqual([r['terminal_kind'] for r in value['results']],['clean_observation']+['matched_rejection']*3+['clean_observation']*2+['unresolved_policy','missing_evidence'])
        self.assertEqual(value['unstarted_jobs'],[])
        self.assertEqual(value['new_primary_samples'],0)

    def test_changed_raw_hash_rejected(self):
        value=deepcopy(read(MANIFEST));key=next(k for k in value['files_sha256'] if k.endswith('/observation.json'))
        value['files_sha256'][key]='0'*64
        with self.assertRaises(ValueError):verify(value)
