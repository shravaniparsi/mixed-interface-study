"""Reject successful verdicts without matching original-source execution proof."""
import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('runtime_verifier', ROOT / 'scripts/extension/verify_restestbench_mutant_runtime_v1.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class RuntimeVerifierTests(unittest.TestCase):
    def fixture(self, folder, outcome):
        key = 'req-1-valid'
        registration = {'upstream_commit': 'pin', 'sha256': {'scripts/extension/run_restestbench_mutant_runtime_v1.py': 'instrument'}, 'services': {'fastapi': {'expected_keys': [key], 'requirements': 1, 'mutants': 0}}}
        observation = {'kind': 'restestbench_mutant_runtime_v1', 'service': 'fastapi', 'upstream_commit': 'pin', 'paid_model_calls': 0, 'expected_keys': [key], 'unattempted_keys': [], 'terminal': 'valid_control_failure', 'commands': [], 'trials': [{'key': key, 'requirement_id': 1, 'mutant_index': None, 'control_passed': False, 'mutation_applied': False, 'bytes_changed': False, 'test_executed': False, 'candidate_detection': False, 'outcome': outcome}]}
        (folder / 'study-head.txt').write_text(m.HEAD)
        (folder / 'instrument-sha256.txt').write_text('instrument  runner.py')
        (folder / 'input-sha256.json').write_text('{}')
        (folder / 'observations.json').write_text(json.dumps(observation))
        return registration

    def test_unexecuted_control_cannot_be_reported_passed(self):
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name)
            registration = self.fixture(folder, 'passed')
            with self.assertRaises(AssertionError):
                m.validate_service(folder, registration, {'fastapi': {}}, {})

    def test_unexecuted_setup_failure_remains_accounted(self):
        with tempfile.TemporaryDirectory() as name:
            folder = Path(name)
            registration = self.fixture(folder, 'reset_or_readiness_failure')
            result = m.validate_service(folder, registration, {'fastapi': {}}, {})
            self.assertEqual(result['recorded_controls'], 1)
            self.assertEqual(result['passing_controls'], 0)
            self.assertEqual(result['candidate_detections'], 0)

    def test_junit_error_is_not_assertion_detection(self):
        counts = {'tests': 1, 'errors': 1, 'failures': 0, 'skipped': 0}
        self.assertEqual(m.classify(1, False, counts), 'test_error')
        self.assertEqual(m.classify(1, True, counts), 'timeout')


if __name__ == '__main__':
    unittest.main()
