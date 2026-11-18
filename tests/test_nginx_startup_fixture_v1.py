"""Synthetic fixture/log predicates only, with no live application execution."""
import importlib.util
from pathlib import Path
import unittest

path = Path(__file__).resolve().parents[1] / 'scripts/extension/nginx_startup_fixture_v1.py'
spec = importlib.util.spec_from_file_location('nginx_startup_fixture', path)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


class StartupFixtureTests(unittest.TestCase):
    def setUp(self):
        self.state = {'tables': [{'name':'certificate','rows':[]}, {'name':'proxy_host','rows':[]}]}
        self.logs = '\n'.join(s for pair in m.MARKERS for s in pair).encode()

    def test_empty_fixture_and_both_completed_timers(self):
        result = m.verify_startup_fixture(self.state, self.logs)
        self.assertTrue(result['initial_logrotation_settled'])
        self.assertTrue(result['initial_certificate_timer_settled'])

    def test_nonempty_certificate_or_proxy_table_rejected(self):
        for index in (0,1):
            self.setUp(); self.state['tables'][index]['rows'] = ['retained row']
            with self.assertRaisesRegex(ValueError, 'empty fixture'):
                m.verify_startup_fixture(self.state, self.logs)

    def test_missing_logrotate_completion_is_not_ready(self):
        with self.assertRaisesRegex(ValueError, 'completion evidence'):
            m.verify_startup_fixture(self.state, self.logs.replace(b'Logrotate completed.', b'Logrotate failed'))

    def test_repeated_startup_markers_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Missing/repeated'):
            m.verify_startup_fixture(self.state, self.logs + b'\n' + self.logs)

    def test_completion_before_start_rejected(self):
        with self.assertRaisesRegex(ValueError, 'precedes'):
            m.verify_startup_fixture(self.state, b'\n'.join(reversed(self.logs.splitlines())))


if __name__ == '__main__': unittest.main()
