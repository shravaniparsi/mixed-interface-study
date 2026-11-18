import unittest
from mixed_interface.write_observations import measure as legacy
from mixed_interface.write_observations_v2 import measure


def obs(value):
    return {'state': 'observed', 'projection': {'value': value}}


def run(fn, before, after, restored, intended):
    return fn(200, obs(before), obs(after), obs(restored), {'value': intended},
              {'record': {'state': 'response', 'status': 200}})


class TypedPersistenceTests(unittest.TestCase):
    def test_bool_number_changes_are_visible_in_all_three_measurements(self):
        for old, new in [(False, 0), (True, 1), ([False], [0]),
                         ({'nested': True}, {'nested': 1})]:
            for before, after in [(old, new), (new, old)]:
                with self.subTest(before=before, after=after):
                    v1 = run(legacy, before, after, before, before)['persistence']
                    self.assertEqual(v1['selected_change'], 'unchanged')
                    self.assertTrue(v1['intended_values_observed'])
                    self.assertTrue(v1['immediate_projection_survives_restart'])
                    v2 = run(measure, before, after, before, before)['persistence']
                    self.assertEqual(v2['selected_change'], 'other_change')
                    self.assertFalse(v2['intended_values_observed'])
                    self.assertFalse(v2['immediate_projection_survives_restart'])

    def test_intended_type_changing_assignment_is_recognized(self):
        r = run(measure, False, 0, 0, 0)
        self.assertEqual(r['schema_version'], 2)
        self.assertEqual(r['persistence']['selected_change'], 'requested_patch_observed')
        self.assertTrue(r['persistence']['intended_values_observed'])
        self.assertTrue(r['persistence']['immediate_projection_survives_restart'])
        self.assertEqual(r['continuation']['state'], 'not_measured')

    def test_missing_observations_remain_unknown(self):
        r = measure(None, obs(False), {'state': 'missing'}, {'state': 'not_planned'},
                    {'value': 0}, {'record': {'state': 'missing'}})['persistence']
        self.assertEqual(r['selected_change'], 'unknown')
        self.assertIsNone(r['intended_values_observed'])
        self.assertIsNone(r['immediate_projection_survives_restart'])

    def test_ordinary_string_write_agrees_except_version(self):
        a = run(legacy, 'old', 'new', 'new', 'new')
        b = run(measure, 'old', 'new', 'new', 'new')
        a['schema_version'] = 2
        self.assertEqual(a, b)

    def test_unsupported_nonfinite_json_is_rejected(self):
        with self.assertRaises(ValueError):
            run(measure, 0, float('nan'), 0, 0)
