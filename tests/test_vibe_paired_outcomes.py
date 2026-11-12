"""Known aggregate-count ambiguities and unavailable evidence must remain distinct."""
from pathlib import Path
import sys
import json
import unittest
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts/extension'))
from vibe_paired_outcomes_v1 import compare, node_outcomes, parse_event_text


def node(outcome, exception='AssertionError'):
    return {'outcome': outcome, 'failed_stages': [] if outcome == 'passed' else [{'when': 'call' if outcome == 'failed' else 'setup', 'exception': exception}]}


class PairedOutcomesTests(unittest.TestCase):
    def test_jsonl_preserves_unicode_separators_and_exposes_truncation(self):
        record = {'kind': 'http', 'text': 'a\u0085b\u2028c'}
        text = json.dumps(record, ensure_ascii=False) + '\n' + '{"kind":'
        events, malformed = parse_event_text(text)
        self.assertEqual(events, [record])
        self.assertEqual(malformed[0]['line'], 2)

    def test_equal_counts_can_hide_new_test_failure(self):
        before = {'a': node('passed'), 'b': node('failed')}
        mutant = {'a': node('failed'), 'b': node('passed')}
        counts = {'passed': 1, 'failures': 1, 'errors': 0}
        result = compare(before, mutant, before, counts, counts)
        self.assertFalse(result['aggregate_kill'])
        self.assertEqual(result['new_assertion_failure_nodes'], ['a'])
        self.assertTrue(result['count_rule_disagrees_with_new_failure'])

    def test_error_in_already_failing_test_is_not_new_failure(self):
        before = {'a': node('passed'), 'b': node('failed')}
        mutant = {'a': node('passed'), 'b': node('error', 'ValueError')}
        result = compare(before, mutant, before, {'passed': 1, 'failures': 1, 'errors': 0}, {'passed': 1, 'failures': 0, 'errors': 1})
        self.assertTrue(result['aggregate_kill'])
        self.assertFalse(result['identified_new_failure'])

    def test_unstable_control_and_lost_identity_abstain(self):
        before = {'a': node('passed')}; after = {'a': node('failed')}; counts = {'passed': 1, 'failures': 0, 'errors': 0}
        self.assertEqual(compare(before, after, after, counts, counts)['reason'], 'unstable_original_controls')
        self.assertEqual(compare(before, {}, before, counts, counts)['reason'], 'collection_mismatch_or_empty')
        self.assertIsNone(node_outcomes([{'kind': 'collection', 'nodeids': ['a']}]))


if __name__ == '__main__':
    unittest.main()
