import copy
import unittest
from qualify_viseron_ordinary_v1 import canonical_files


class StateComparisonTests(unittest.TestCase):
    def setUp(self):
        self.rows = [
            {'path': '.viseron', 'kind': 'directory', 'mode': 493, 'uid': 1000, 'gid': 1000, 'mtime_ns': 1},
            {'path': '.viseron/auth', 'kind': 'file', 'mode': 384, 'uid': 1000, 'gid': 1000, 'mtime_ns': 1, 'bytes': 50, 'sha256': 'auth'},
            {'path': '.viseron/webserver', 'kind': 'file', 'mode': 384, 'uid': 1000, 'gid': 1000, 'mtime_ns': 1, 'bytes': 30, 'sha256': 'cookie-secret'},
            {'path': 'viseron.log', 'kind': 'file', 'mode': 420, 'uid': 1000, 'gid': 1000, 'mtime_ns': 1, 'bytes': 10, 'sha256': 'log'},
        ]

    def test_only_registered_log_and_auth_write_metadata_differences_allowed(self):
        other = copy.deepcopy(self.rows)
        for i in [0, 1, 3]:
            other[i]['mtime_ns'] += 1
        other[3].update(bytes=20, sha256='new-log')
        self.assertEqual(canonical_files(self.rows), canonical_files(other))
        self.assertEqual(self.rows[0]['mtime_ns'], 1)

    def test_auth_content_and_cookie_secret_changes_are_not_hidden(self):
        for i in [1, 2]:
            other = copy.deepcopy(self.rows)
            other[i]['sha256'] = 'changed'
            self.assertNotEqual(canonical_files(self.rows), canonical_files(other))

    def test_permissions_and_unregistered_timestamps_are_not_hidden(self):
        for i, key in [(1, 'mode'), (2, 'mtime_ns'), (3, 'uid')]:
            other = copy.deepcopy(self.rows)
            other[i][key] += 1
            self.assertNotEqual(canonical_files(self.rows), canonical_files(other))

    def test_added_rotated_log_or_missing_entry_is_not_hidden(self):
        self.assertNotEqual(canonical_files(self.rows), canonical_files(self.rows[:-1]))
        self.assertNotEqual(canonical_files(self.rows), canonical_files(self.rows + [{'path': 'viseron.log.1'}]))


if __name__ == '__main__':
    unittest.main()
