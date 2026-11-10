"""Retained live controls stay source-qualified and separate from primary samples."""
from copy import deepcopy
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from verify_realworld_generated_runtime_archive import verify,read,MANIFEST

class GeneratedArchiveTests(unittest.TestCase):
    def test_live_reference_pairs_reconstruct(self):
        value=verify();self.assertEqual((value['pairs'],value['branches']),(2,4))
        self.assertTrue(all(r['terminal_kind']=='clean_observation' for r in value['results']))
        self.assertEqual(value['new_primary_samples'],0)

    def test_changed_raw_hash_rejected(self):
        value=deepcopy(read(MANIFEST));key=next(k for k in value['files_sha256'] if k.endswith('/observation.json'))
        value['files_sha256'][key]='0'*64
        with self.assertRaises(ValueError):verify(value)
