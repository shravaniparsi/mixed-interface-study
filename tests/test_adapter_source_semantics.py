"""Semantic controls for the declared fixture, independent of converter behavior."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/extension'))
from build_adapter_input_inventory_v1 import merge_patch, build


class AdapterSourceSemanticsTests(unittest.TestCase):
    def test_nested_removal_preserves_unmentioned_siblings_and_inputs(self):
        target = {'nested': {'erase': 'old', 'keep': 'old'}, 'other': [1, 2]}
        frozen = deepcopy(target)
        self.assertEqual(merge_patch(target, {'nested': {'erase': None, 'flag': False}}),
                         {'nested': {'keep': 'old', 'flag': False}, 'other': [1, 2]})
        self.assertEqual(target, frozen)

    def test_arrays_replace_in_order_and_empty_object_preserves(self):
        self.assertEqual(merge_patch({'items': ['first', 'second']}, {'items': ['second', 'first']}), {'items': ['second', 'first']})
        self.assertEqual(merge_patch({'items': ['first']}, {'items': []}), {'items': []})
        self.assertEqual(merge_patch({'nested': {'keep': 0}}, {'nested': {}}), {'nested': {'keep': 0}})

    def test_create_null_and_patch_null_have_distinct_declared_meanings(self):
        _, inventory = build()
        cases = {r['id']: r for r in inventory['cases']}
        created = cases['create_record:label-null']['expected_records']['created']
        patched = cases['patch_record:label-null']['expected_records']['seed']
        self.assertIn('label', created)
        self.assertIsNone(created['label'])
        self.assertNotIn('label', patched)
        self.assertEqual(cases['patch_record:empty']['initial_records'], cases['patch_record:empty']['expected_records'])
