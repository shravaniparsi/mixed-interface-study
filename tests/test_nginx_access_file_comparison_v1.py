"""Synthetic local OpenSSL checks, not application/runtime qualification."""
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import unittest

path = Path(__file__).resolve().parents[1] / 'scripts/extension/nginx_access_file_comparison_v1.py'
spec = importlib.util.spec_from_file_location('nginx_access_comparison', path)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)


@unittest.skipUnless(shutil.which('openssl'), 'Local OpenSSL required for synthetic verification')
class AccessFileComparisonTests(unittest.TestCase):
    def derive(self, password, salt):
        result = subprocess.run(['openssl', 'passwd', '-apr1', '-salt', salt, '-stdin'],
                                input=(password + '\n').encode(), capture_output=True, check=True, timeout=5)
        return result.stdout.decode().strip()

    def state(self, password='Study-Only-Control-2026'):
        names = ['access_list_id', 'username', 'password']
        return {'tables': [{'name': 'access_list_auth',
                'columns': [[['integer', str(i)], ['text', name]] for i, name in enumerate(names)],
                'rows': [json.dumps([['integer', '3'], ['text', 'studycontrol'], ['text', password]])]}]}

    def file(self, salt='12345678', password='Study-Only-Control-2026'):
        return ('studycontrol:' + self.derive(password, salt) + '\n').encode()

    def test_distinct_valid_salts_verify_against_same_persisted_password(self):
        result = m.compare_ordinary_access_files(self.file(), self.file('abcdefgh'), self.state(), self.state(), 3, self.derive)
        self.assertFalse(result['raw_bytes_equal'])
        self.assertEqual(result['left']['verified_rows'], 1)

    def test_wrong_password_hash_is_not_ignored(self):
        with self.assertRaisesRegex(ValueError, 'authenticate'):
            m.compare_ordinary_access_files(self.file(), self.file(password='wrong'), self.state(), self.state(), 3, self.derive)

    def test_different_database_passwords_are_not_normalized(self):
        with self.assertRaisesRegex(ValueError, 'credentials differ'):
            m.compare_ordinary_access_files(self.file(), self.file(password='wrong'), self.state(), self.state('wrong'), 3, self.derive)

    def test_extra_line_wrong_user_and_missing_newline_rejected(self):
        raw = self.file()
        for changed in [raw + b'\n', raw + raw, raw.replace(b'studycontrol:', b'other:', 1), raw[:-1]]:
            with self.subTest(changed=changed[:20]):
                with self.assertRaises(ValueError):
                    m.verify_access_file(changed, ('studycontrol', 'Study-Only-Control-2026'), self.derive)

    def test_extra_auth_row_rejected(self):
        state = self.state(); state['tables'][0]['rows'] *= 2
        with self.assertRaisesRegex(ValueError, 'exactly one'):
            m.ordinary_credential(state, 3)

    def test_null_stored_password_is_not_reconstructed_from_fixture(self):
        state = self.state()
        row = json.loads(state['tables'][0]['rows'][0]); row[-1] = ['null']
        state['tables'][0]['rows'][0] = json.dumps(row)
        with self.assertRaisesRegex(ValueError, 'stored text'):
            m.ordinary_credential(state, 3)


if __name__ == '__main__':
    unittest.main()
