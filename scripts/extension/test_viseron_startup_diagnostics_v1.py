import io
import json
import unittest
import urllib.error
from unittest.mock import patch
from viseron_startup_diagnostics_v1 import probe, summarize_log


class DiagnosticTests(unittest.TestCase):
    def test_http_error_retains_status_without_body_or_headers(self):
        error = urllib.error.HTTPError('http://private', 502, 'private-reason', {'secret': 'private'}, io.BytesIO(b'private-body'))
        with patch('urllib.request.urlopen', side_effect=error):
            self.assertEqual(probe(), {'ready': False, 'http_status': 502, 'error_type': 'HTTPError'})

    def test_connection_failure_retains_errno_without_message(self):
        with patch('urllib.request.urlopen', side_effect=urllib.error.URLError(ConnectionRefusedError(111, 'private-token'))):
            result = probe()
        self.assertEqual(result['errno'], 111)
        self.assertEqual(result['reason_type'], 'ConnectionRefusedError')
        self.assertNotIn('private-token', json.dumps(result))

    def test_unexpected_exception_has_type_only(self):
        with patch('urllib.request.urlopen', side_effect=ValueError('private-token')):
            self.assertEqual(probe(), {'ready': False, 'error_type': 'ValueError'})

    def test_log_markers_do_not_publish_arbitrary_log_text(self):
        result = summarize_log(b'ModuleNotFoundError: private.module\nAuthorization: Bearer private-token\nPermission denied')
        self.assertEqual(result['marker_counts']['ModuleNotFoundError'], 1)
        self.assertEqual(result['marker_counts']['Permission denied'], 1)
        self.assertNotIn('private', json.dumps(result))


if __name__ == '__main__':
    unittest.main()
