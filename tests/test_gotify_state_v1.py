import importlib.util
from pathlib import Path
import sqlite3
import tempfile
import unittest

spec = importlib.util.spec_from_file_location('gotify_state', Path(__file__).resolve().parents[1] / 'scripts/extension/gotify_state_v1.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


class ExactStateTests(unittest.TestCase):
    def test_committed_wal_is_observed_without_checkpoint(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'state.db'
            writer = sqlite3.connect(path)
            try:
                writer.execute('PRAGMA journal_mode=WAL')
                writer.execute('PRAGMA wal_autocheckpoint=0')
                writer.execute('CREATE TABLE resource (id INTEGER, value TEXT)')
                writer.execute("INSERT INTO resource VALUES (1, 'first')")
                writer.commit()
                before = module.read_state(path)
                writer.execute("UPDATE resource SET value='second'")
                writer.commit()
                after = module.read_state(path)
                self.assertNotEqual(before, after)
                self.assertEqual(after['tables']['resource']['rows'], [[1, 'second']])
            finally:
                writer.close()

    def test_session_timestamp_and_null_are_not_normalized(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'state.db'
            with sqlite3.connect(path) as writer:
                writer.execute('CREATE TABLE client (id INTEGER, last_used TEXT, token BLOB)')
                writer.execute('INSERT INTO client VALUES (1, NULL, ?)', (b'\x00\xff',))
            before = module.read_state(path)
            with sqlite3.connect(path) as writer:
                writer.execute("UPDATE client SET last_used='2026-11-18T00:00:01Z'")
            after = module.read_state(path)
            self.assertNotEqual(before, after)
            self.assertEqual(before['tables']['client']['rows'][0][2], {'sqlite_blob_hex': '00ff'})

    def test_missing_database_is_not_created(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'missing.db'
            with self.assertRaises(sqlite3.OperationalError):
                module.read_state(path)
            self.assertFalse(path.exists())


if __name__ == '__main__':
    unittest.main()
