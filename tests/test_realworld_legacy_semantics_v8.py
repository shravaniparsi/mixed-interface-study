"""Synthetic v8 envelopes over unchanged historic native traces; not live qualification."""
from copy import deepcopy
from pathlib import Path
import hashlib
import json
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import realworld_legacy_jobs_v8 as jobs
import realworld_terminal_outcomes as previous
import realworld_legacy_terminal_v8 as current

FIXTURES = ROOT / 'tests/fixtures/legacy-native-v8'
def read(name): return json.loads((FIXTURES / name).read_bytes())


def example(cid):
    run = next(b for b in read('summary.json')['branches'] if b['candidate_id'] == cid)
    raw = read(run['evidence'])
    # Deliberately synthetic envelope. Historical runs lack v8 transport/timing.
    raw['oracle_revision'] = 3
    run.update(status='completed', backend_exit_confirmed=True)
    spec = next(s for s in jobs.selection()['cases'] if s['candidate_id'] == cid)
    return raw, run, spec


def classify(value, module=current):
    raw, run, spec = value
    return module.classify_branch(raw, run, spec, fixture=read('fixture-references.json'),
                                  cleanup_confirmed=True)


class LegacySemanticTests(unittest.TestCase):
    def test_original_trace_bytes_match_provenance(self):
        for name, expected in read('provenance.json')['files'].items():
            self.assertEqual(hashlib.sha256((FIXTURES / name).read_bytes()).hexdigest(), expected)

    def test_native_comment_regression_reproduced_and_fixed(self):
        value = example('comment-native-control')
        self.assertEqual(classify(value, previous)['kind'], 'missing_evidence')
        self.assertIn('check_value_not_supported_by_recorded_state:comment_loaded_in_parent',
                      classify(value, previous)['issues'])
        self.assertEqual(classify(value)['kind'], 'clean_observation')

    def test_profile_success_preserved(self):
        value = example('profile-native-control')
        self.assertEqual(classify(value), classify(value, previous))
        self.assertEqual(classify(value)['kind'], 'clean_observation')

    def test_input_records_not_rewritten(self):
        value = example('comment-native-control'); saved = deepcopy(value)
        classify(value)
        self.assertEqual(value, saved)

    def test_prefix_list_cannot_substitute_for_continuation_list(self):
        value = example('comment-native-control'); raw = value[0]
        for event in raw['trace']:
            if event.get('phase') == 'continuation' and event.get('source') == 'ui' and event.get('method') == 'GET' and event.get('path', '').endswith('/comments'):
                event['phase'] = 'prefix'
        self.assertEqual(classify(value)['kind'], 'missing_evidence')
        self.assertIn('missing_continuation_comment_list', classify(value)['issues'])

    def test_wrong_comment_identity_fails_closed(self):
        value = example('comment-native-control')
        for event in value[0]['trace']:
            if event.get('phase') == 'continuation' and event.get('source') == 'ui' and event.get('type') == 'response' and event.get('method') == 'GET' and event.get('path', '').endswith('/comments'):
                for comment in event['data']['comments']: comment['id'] += 999
        self.assertEqual(classify(value)['kind'], 'missing_evidence')

    def test_singleton_success_still_has_no_paired_contrast(self):
        registry = jobs.selection()
        for cid in ('comment-native-control', 'profile-native-control'):
            job = next(j for j in jobs.plan_for(registry)['jobs'] if j['candidate_id'] == cid)
            raw, run, spec = example(cid)
            result = jobs.extract(job, {'ui': (raw, run)}, spec,
                                  read('fixture-references.json'), 'synthetic', True, {})
            self.assertEqual(result['branch']['kind'], 'clean_observation')
            self.assertIsNone(result['channel_discrepancy'])
            self.assertFalse(result['paired_comparison_eligible'])

    def test_synthetic_cleanup_assumption_cannot_be_removed(self):
        value = example('comment-native-control'); del value[1]['backend_exit_confirmed']
        self.assertEqual(classify(value)['kind'], 'cleanup_unconfirmed')
