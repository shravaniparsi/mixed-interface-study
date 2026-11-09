"""Hash-qualified offline replay of the real halted v8 diagnostic."""
from copy import deepcopy
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from verify_realworld_legacy_halted_archive import verify,read,MANIFEST


class LegacyHaltedArchiveTests(unittest.TestCase):
    def test_actual_halted_run_reconstructs_without_promotion(self):
        value=verify()
        self.assertEqual(value['status'],'halted_terminal_outcome')
        self.assertEqual(value['branches'],8)
        self.assertFalse(value['primary_freeze_complete'])

    def test_changed_file_hash_cannot_pass(self):
        manifest=deepcopy(read(MANIFEST));key=next(iter(manifest['files_sha256']))
        manifest['files_sha256'][key]='0'*64
        with self.assertRaises(ValueError):verify(manifest)
