import importlib.util
import json
import os
from pathlib import Path
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('checkpoint', ROOT / 'scripts/extension/nginx_filesystem_checkpoint_v1.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

@unittest.skipUnless(hasattr(os, 'listxattr'), 'Requires native extended-attribute inspection; exercised on Linux CI')
class CheckpointTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name).resolve()
        self.state = self.base / 'state'; self.state.mkdir()
        self.checkpoint = self.base / 'checkpoint'
        (self.state / 'key').write_bytes(b'private fixture\x00bytes')
        (self.state / 'key').chmod(0o600)
        os.utime(self.state / 'key', ns=(1234567890000000000, 1234567890000000000))
    def tearDown(self): self.temp.cleanup()

    def test_roundtrip_preserves_bytes_modes_and_mtimes(self):
        before = m.inventory(self.state); m.capture(self.state, self.checkpoint)
        (self.state / 'key').write_bytes(b'changed'); (self.state / 'extra').write_text('extra')
        m.restore(self.state, self.checkpoint)
        self.assertEqual(m.inventory(self.state), before)

    def test_symlink_not_followed_during_capture_or_restore(self):
        external = self.base / 'external'; external.mkdir(); (external / 'keep').write_text('untouched')
        (self.state / 'link').symlink_to(external, target_is_directory=True)
        before = m.inventory(self.state); m.capture(self.state, self.checkpoint)
        m.restore(self.state, self.checkpoint)
        self.assertEqual(m.inventory(self.state), before)
        self.assertEqual((external / 'keep').read_text(), 'untouched')
        self.assertFalse(any(row['path'].startswith('link/') for row in before))

    def test_tampered_checkpoint_does_not_delete_destination(self):
        m.capture(self.state, self.checkpoint)
        (self.checkpoint / 'tree/key').write_text('tampered')
        before = m.inventory(self.state)
        with self.assertRaises(ValueError): m.restore(self.state, self.checkpoint)
        self.assertEqual(m.inventory(self.state), before)

    def test_manifest_traversal_rejected_before_mutation(self):
        m.capture(self.state, self.checkpoint)
        rows = json.loads((self.checkpoint / 'manifest.json').read_text()); rows[-1]['path'] = '../outside'
        (self.checkpoint / 'manifest.json').write_text(json.dumps(rows))
        before = m.inventory(self.state)
        with self.assertRaises(ValueError): m.restore(self.state, self.checkpoint)
        self.assertEqual(m.inventory(self.state), before)

    def test_overlap_and_overwrite_rejected(self):
        with self.assertRaises(ValueError): m.capture(self.state, self.state / 'checkpoint')
        m.capture(self.state, self.checkpoint)
        with self.assertRaises(ValueError): m.capture(self.state, self.checkpoint)

    def test_special_file_and_hardlink_rejected(self):
        os.link(self.state / 'key', self.state / 'hardlink')
        with self.assertRaises(ValueError): m.inventory(self.state)
        (self.state / 'hardlink').unlink(); os.mkfifo(self.state / 'fifo')
        with self.assertRaises(ValueError): m.inventory(self.state)

if __name__ == '__main__': unittest.main()
