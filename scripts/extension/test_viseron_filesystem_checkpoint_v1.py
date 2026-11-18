import json
import os
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from viseron_filesystem_checkpoint_v1 import capture, restore, inventory


class CheckpointTests(unittest.TestCase):
    def setUp(self):
        # macOS Python lacks this Linux-only API. Exercise real xattr checks in CI.
        if not hasattr(os, "listxattr"):
            mock = patch.object(os, "listxattr", return_value=[], create=True)
            mock.start()
            self.addCleanup(mock.stop)
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.base = Path(self.temp.name).resolve()
        self.root = self.base / 'state'
        self.root.mkdir()
        self.store = self.root / '.viseron'
        self.store.mkdir()
        (self.store / 'auth').write_text('synthetic-secret')
        (self.root / 'config.yaml').write_text('webserver: {}\n')
        os.chmod(self.store / 'auth', 0o600)
        self.checkpoint = self.base / 'checkpoint'

    def test_roundtrip_restores_deleted_changed_and_extra_entries_with_metadata(self):
        before = inventory(self.root)
        report = capture(self.root, self.checkpoint)
        (self.store / 'auth').unlink()
        (self.root / 'config.yaml').write_text('changed')
        (self.root / 'extra').mkdir()
        (self.root / 'extra' / 'new').write_text('new')
        result = restore(self.root, self.checkpoint)
        self.assertEqual(inventory(self.root), before)
        self.assertEqual(result['state_sha256'], report['state_sha256'])
        self.assertNotIn('synthetic-secret', json.dumps(result))

    def test_tampered_checkpoint_rejected_before_destination_changes(self):
        capture(self.root, self.checkpoint)
        (self.checkpoint / 'tree' / '.viseron' / 'auth').write_text('tamper')
        before = inventory(self.root)
        with self.assertRaisesRegex(RuntimeError, 'mismatch'):
            restore(self.root, self.checkpoint)
        self.assertEqual(inventory(self.root), before)

    def test_symlink_refused_without_reading_or_removing_target(self):
        outside = self.base / 'outside'
        outside.write_text('untouched')
        (self.root / 'link').symlink_to(outside)
        with self.assertRaisesRegex(RuntimeError, 'non-regular'):
            capture(self.root, self.checkpoint)
        self.assertEqual(outside.read_text(), 'untouched')
        self.assertFalse(self.checkpoint.exists())

    def test_nested_checkpoint_refused(self):
        with self.assertRaisesRegex(RuntimeError, 'overlap'):
            capture(self.root, self.root / 'checkpoint')

    def test_hardlinks_refused(self):
        os.link(self.store / 'auth', self.root / 'alias')
        with self.assertRaisesRegex(RuntimeError, 'Hard-linked'):
            capture(self.root, self.checkpoint)

    def test_extended_attributes_refused(self):
        with patch.object(os, "listxattr", return_value=["user.fixture"]):
            with self.assertRaisesRegex(RuntimeError, "Extended attributes"):
                capture(self.root, self.checkpoint)

    def test_overwrite_refused(self):
        capture(self.root, self.checkpoint)
        with self.assertRaisesRegex(RuntimeError, 'overwrite'):
            capture(self.root, self.checkpoint)


if __name__ == '__main__':
    unittest.main()
