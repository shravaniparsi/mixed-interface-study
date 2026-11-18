import importlib.util
import os
from pathlib import Path
import sqlite3
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts/extension'))
spec = importlib.util.spec_from_file_location('restore_db', ROOT / 'scripts/extension/nginx_sqlite_restore_v1.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

@unittest.skipUnless(hasattr(os, 'listxattr'), 'Native filesystem checks run on Linux CI')
class RestoreTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve(); self.data = self.base / 'data'; self.data.mkdir()
        self.certs = self.base / 'certs'; self.certs.mkdir()
        self.db = self.data / 'database.sqlite'; self.backup = self.base / 'backup.sqlite'
        for path, value in [(self.db, 'previous'), (self.backup, 'checkpoint')]:
            with sqlite3.connect(path) as db:
                db.execute('CREATE TABLE fixture (value TEXT, bytes BLOB)')
                db.execute('INSERT INTO fixture VALUES (?, ?)', (value, b'\x00\xff'))
        self.expected = m.digest(self.backup)
        self.db.chmod(0o600)
        self.guard = patch.object(m, 'inspect_container', return_value={'mode': 'restore', 'container_id': 'synthetic-test'})
        self.inspect = self.guard.start(); self.addCleanup(self.guard.stop)
    def run_restore(self):
        return m.restore_database_file('fixture', self.data, self.certs, self.backup, self.expected)
    def test_restores_sqlite_bytes_and_removes_only_old_sidecars(self):
        for name in m.SIDECARS: (self.data / name).write_bytes(b'old sidecar fixture')
        (self.data / 'keys.json').write_text('must remain')
        before = self.db.stat()
        result = self.run_restore()
        with sqlite3.connect(self.db) as db:
            self.assertEqual(db.execute('SELECT * FROM fixture').fetchall(), [('checkpoint', b'\x00\xff')])
            self.assertEqual(db.execute('PRAGMA integrity_check').fetchone(), ('ok',))
        self.assertEqual(self.db.stat().st_mode, before.st_mode)
        self.assertEqual(self.db.stat().st_mtime_ns, before.st_mtime_ns)
        self.assertEqual((self.data / 'keys.json').read_text(), 'must remain')
        self.assertEqual(len(result['removed_sidecars']), 3)
    def test_wrong_digest_leaves_database_untouched(self):
        before = self.db.read_bytes(); self.expected = '0' * 64
        with self.assertRaises(ValueError): self.run_restore()
        self.assertEqual(self.db.read_bytes(), before)
    def test_running_writer_guard_failure_leaves_database_untouched(self):
        before = self.db.read_bytes(); self.inspect.side_effect = ValueError('writers active')
        with self.assertRaises(ValueError): self.run_restore()
        self.assertEqual(self.db.read_bytes(), before)
    def test_lifecycle_change_before_replace_leaves_database_untouched(self):
        before = self.db.read_bytes(); self.inspect.side_effect = [{'id': 'one'}, {'id': 'two'}]
        with self.assertRaises(ValueError): self.run_restore()
        self.assertEqual(self.db.read_bytes(), before)
        self.assertEqual(list(self.data.glob('.study-database-restore-*')), [])
    def test_symlink_sidecar_rejected_without_touching_target(self):
        outside = self.base / 'outside'; outside.write_text('private outside')
        (self.data / m.SIDECARS[0]).symlink_to(outside)
        before = self.db.read_bytes()
        with self.assertRaises(ValueError): self.run_restore()
        self.assertEqual(self.db.read_bytes(), before)
        self.assertEqual(outside.read_text(), 'private outside')
    def test_backup_inside_state_root_rejected(self):
        self.backup = self.data / 'backup.sqlite'; self.backup.write_bytes(self.db.read_bytes())
        with self.assertRaises(ValueError): self.run_restore()

if __name__ == '__main__': unittest.main()
