import sys
import unittest
from copy import deepcopy
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from test_realworld_identity_extract_v1 import synthetic
from realworld_identity_extract_v1 import extract as legacy_extract
from realworld_identity_measurements_v2 import extract


def failed_reads():
    raw, spec, fixture = synthetic(status=500)
    record = raw['identity']['after']
    record['readable'] = False
    record.pop('data')
    record['error'] = 'Unreadable snapshot'
    for read in record['reads']:
        if read['path'] == '/api/user' or (read['path'].startswith('/api/articles/') and not read['path'].endswith('/comments')):
            read['status'] = 500; read['data'] = {'raw': 'Internal Server Error'}
            event = raw['trace'][read['response_sequence'] - 1]
            event.update(status=500, data=deepcopy(read['data']))
    return raw, spec, fixture


class IdentityMeasurementTests(unittest.TestCase):
    def measured(self, values):
        return extract(*values, legacy_extract(*values))

    def test_api_and_ui_completed_continuations_remain_separate(self):
        for channel in ('api', 'ui'):
            result = self.measured(synthetic(channel))
            self.assertTrue(result['qualified'], result)
            self.assertEqual(result['measurement']['continuation']['interface'], channel)
            self.assertEqual(result['measurement']['continuation']['state'], 'observed')
            self.assertEqual(result['requirement_policy']['outcome'], 'unknown')
            self.assertEqual(result['measurement']['persistence']['selected_change'], 'unknown')

    def test_failed_readbacks_are_observed_without_repairing_original_halt(self):
        values = failed_reads(); original = deepcopy(values[0])
        self.assertEqual(legacy_extract(*values)['kind'], 'missing_evidence')
        result = self.measured(values)
        self.assertTrue(result['qualified'], result)
        measurement = result['measurement']
        self.assertEqual(measurement['http']['status'], 500)
        self.assertEqual(sum(r['status'] == 500 for r in measurement['readbacks'].values()), 4)
        self.assertEqual(measurement['persistence']['immediate'], {'state': 'not_planned'})
        self.assertIsNone(measurement['persistence']['immediate_projection_survives_restart'])
        self.assertEqual(measurement['continuation']['state'], 'not_executed_prefix_unsuccessful')
        self.assertEqual(values[0], original)
        self.assertEqual(legacy_extract(*values)['kind'], 'missing_evidence')

    def test_rejection_does_not_establish_database_rollback(self):
        result = self.measured(synthetic(username=None, status=422, unknown=False))
        self.assertTrue(result['qualified'], result)
        self.assertEqual(result['measurement']['persistence']['selected_change'], 'unknown')

    def test_missing_probe_cannot_disappear(self):
        raw, spec, fixture = failed_reads(); raw['identity']['after']['reads'].pop()
        self.assertFalse(self.measured((raw, spec, fixture))['qualified'])

    def test_status_without_matching_trace_rejected(self):
        raw, spec, fixture = failed_reads(); raw['identity']['after']['reads'][0]['status'] = 200
        self.assertFalse(self.measured((raw, spec, fixture))['qualified'])

    def test_reordered_probes_rejected(self):
        raw, spec, fixture = failed_reads(); raw['identity']['after']['reads'].reverse()
        self.assertFalse(self.measured((raw, spec, fixture))['qualified'])

    def test_changed_actor_or_command_rejected(self):
        for field in ('actor', 'command'):
            raw, spec, fixture = failed_reads()
            if field == 'actor': raw['actor']['email'] = 'other@example.com'
            else:
                next(e for e in raw['trace'] if e['type'] == 'request' and e['phase'] == 'prefix')['payload']['user']['username'] = 'other'
            self.assertFalse(self.measured((raw, spec, fixture))['qualified'])

    def test_extra_write_after_error_rejected(self):
        raw, spec, fixture = failed_reads()
        for kind in ('request', 'response'):
            raw['trace'].append({'type': kind, 'source': 'api', 'phase': 'failed_prefix_followup',
                                 'method': 'DELETE', 'path': '/api/articles/base',
                                 'sequence': len(raw['trace']) + 1, 'status': 204})
        self.assertFalse(self.measured((raw, spec, fixture))['qualified'])

    def test_false_continuation_claim_rejected(self):
        raw, spec, fixture = failed_reads(); raw['observations']['ui_continuation_started'] = True
        self.assertFalse(self.measured((raw, spec, fixture))['qualified'])

    def test_unfinished_capture_rejected(self):
        raw, spec, fixture = failed_reads(); raw['capture_integrity']['complete'] = False
        self.assertFalse(self.measured((raw, spec, fixture))['qualified'])

    def test_no_database_inference_from_forged_raw_field(self):
        raw, spec, fixture = failed_reads()
        raw['database'] = {'username_committed': True}
        result = self.measured((raw, spec, fixture))
        self.assertTrue(result['qualified'], result)
        self.assertEqual(result['measurement']['persistence']['selected_change'], 'unknown')

    def test_unqualified_continuation_cannot_gain_a_pass_from_read_statuses(self):
        raw, spec, fixture = synthetic()
        raw['identity']['after']['data']['user']['bio'] = 'unbound summary'
        result = self.measured((raw, spec, fixture))
        self.assertTrue(result['qualified'], result)
        self.assertEqual(result['measurement']['continuation']['state'], 'unqualified')

    def test_readback_before_write_rejected_even_with_reindexed_bindings(self):
        raw, spec, fixture = failed_reads()
        prefix = [e for e in raw['trace'] if e['phase'] == 'prefix']
        raw['trace'] = [e for e in raw['trace'] if e['phase'] != 'prefix'] + prefix
        mapping = {e['sequence']: i + 1 for i, e in enumerate(raw['trace'])}
        for i, e in enumerate(raw['trace']): e['sequence'] = i + 1
        for name in ('before', 'after'):
            for read in raw['identity'][name]['reads']:
                read['response_sequence'] = mapping[read['response_sequence']]
        self.assertFalse(self.measured((raw, spec, fixture))['qualified'])

    def test_fixture_substitution_rejected(self):
        raw, spec, fixture = failed_reads(); fixture['base']['body'] = 'other fixture'
        self.assertFalse(self.measured((raw, spec, fixture))['qualified'])


if __name__ == '__main__': unittest.main()
