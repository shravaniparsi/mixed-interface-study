"""Real local pipes/private files with a fake worker; no browser or network."""
import hashlib
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from seatsurfing_browser_bridge_v1 import BrowserBridge

WORKER = r'''
import hashlib,json,pathlib,sys,time
root=pathlib.Path(sys.argv[1]);root.mkdir()
print(json.dumps({'status':'ready','mode':'native_login','browserVersion':'151.0.7922.34','runtimeQualified':False}),flush=True)
for line in sys.stdin:
 c=json.loads(line)
 time.sleep(c.get('delay',0))
 raw=json.dumps({'synthetic':True}).encode()
 name=c['requestId']+'-result.json'
 (root/name).write_bytes(raw)
 print(json.dumps({'requestId':c['requestId'],'status':'completed','artifact':{'file':name,'sha256':hashlib.sha256(raw).hexdigest()},'phase':'editor'}),flush=True)
'''


class BridgeTest(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory(prefix='study-seatsurfing-bridge-')
        self.addCleanup(self.temp.cleanup)
        self.root=Path(self.temp.name)
        self.bridge=BrowserBridge([sys.executable,'-u','-c',WORKER,str(self.root/'artifacts')],self.root/'transport',self.root/'artifacts','native_login')
        self.addCleanup(self.bridge.close)
        self.bridge.await_ready()

    def test_exact_result_artifact(self):
        self.assertEqual(self.bridge.send({'requestId':'one','operation':'synthetic'}),{'synthetic':True})

    def test_timeout_keeps_original_command_and_process(self):
        with self.assertRaises(TimeoutError):
            self.bridge.send({'requestId':'one','delay':0.12},command_seconds=2,observe_seconds=0.02)
        self.assertIsNone(self.bridge.process.poll())
        with self.assertRaises(ValueError): self.bridge.send({'requestId':'two'})
        self.assertEqual(self.bridge.observe_pending(1),{'synthetic':True})
        self.assertEqual(self.bridge.used_ids,{'one'})

    def test_completed_id_cannot_be_resent(self):
        self.bridge.send({'requestId':'one'})
        with self.assertRaises(ValueError): self.bridge.send({'requestId':'one'})

    def test_hash_mismatch_rejected(self):
        self.bridge.send({'requestId':'one'})
        with self.assertRaisesRegex(ValueError,'hash mismatch'):
            self.bridge.read_artifact({'artifact':{'file':'one-result.json','sha256':'0'*64}},'one')

    def test_path_escape_rejected(self):
        with self.assertRaisesRegex(ValueError,'name/hash'):
            self.bridge.read_artifact({'artifact':{'file':'../outside.json','sha256':'0'*64}},'one')

    def test_symlink_result_rejected(self):
        self.bridge.send({'requestId':'one'})
        path=self.root/'artifacts/one-result.json'
        raw=path.read_bytes();path.unlink()
        (self.root/'outside.json').write_bytes(raw);path.symlink_to(self.root/'outside.json')
        with self.assertRaisesRegex(ValueError,'regular'):
            self.bridge.read_artifact({'artifact':{'file':path.name,'sha256':hashlib.sha256(raw).hexdigest()}},'one')

    def test_original_deadline_does_not_allow_resend(self):
        # Fix the observation clock: a busy CI runner can consume the entire
        # 20 ms deadline before send() reaches its first observe_pending call.
        # This tests the two distinct states without a scheduler-dependent race.
        with patch('seatsurfing_browser_bridge_v1.time.monotonic',return_value=100), patch.object(self.bridge,'read_message',side_effect=TimeoutError('synthetic observation timeout')):
            with self.assertRaises(TimeoutError): self.bridge.send({'requestId':'one'},command_seconds=0.02,observe_seconds=0.01)
        self.assertFalse(self.bridge.failed)
        with patch('seatsurfing_browser_bridge_v1.time.monotonic',return_value=101):
            with self.assertRaises(TimeoutError): self.bridge.observe_pending(1)
        self.assertTrue(self.bridge.failed)
        self.assertEqual(self.bridge.used_ids,{'one'})
        with self.assertRaises(ValueError): self.bridge.send({'requestId':'two'})


class CommandLayoutTest(unittest.TestCase):
    def test_pinned_isolated_launch_has_no_auto_removal_or_host_ports(self):
        from launch_seatsurfing_browser_v1 import browser_command, BROWSER_IMAGE_ID, PG
        command=browser_command(Path('/tools'),Path('/private/config.json'),Path('/private/evidence'))
        self.assertIn(BROWSER_IMAGE_ID,command)
        self.assertEqual(command[command.index('--network')+1],'container:'+PG)
        self.assertNotIn('--rm',command)
        self.assertNotIn('-p',command)
        self.assertIn('--read-only',command)
        self.assertIn('/private/config.json:/input/config.json:ro',command)

    def test_restore_mounts_only_exact_snapshot_file(self):
        from launch_seatsurfing_browser_v1 import browser_command
        command=browser_command(Path('/tools'),Path('/private/config.json'),Path('/private/evidence'),Path('/private/checkpoint/storage.json'))
        self.assertIn('/private/checkpoint/storage.json:/private/checkpoint/storage.json:ro',command)
        self.assertNotIn('/private/checkpoint:/private/checkpoint:ro',command)


if __name__=='__main__':unittest.main()
