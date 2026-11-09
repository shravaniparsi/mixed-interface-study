"""Archived controls and adversarial fixtures; no new application executions."""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import realworld_terminal_outcomes as bridge


class RealWorldTerminalTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.directory = ROOT / 'results/realworld-paired-controls-ci-20261107'
        cls.read = staticmethod(lambda name: json.loads((cls.directory / name).read_bytes()))
        cls.summary = cls.read('summary.json')
        cls.specs = {c['candidate_id']: c for c in cls.read('registered-candidates.json')['cases']}
        cls.fixture = cls.read('fixture-references.json')

    def setUp(self):
        self.run = deepcopy(self.summary['branches'][0])
        self.raw = self.read(self.run['evidence'])
        self.spec = deepcopy(self.specs[self.run['candidate_id']])

    def classify(self, cleanup=True):
        return bridge.classify_branch(self.raw, self.run, self.spec,
                                      fixture=self.fixture, cleanup_confirmed=cleanup)

    def test_all_fourteen_archived_controls(self):
        for branch in self.summary['branches']:
            with self.subTest(branch=branch['case_id']):
                value = bridge.classify_branch(self.read(branch['evidence']), branch,
                    self.specs[branch['candidate_id']], fixture=self.fixture, cleanup_confirmed=True)
                self.assertEqual(value['kind'], 'clean_observation')

    def test_cleanup_precedes_timeout(self):
        self.run['timed_out'] = True
        self.assertEqual(self.classify(False)['kind'], 'cleanup_unconfirmed')

    def test_backend_exit_required(self):
        self.run['backend_exit_confirmed'] = False
        self.assertEqual(self.classify()['kind'], 'cleanup_unconfirmed')

    def test_timeout(self):
        self.run['timed_out'] = True
        self.assertEqual(self.classify()['kind'], 'case_timeout')

    def test_interrupt_precedes_timeout(self):
        self.run.update(interrupted=True, timed_out=True)
        self.assertEqual(self.classify()['kind'], 'interrupted')

    def test_missing_result(self):
        self.raw = {}
        self.assertEqual(self.classify()['kind'], 'missing_evidence')

    def test_exception_not_application_failure(self):
        self.raw['error'] = {'message': 'HTTP 500'}
        self.assertEqual(self.classify()['kind'], 'environment_failure')

    def test_unexpected_exit(self):
        self.run['exit_code'] = 1
        self.assertEqual(self.classify()['kind'], 'environment_failure')

    def test_boolean_exit_rejected(self):
        self.run['exit_code'] = False
        self.assertEqual(self.classify()['kind'], 'environment_failure')

    def test_failed_runner_not_relabelled(self):
        self.run['status'] = 'failed'
        self.assertEqual(self.classify()['kind'], 'environment_failure')

    def test_completed_transport_translation_preserves_inputs(self):
        self.run['status'] = 'completed'
        saved = deepcopy((self.raw, self.run))
        self.assertEqual(self.classify()['kind'], 'clean_observation')
        self.assertEqual((self.raw, self.run), saved)

    def test_missing_integrity(self):
        del self.raw['integrity']
        self.assertEqual(self.classify()['kind'], 'missing_evidence')

    def test_forged_business_verdict(self):
        next(c for c in self.raw['checks'] if c['name'] == 'prefix_tag_response_representation')['passed'] = False
        self.assertEqual(self.classify()['kind'], 'missing_evidence')

    def test_wrong_registered_identity(self):
        self.spec['candidate_id'] = 'unrelated'
        self.assertEqual(self.classify()['kind'], 'missing_evidence')

    def test_malformed_trace(self):
        self.raw['trace'] = [None]
        self.assertEqual(self.classify()['kind'], 'missing_evidence')

    def test_trace_supported_expectation_mismatch_is_complete(self):
        # Synthetic expectation counterexample, not a new application finding.
        self.spec['expectation']['outcome'] = 'reject'
        self.raw['expectation'] = deepcopy(self.spec['expectation'])
        self.assertEqual(self.classify()['kind'], 'completed_mismatch')

    def test_unresolved_expectation_remains_unresolved(self):
        self.spec['expectation']['category'] = 'unresolved'
        self.raw['expectation'] = deepcopy(self.spec['expectation'])
        self.assertEqual(self.classify()['kind'], 'unresolved_policy')

    def test_capture_integrity_required(self):
        del self.raw['capture_integrity']
        self.assertEqual(self.classify()['kind'], 'missing_evidence')
