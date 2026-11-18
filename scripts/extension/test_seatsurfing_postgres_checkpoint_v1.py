"""Synthetic safety-guard checks only: no Docker, database or application."""
import importlib.util
import json
import unittest
from pathlib import Path
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('seat_checkpoint', Path(__file__).with_name('seatsurfing_postgres_checkpoint_v1.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class Guards(unittest.TestCase):
    def setUp(self):
        self.app_image = 'sha256:' + 'a' * 64
        self.items = {
            m.APP: {'State': {'Running': False}, 'Image': self.app_image, 'HostConfig': {'NetworkMode': 'container:' + m.PG}},
            m.PG: {'Id': 'pg-id', 'State': {'Running': True}, 'Image': m.PG_IMAGE_ID, 'HostConfig': {'NetworkMode': 'none'}},
            m.BROWSER: {'State': {'Running': False}, 'Image': m.BROWSER_IMAGE_ID, 'HostConfig': {'NetworkMode': 'container:' + m.PG}},
        }
        self.version = '180007'
        self.connections = '0'
    def invoke(self):
        def run(args, data=None):
            self.assertEqual(args[:2], ['docker', 'inspect'])
            return json.dumps([self.items[args[2]]]).encode()
        def sql(query, database=m.DB):
            if query == 'SHOW server_version_num': return self.version
            if 'FROM pg_database' in query: return 'postgres\nseatsurfing\n'
            if 'pg_stat_activity' in query: return self.connections
            if 'pg_largeobject_metadata' in query: return '0'
            self.fail('Unexpected SQL: ' + query)
        with patch.object(m, 'APP_IMAGE_ID', self.app_image), patch.object(m, 'run', run), patch.object(m, 'sql', sql):
            m.guard()
    def test_stopped_exact_fixture_reaches_guard(self): self.invoke()
    def test_running_application_rejected(self):
        self.items[m.APP]['State']['Running'] = True
        with self.assertRaisesRegex(RuntimeError, 'stopped application'): self.invoke()
    def test_running_browser_rejected(self):
        self.items[m.BROWSER]['State']['Running'] = True
        with self.assertRaisesRegex(RuntimeError, 'Browser must be stopped'): self.invoke()
    def test_wrong_database_image_rejected(self):
        self.items[m.PG]['Image'] = 'sha256:' + 'b' * 64
        with self.assertRaisesRegex(RuntimeError, 'identity mismatch'): self.invoke()
    def test_external_network_rejected(self):
        self.items[m.PG]['HostConfig']['NetworkMode'] = 'bridge'
        with self.assertRaisesRegex(RuntimeError, 'no external network'): self.invoke()
    def test_wrong_server_version_rejected(self):
        self.version = '170007'
        with self.assertRaisesRegex(RuntimeError, 'Server differs'): self.invoke()
    def test_active_database_session_rejected(self):
        self.connections = '1'
        with self.assertRaisesRegex(RuntimeError, 'sessions remain'): self.invoke()

if __name__ == '__main__': unittest.main()
