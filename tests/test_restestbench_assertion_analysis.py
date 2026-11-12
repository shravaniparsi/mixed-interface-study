"""Failure-site descriptions must follow predicates, not assertion messages."""
import importlib.util
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('assertion_analysis', ROOT / 'scripts/extension/build_restestbench_assertion_analysis_v1.py')
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)


class AssertionSiteTests(unittest.TestCase):
    path = 'data/tests/fastapi/test_1.py'

    def locate(self, source, line=1):
        return m.locate_failure(f'{self.path}:{line}: in test_example\n', {self.path: source})

    def test_status_in_message_does_not_change_predicate_category(self):
        result = self.locate('assert body["title"] == expected, f"status {response.status_code}"\n')
        self.assertEqual(result['kind'], 'other_assertion')

    def test_multiline_status_predicate_is_located(self):
        result = self.locate('assert (\n    response.status_code in [200, 201]\n)\n', 2)
        self.assertEqual(result['kind'], 'http_status_assertion')

    def test_exception_outside_assertion_is_not_assertion_site(self):
        result = self.locate('title = body["title"]\nassert title == expected\n')
        self.assertEqual(result['kind'], 'non_assertion_site')
        self.assertEqual(m.locate_failure('missing traceback', {})['kind'], 'unresolved_failure_site')


if __name__ == '__main__':
    unittest.main()
