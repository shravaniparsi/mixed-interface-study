"""Retained v9 replay and branch outcome regression checks."""
from copy import deepcopy
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from verify_realworld_fresh_legacy_archive import verify,read,MANIFEST


class FreshLegacyArchiveTests(unittest.TestCase):
    def test_live_sweep_reconstructs_without_resolving_incomparability(self):
        value=verify();self.assertEqual(value['branches'],12)
        self.assertEqual(sum(d['kind']=='incomparable_observation' for d in value['decisions']),3)

    def test_live_branch_outcomes_and_generated_reference_gate(self):
        root=ROOT/read(MANIFEST)['archive_root']/'realworld-legacy-v9'
        for jid,expected in [('legacy-004','empty_returned_reference'),('legacy-005','returned_reference_not_resolvable'),('legacy-006','passed')]:
            raws=[read(p) for p in (root/jid/'run').glob('*/*-r1.json')]
            self.assertEqual(len(raws),2)
            self.assertEqual({r['observations']['continuation_outcome'] for r in raws},{expected})
            value=read(root/jid/'observations.json')
            self.assertIsNone(value['terminal']['outcome']['channel_discrepancy'])
        full=read(root/'legacy-006/observations.json')
        self.assertFalse(full['comparability']['same_prefix_state'])
        self.assertFalse(full['comparability']['same_consumer_command'])
        self.assertTrue(all(b['kind']=='clean_observation' for b in full['branches'].values()))
        for jid in ('legacy-007','legacy-008'):
            singleton=read(root/jid/'observations.json')
            self.assertFalse(singleton['paired_comparison_eligible'])
            self.assertEqual(singleton['branch']['kind'],'clean_observation')

    def test_changed_trace_hash_fails(self):
        manifest=deepcopy(read(MANIFEST));name=next(n for n in manifest['files_sha256'] if n.endswith('-r1.json'))
        manifest['files_sha256'][name]='0'*64
        with self.assertRaises(ValueError):verify(manifest)
