import copy
import json
from pathlib import Path
import tempfile
import unittest

from mixed_interface.evaluation import generated_pairs, legacy_pairs, file_hashes, verify_snapshot

ROOT = Path(__file__).resolve().parents[1]


class PairRegistrationTests(unittest.TestCase):
    def setUp(self):
        self.pool = json.loads((ROOT / 'manifests/quartz-job-generated-pool-v2.json').read_text())

    def pairs(self, pool):
        return generated_pairs(pool, 'quartz', 'stored_job',
                               {'route_only': 'control', 'payload_mutation': 'unexecuted'})

    def test_existing_registry_pairs_without_inventing_ui_mutations(self):
        pairs = self.pairs(self.pool)
        self.assertEqual(len(pairs), 22)
        mutations = [p for p in pairs if p['intervention'] == 'payload_mutation']
        self.assertEqual(len(mutations), 20)
        self.assertEqual({p['producer_interface'] for p in mutations}, {'api'})
        self.assertTrue(all(set(p['case_ids']) == {'api', 'ui'} for p in pairs))

    def test_different_consumer_intent_cannot_be_paired(self):
        pool = copy.deepcopy(self.pool)
        pool['cases'][0]['operations'][1]['input']['description'] = 'Different intended operation'
        with self.assertRaisesRegex(ValueError, 'Unpaired'):
            self.pairs(pool)

    def test_different_prefix_cannot_be_paired(self):
        pool = copy.deepcopy(self.pool)
        pool['cases'][0]['operations'][0]['input']['description'] = 'Different prefix'
        with self.assertRaisesRegex(ValueError, 'Unpaired'):
            self.pairs(pool)

    def test_different_expectation_scope_cannot_be_paired(self):
        pool = copy.deepcopy(self.pool)
        pool['cases'][0]['expectation_scope'] = {'kind': 'different_operation'}
        with self.assertRaisesRegex(ValueError, 'Unpaired'):
            self.pairs(pool)

    def test_duplicate_candidate_and_missing_counterpart_rejected(self):
        pool = copy.deepcopy(self.pool)
        pool['cases'].append(copy.deepcopy(pool['cases'][0]))
        with self.assertRaisesRegex(ValueError, 'Duplicate'):
            self.pairs(pool)
        pool['cases'] = self.pool['cases'][1:]
        with self.assertRaisesRegex(ValueError, 'Unpaired'):
            self.pairs(pool)

    def test_single_native_controls_stay_outside_paired_denominator(self):
        registry = {'cases': [
            {'candidate_id': 'pair', 'workflow': 'w', 'prefix_interface': 'api', 'continuations': ['api', 'ui']},
            {'candidate_id': 'native-control', 'workflow': 'w', 'prefix_interface': 'ui', 'continuations': ['ui']},
        ]}
        paired, singletons = legacy_pairs(registry, 'development', {'w': 'w'})
        self.assertEqual([r['candidate_id'] for r in paired], ['pair'])
        self.assertEqual([r['candidate_id'] for r in singletons], ['native-control'])

    def test_petclinic_requires_both_declared_oracles(self):
        registry = {'oracles': ['fresh_ui'], 'candidates': []}
        with self.assertRaisesRegex(ValueError, 'explicitly declare'):
            legacy_pairs(registry, 'development', {}, petclinic=True)


class PreparationIntegrityTests(unittest.TestCase):
    def test_changed_file_and_false_freeze_are_rejected(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'oracle.json').write_text('{"scope":"shared"}')
            snapshot = {'artifact_sha256': file_hashes(root, ['oracle.json']),
                        'primary_freeze_complete': False, 'execution_authorized_by_snapshot': False}
            self.assertTrue(verify_snapshot(root, snapshot, ['oracle.json']))
            snapshot['primary_freeze_complete'] = True
            with self.assertRaisesRegex(ValueError, 'completed primary freeze'):
                verify_snapshot(root, snapshot, ['oracle.json'])
            snapshot['primary_freeze_complete'] = False
            (root / 'oracle.json').write_text('{"scope":"api"}')
            with self.assertRaisesRegex(ValueError, 'artifact changed'):
                verify_snapshot(root, snapshot, ['oracle.json'])

    def test_no_execution_authority_or_outside_file(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'input.json').write_text('{}')
            snapshot = {'artifact_sha256': file_hashes(root, ['input.json']),
                        'primary_freeze_complete': False, 'execution_authorized_by_snapshot': True}
            with self.assertRaisesRegex(ValueError, 'cannot authorize'):
                verify_snapshot(root, snapshot, ['input.json'])
            with self.assertRaisesRegex(ValueError, 'inside the study'):
                file_hashes(root, ['../outside.json'])

    def test_deleted_required_hash_entry_cannot_pass(self):
        with tempfile.TemporaryDirectory() as folder:
            root = Path(folder)
            (root / 'corpus.json').write_text('{}')
            snapshot = {'artifact_sha256': file_hashes(root, ['corpus.json']),
                        'primary_freeze_complete': False, 'execution_authorized_by_snapshot': False}
            with self.assertRaisesRegex(ValueError, 'complete required artifact inventory'):
                verify_snapshot(root, snapshot, ['corpus.json', 'oracle.json'])


if __name__ == '__main__':
    unittest.main()
