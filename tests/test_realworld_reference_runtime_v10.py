"""Live prospective comparator retains literal classifications and partial evidence."""
from copy import deepcopy
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from verify_realworld_reference_runtime_v10 import verify,read,MANIFEST

class ReferenceRuntimeTests(unittest.TestCase):
    def test_live_attempt_reconstructs(self):
        value=verify()
        self.assertEqual((value['completed_jobs'],value['branches']),(7,12))
        self.assertEqual(value['status'],'completed_bounded_diagnostic')
        self.assertEqual([d['kind'] for d in value['decisions']],['clean_observation']*2+['incomparable_observation']*2+['clean_observation']*3)
        self.assertTrue(all(not d['repeat_dispatched'] for d in value['decisions']))
        self.assertFalse(value['primary_freeze_complete'])

    def test_reference_proof_is_retained_with_literal_terminal(self):
        root=ROOT/read(MANIFEST)['archive_root']/'realworld-legacy-v10'
        full=read(root/'legacy-006/observations.json')
        self.assertEqual(full['literal_terminal']['kind'],'incomparable_observation')
        self.assertEqual(full['terminal']['kind'],'clean_observation')
        self.assertTrue(full['reference_comparison']['reference_comparison_qualified'])
        self.assertEqual(full['reference_comparison']['local_bindings'],{'api':True,'ui':True})
        self.assertTrue(all(full['comparability'].values()))
        for jid in ('legacy-004','legacy-005'):
            value=read(root/jid/'observations.json')
            self.assertEqual(value['terminal'],value['literal_terminal'])
            self.assertFalse(value['reference_comparison']['reference_comparison_qualified'])
        for jid in ('legacy-007','legacy-008'):
            value=read(root/jid/'observations.json')
            self.assertNotIn('terminal',value);self.assertFalse(value['paired_comparison_eligible'])

    def test_changed_raw_hash_rejected(self):
        m=deepcopy(read(MANIFEST));key=next(k for k in m['files_sha256'] if k.endswith('-r1.json'))
        m['files_sha256'][key]='0'*64
        with self.assertRaises(ValueError):verify(m)
