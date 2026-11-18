"""Synthetic local Git/filesystem evidence tests; no downloads or application."""
import hashlib
from pathlib import Path
import subprocess
import tempfile
import unittest
from build_seatsurfing_runtime_v1 import digest, inventory, verify_checkout


class BuildGuards(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='study-seatsurfing-build-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git('init', '-q')
        (self.root / 'source.txt').write_bytes(b'original\n')
        self.git('add', 'source.txt')
        self.git('-c', 'user.name=Synthetic', '-c', 'user.email=synthetic@example.invalid', 'commit', '-qm', 'fixture')
        self.revision = self.git('rev-parse', 'HEAD')
        blob = self.git('rev-parse', 'HEAD:source.txt')
        self.tree = [{'path': 'source.txt', 'mode': '100644', 'type': 'blob', 'sha': blob}]
        self.rows = [{'path': 'source.txt', 'bytes': 9, 'sha256': digest(self.root / 'source.txt')}]

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], text=True, stderr=subprocess.DEVNULL).strip()

    def test_exact_checkout(self):
        self.assertEqual(len(verify_checkout(self.root, self.revision, self.tree, self.rows)), 1)

    def test_wrong_revision_rejected(self):
        with self.assertRaises(AssertionError):
            verify_checkout(self.root, '0' * 40, self.tree, self.rows)

    def test_omitted_tree_entry_rejected(self):
        with self.assertRaises(AssertionError):
            verify_checkout(self.root, self.revision, [], self.rows)

    def test_modified_source_rejected(self):
        (self.root / 'source.txt').write_bytes(b'modified\n')
        with self.assertRaises(AssertionError):
            verify_checkout(self.root, self.revision, self.tree, self.rows)

    def test_duplicate_source_rejected(self):
        with self.assertRaises(AssertionError):
            verify_checkout(self.root, self.revision, self.tree, self.rows * 2)

    def test_symlink_substitution_rejected(self):
        (self.root / 'source.txt').unlink()
        (self.root / 'target.txt').write_bytes(b'original\n')
        (self.root / 'source.txt').symlink_to('target.txt')
        with self.assertRaises(AssertionError):
            verify_checkout(self.root, self.revision, self.tree, self.rows)

    def test_inventory_records_bytes_and_link_without_following(self):
        directory = self.root / 'artifacts'
        directory.mkdir()
        (directory / 'binary').write_bytes(b'fixture')
        (directory / 'link').symlink_to('binary')
        rows = inventory(directory)
        self.assertEqual(rows[0]['sha256'], hashlib.sha256(b'fixture').hexdigest())
        self.assertEqual(rows[1]['kind'], 'symlink')
        self.assertEqual(rows[1]['target'], 'binary')
        (directory / 'binary').write_bytes(b'changed')
        self.assertNotEqual(rows, inventory(directory))


if __name__ == '__main__':
    unittest.main()
