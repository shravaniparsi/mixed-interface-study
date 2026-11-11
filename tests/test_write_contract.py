import unittest
from mixed_interface.write_contract import check


class WriteContractTests(unittest.TestCase):
    def record(self):
        return {'id': 'synthetic', 'before': {'parent': 'a', 'child': 'old'},
                'after': {'parent': 'b', 'child': None},
                'contract': {'assignments': {'parent': 'b'}, 'derived_assignments': {'child': None}}}

    def test_legitimate_cascade_is_not_preservation_failure(self):
        self.assertFalse(check(self.record())['contract_violation'])

    def test_stale_child_fails_even_without_child_change(self):
        r = self.record(); r['after']['child'] = 'old'
        self.assertEqual(check(r)['derived_assignment_failures'], ['child'])

    def test_missing_child_does_not_satisfy_explicit_null(self):
        r = self.record(); del r['after']['child']
        self.assertEqual(check(r)['derived_assignment_failures'], ['child'])

    def test_unmeasured_view_is_unavailable_not_passing(self):
        r = self.record()
        r['contract']['agreements'] = [{'left': 'readback', 'right': 'invoke', 'fields': ['child']}]
        r['views'] = {'readback': {'child': None}}
        result = check(r)
        self.assertEqual(result['agreements'][0]['status'], 'unavailable')
        self.assertFalse(result['all_declared_observations_available'])

    def test_both_measured_views_omitting_required_key_fail(self):
        r = self.record()
        r['contract']['agreements'] = [{'left': 'readback', 'right': 'invoke', 'fields': ['child']}]
        r['views'] = {'readback': {}, 'invoke': {}}
        self.assertEqual(check(r)['agreements'][0]['status'], 'fail')

    def test_false_and_zero_are_not_interchangeable(self):
        r = self.record(); r['contract']['derived_assignments']['child'] = False
        r['after']['child'] = 0
        self.assertTrue(check(r)['contract_violation'])

    def test_requested_and_derived_assignments_must_be_disjoint(self):
        r = self.record(); r['contract']['derived_assignments']['parent'] = 'b'
        with self.assertRaises(ValueError): check(r)
