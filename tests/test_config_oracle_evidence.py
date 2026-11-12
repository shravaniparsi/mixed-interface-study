from pathlib import Path
import sys
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/extension'))
from verify_netbox_config_defaults_v1 import compare_fields


class ConfigurationEvidenceTests(unittest.TestCase):
    def test_missing_is_not_explicit_null(self):
        self.assertTrue(compare_fields({}, {'value': None})['value']['missing'])
        self.assertEqual(compare_fields({'value': None}, {'value': None}), {})

    def test_falsy_types_and_explicit_values_remain_distinct(self):
        self.assertTrue(compare_fields({'value': False}, {'value': 0}))
        self.assertEqual(compare_fields({'bool': False, 'int': 0, 'text': ''}, {'bool': False, 'int': 0, 'text': ''}), {})

    def test_only_declared_fields_contribute(self):
        self.assertEqual(compare_fields({'id': 9, 'value': 'b'}, {'value': 'b'}), {})
        self.assertTrue(compare_fields({'value': 'a'}, {'value': 'b'}))
