"""Safety checks for immutable recipe preparation; no application execution."""
import importlib.util
from pathlib import Path
import unittest

MODULE = Path(__file__).resolve().parents[1] / 'scripts/extension/build_maintained_maxun_v1.py'
spec = importlib.util.spec_from_file_location('maxun_build', MODULE)
build = importlib.util.module_from_spec(spec)
spec.loader.exec_module(build)


class RecipePinning(unittest.TestCase):
    def setUp(self):
        self.raw = b'FROM node:22 AS builder\nRUN npm install\nFROM node:22-slim AS runner\nCMD ["npm", "run", "server"]\n'
        self.bases = {'node:22': {'digest': 'node@sha256:' + 'a' * 64},
                      'node:22-slim': {'digest': 'node@sha256:' + 'b' * 64}}

    def pin(self, raw=None, digest=None, bases=None, expected=None):
        return build.pin_recipe(raw or self.raw, digest or build.sha(self.raw),
                                expected or ['node:22', 'node:22-slim'], bases or self.bases)

    def test_only_from_changes(self):
        actual = self.pin()
        expected = self.raw.replace(b'FROM node:22 AS', ('FROM node@sha256:' + 'a' * 64 + ' AS').encode())
        expected = expected.replace(b'FROM node:22-slim AS', ('FROM node@sha256:' + 'b' * 64 + ' AS').encode())
        self.assertEqual(actual, expected)

    def test_modified_recipe_rejected(self):
        with self.assertRaises(ValueError):
            self.pin(raw=self.raw.replace(b'npm install', b'npm install --force'))

    def test_wrong_base_rejected(self):
        with self.assertRaises(ValueError):
            self.pin(expected=['node:20', 'node:22-slim'])

    def test_tag_is_not_digest(self):
        with self.assertRaises(ValueError):
            self.pin(bases={'node:22': {'digest': 'node:latest'}, 'node:22-slim': self.bases['node:22-slim']})

    def test_digest_must_be_hex(self):
        with self.assertRaises(ValueError):
            self.pin(bases={'node:22': {'digest': 'node@sha256:' + 'z' * 64}, 'node:22-slim': self.bases['node:22-slim']})


if __name__ == '__main__':
    unittest.main()
