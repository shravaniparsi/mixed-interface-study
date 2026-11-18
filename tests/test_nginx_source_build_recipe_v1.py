import importlib.util
from pathlib import Path
import subprocess
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('recipe', ROOT / 'scripts/extension/prepare_nginx_source_build_v1.py')
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

class BuildRecipeTests(unittest.TestCase):
    def setUp(self):
        self.dockerfile = (ROOT / 'results/catalog-source-wave1-v1/30.txt').read_text()
        self.installer = (ROOT / 'results/catalog-source-wave21-v1/7.txt').read_text()
        self.digest = 'sha256:' + 'a' * 64
        self.archives = {n: self.digest for n in m.ARCHIVES}

    def test_pins_and_verifies_before_extraction_without_shell_execution(self):
        docker, installer = m.derive(self.dockerfile, self.installer, self.digest, self.digest, self.archives)
        self.assertIn('FROM nginxproxymanager/testca@' + self.digest, docker)
        self.assertIn('RUN yarn install --frozen-lockfile', docker)
        self.assertLess(installer.index('sha256sum -c -'), installer.index('tar -C /'))
        run = next(line[4:] for line in docker.splitlines() if line.startswith("RUN printf '%s\\n'"))
        checked = subprocess.run(['bash', '-n'], input=run, text=True, capture_output=True)
        self.assertEqual(checked.returncode, 0, checked.stderr)

    def test_rejects_missing_archive_identity(self):
        with self.assertRaises(ValueError): m.derive(self.dockerfile, self.installer, self.digest, self.digest, {})

    def test_rejects_non_digest_or_shell_text(self):
        with self.assertRaises(ValueError): m.derive(self.dockerfile, self.installer, 'latest; true', self.digest, self.archives)

    def test_rejects_changed_original_build_contract(self):
        with self.assertRaises(ValueError): m.derive(self.dockerfile.replace('RUN yarn install', 'RUN npm install'), self.installer, self.digest, self.digest, self.archives)

if __name__ == '__main__': unittest.main()
