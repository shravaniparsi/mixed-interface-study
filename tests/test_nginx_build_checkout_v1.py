"""Exercise complete Git-tree and working-file provenance with a local fixture."""
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import tempfile
import unittest

path = Path(__file__).resolve().parents[1] / 'scripts/extension/build_nginx_runtime_v1.py'
spec = importlib.util.spec_from_file_location('nginx_build', path)
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class NginxBuildCheckoutTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.git('init', '-q')
        (self.root / 'backend').mkdir()
        (self.root / 'backend/source.js').write_text('export default 1;\n')
        (self.root / 'second.txt').write_text('also retained in complete tree\n')
        self.git('add', '.')
        self.git('-c', 'user.name=Fixture', '-c', 'user.email=fixture@example.invalid', 'commit', '-qm', 'fixture')
        self.revision = self.git('rev-parse', 'HEAD').strip()
        self.tree = []
        for item in self.git('ls-tree', '-r', '-t', '-z', 'HEAD').split('\0'):
            if item:
                metadata, name = item.split('\t', 1)
                mode, kind, sha = metadata.split(' ')
                self.tree.append(dict(path=name, mode=mode, type=kind, sha=sha))
        raw = (self.root / 'backend/source.js').read_bytes()
        self.rows = [dict(path='backend/source.js', bytes=len(raw), sha256=hashlib.sha256(raw).hexdigest())]

    def git(self, *args):
        return subprocess.check_output(['git', '-C', str(self.root), *args], text=True)

    def test_accept_exact_tree_and_working_file(self):
        result = build.verify_checkout(self.root, self.revision, self.tree, self.rows)
        self.assertEqual(result, self.rows)

    def test_reject_tree_omission_outside_acquired_files(self):
        tree = [r for r in self.tree if r['path'] != 'second.txt']
        with self.assertRaisesRegex(AssertionError, 'recursive tree'):
            build.verify_checkout(self.root, self.revision, tree, self.rows)

    def test_reject_mode_or_object_change(self):
        for key, replacement in [('mode', '100755'), ('sha', '0' * 40)]:
            with self.subTest(key=key):
                tree = [dict(r) for r in self.tree]
                row = next(r for r in tree if r['path'] == 'second.txt')
                row[key] = replacement
                with self.assertRaisesRegex(AssertionError, 'recursive tree'):
                    build.verify_checkout(self.root, self.revision, tree, self.rows)

    def test_reject_working_source_edit_even_with_same_git_head(self):
        (self.root / 'backend/source.js').write_text('export default 2;\n')
        with self.assertRaisesRegex(AssertionError, 'Source mismatch'):
            build.verify_checkout(self.root, self.revision, self.tree, self.rows)

    def test_reject_wrong_revision(self):
        with self.assertRaisesRegex(AssertionError, 'revision mismatch'):
            build.verify_checkout(self.root, '0' * 40, self.tree, self.rows)


if __name__ == '__main__':
    unittest.main()
