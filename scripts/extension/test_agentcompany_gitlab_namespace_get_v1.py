"""Exercise transport error and bounded-response capture without applications."""
import base64
import io
import unittest
from unittest.mock import patch
import urllib.error
from agentcompany_gitlab_namespace_get_v1 import fetch


class Response(io.BytesIO):
    status = 200
    headers = {}
    def geturl(self): return 'http://127.0.0.1:8929/-/health'


class Opener:
    def __init__(self, response=None, error=None): self.response, self.error = response, error
    def open(self, request, timeout):
        self.request = request
        if self.error: raise self.error
        return self.response


@patch('agentcompany_gitlab_namespace_get_v1.os.readlink', return_value='net:[123]')
class CaptureTests(unittest.TestCase):
    def test_health_body_and_namespace(self, _):
        opener = Opener(Response(b'GitLab OK'))
        result = fetch('/-/health', False, 4096, opener)
        self.assertEqual(base64.b64decode(result['body_base64']), b'GitLab OK')
        self.assertEqual(result['network_namespace'], 'net:[123]')
        self.assertFalse(result['truncated'])
        self.assertEqual(opener.request.get_method(), 'GET')
        self.assertFalse(opener.request.has_header('Private-token'))

    def test_http_denial_is_not_connection_error(self, _):
        error = urllib.error.HTTPError('http://127.0.0.1:8929/api/v4/user', 401, 'Unauthorized', {}, io.BytesIO(b'{"message":"401 Unauthorized"}'))
        result = fetch('/api/v4/user', True, 2 * 1024**2, Opener(error=error))
        self.assertEqual(result['status'], 401)
        self.assertNotIn('error_type', result)

    def test_connection_reason_preserved(self, _):
        result = fetch('/-/health', False, 4096, Opener(error=urllib.error.URLError(ConnectionRefusedError(111, 'Connection refused'))))
        self.assertEqual(result['error_type'], 'URLError')
        self.assertIn('Connection refused', result['error'])
        self.assertNotIn('status', result)

    def test_oversize_is_explicit(self, _):
        result = fetch('/-/health', False, 4096, Opener(Response(b'x' * 5000)))
        self.assertTrue(result['truncated'])
        self.assertEqual(len(base64.b64decode(result['body_base64'])), 4096)


if __name__ == '__main__': unittest.main()
