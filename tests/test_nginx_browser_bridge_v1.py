"""Real local pipe transport, using a synthetic child instead of any browser/app."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest

path = Path(__file__).resolve().parents[1] / 'scripts/extension/nginx_browser_bridge_v1.py'
spec = importlib.util.spec_from_file_location('nginx_bridge', path)
m = importlib.util.module_from_spec(spec); spec.loader.exec_module(m)

CHILD = '''
import json,sys,time
print(json.dumps(dict(status='ready',browserVersion='151.0.7922.34')),flush=True)
for line in sys.stdin:
 c=json.loads(line)
 if c['operation']=='delay': time.sleep(.15)
 if c['operation']=='eof': break
 if c['operation']=='malformed': print('not-json',flush=True); continue
 response=dict(requestId=c['requestId'],status='completed',result={'seen':c['requestId']})
 if c['operation']=='wrong': response['requestId']='different-id'
 if c['operation']=='failed': response['status']='failed'
 print(json.dumps(response),flush=True)
'''


class BrowserBridgeTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.addCleanup(self.temp.cleanup)
        self.bridge = m.BrowserBridge([sys.executable, '-u', '-c', CHILD], Path(self.temp.name) / 'private')
        self.addCleanup(self.bridge.close)
        self.bridge.await_ready(seconds=2)

    def test_success_retains_private_request_response_and_raw_output(self):
        self.assertEqual(self.bridge.send({'requestId':'one','operation':'ok'}), {'seen':'one'})
        self.assertTrue((self.bridge.directory / 'one.request.json').is_file())
        self.assertTrue((self.bridge.directory / 'one.response.json').is_file())
        self.assertGreater((self.bridge.directory / 'worker.stdout').stat().st_size, 0)

    def test_observation_timeout_keeps_same_pending_process_without_resend(self):
        pid = self.bridge.process.pid
        with self.assertRaises(TimeoutError):
            self.bridge.send({'requestId':'one','operation':'delay'}, command_seconds=2, observe_seconds=.01)
        self.assertIsNone(self.bridge.process.poll())
        with self.assertRaises(ValueError):
            self.bridge.send({'requestId':'two','operation':'ok'})
        self.assertEqual(self.bridge.observe_pending(1), {'seen':'one'})
        self.assertEqual(self.bridge.process.pid, pid)
        self.assertEqual(self.bridge.used_ids, {'one'})

    def test_reused_command_id_rejected(self):
        command = {'requestId':'one','operation':'ok'}
        self.bridge.send(command)
        with self.assertRaises(ValueError): self.bridge.send(command)

    def test_identity_mismatch_prevents_further_commands(self):
        with self.assertRaisesRegex(ValueError, 'identity/status'):
            self.bridge.send({'requestId':'one','operation':'wrong'})
        with self.assertRaises(ValueError): self.bridge.send({'requestId':'two','operation':'ok'})

    def test_worker_failure_and_malformed_output_are_not_success(self):
        with self.assertRaises(RuntimeError):
            self.bridge.send({'requestId':'one','operation':'failed'})
        report = json.loads((self.bridge.directory / 'one.response.json').read_text())
        self.assertEqual(report['status'], 'failed')

    def test_eof_does_not_restart_worker(self):
        pid = self.bridge.process.pid
        with self.assertRaises(EOFError):
            self.bridge.send({'requestId':'one','operation':'eof'})
        self.assertEqual(self.bridge.process.pid, pid)
        self.assertTrue(self.bridge.failed)

    def test_malformed_output_is_retained_and_rejected(self):
        with self.assertRaisesRegex(ValueError, 'Malformed'):
            self.bridge.send({'requestId':'one','operation':'malformed'})
        self.assertIn(b'not-json', (self.bridge.directory / 'worker.stdout').read_bytes())


if __name__ == '__main__': unittest.main()
