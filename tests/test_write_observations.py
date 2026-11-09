import unittest
from mixed_interface.write_observations import measure


def observed(value):
    return {'state': 'observed', 'projection': {'username': value, 'id': 1}}


class WriteObservationTests(unittest.TestCase):
    def call(self, status=500, immediate=None, restart=None, readbacks=None):
        return measure(status, observed('old'), immediate or observed('new'),
                       restart or observed('new'), {'username': 'new'},
                       readbacks or {'user': {'state': 'response', 'status': 500}})

    def test_failed_response_can_commit(self):
        result = self.call()
        self.assertEqual(result['persistence']['selected_change'], 'requested_patch_observed')
        self.assertTrue(result['persistence']['immediate_projection_survives_restart'])
        self.assertEqual(result['continuation']['state'], 'not_measured')

    def test_success_does_not_imply_change(self):
        self.assertEqual(self.call(200, observed('old'))['persistence']['selected_change'], 'unchanged')

    def test_unavailable_snapshot_never_means_unchanged(self):
        for state in ('missing', 'unreadable', 'not_planned'):
            result = self.call(immediate={'state': state})['persistence']
            self.assertEqual(result['selected_change'], 'unknown')
            self.assertIsNone(result['intended_values_observed'])
            self.assertIsNone(result['immediate_projection_survives_restart'])

    def test_extra_change_is_retained(self):
        value = observed('new'); value['projection']['id'] = 2
        result = self.call(immediate=value)['persistence']
        self.assertEqual(result['selected_change'], 'other_change')
        self.assertTrue(result['intended_values_observed'])
        self.assertFalse(result['immediate_projection_survives_restart'])

    def test_noop_intended_value_is_not_a_mutation(self):
        result = measure(200, observed("new"), observed("new"), {"state": "not_planned"},
                         {"username": "new"}, {"user": {"state": "not_planned"}})
        self.assertEqual(result["persistence"]["selected_change"], "unchanged")
        self.assertTrue(result["persistence"]["intended_values_observed"])
        self.assertIsNone(result["persistence"]["immediate_projection_survives_restart"])

    def test_missing_response_is_not_rejection(self):
        self.assertEqual(self.call(None)['http'], {'state': 'missing', 'status': None})

    def test_partial_readback_and_no_continuation_inference(self):
        reads = {'user': {'state': 'response', 'status': 200}, 'article': {'state': 'missing'}}
        result = self.call(readbacks=reads)
        self.assertEqual(result['readbacks'], reads)
        self.assertEqual(result['continuation']['state'], 'not_measured')
        reads['user']['status'] = 500
        self.assertEqual(result['readbacks']['user']['status'], 200)

    def test_incompatible_projection_rejected(self):
        value = observed('new'); del value['projection']['id']
        with self.assertRaisesRegex(ValueError, 'scope differs'):
            self.call(immediate=value)

    def test_invalid_status_and_invented_snapshot_rejected(self):
        for status in (True, 600, '500'):
            with self.assertRaises(ValueError): self.call(status)
        with self.assertRaises(ValueError):
            self.call(immediate={'state': 'unreadable', 'projection': {'username': 'new'}})


if __name__ == '__main__': unittest.main()
