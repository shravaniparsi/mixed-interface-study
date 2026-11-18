"""Synthetic private-bundle integrity tests; no application/Docker/database."""
import importlib.util
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location('joint', Path(__file__).with_name('seatsurfing_joint_checkpoint_v2.py'))
m = importlib.util.module_from_spec(spec)
spec.loader.exec_module(m)

class Bundle(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.calls = []
        self.origin = 'http://fixture.invalid:8080'
        self.storage = {'cookies': [], 'origins': [{'origin': self.origin, 'localStorage': [{'name': 'accessToken', 'value': 'synthetic-access'}, {'name': 'refreshToken', 'value': 'synthetic-refresh'}]}]}
        for name, raw in {'private.pem': b'synthetic-private', 'public.pem': b'synthetic-public', 'build.json': b'{}', 'storage.json': m.encode(self.storage)}.items():
            (self.root / name).write_bytes(raw)
        self.proof = {k: True for k in ['native_storage_capture','browser_requests_settled','application_operations_settled','actor_verified','token_unchanged','refresh_outside_checkpoint_interval','browser_and_application_stopped','browser_and_application_paused','no_unmapped_browser_state']}
        self.proof.update(storage_sha256=m.digest((self.root/'storage.json').read_bytes()),network_trace_sha256='a'*64)
        self.save_proof()
    def save_proof(self): (self.root/'proof.json').write_bytes(m.encode(self.proof))
    def invoke(self, action):
        def database(action, build, private, report):
            self.calls.append(action)
            if action == 'capture':
                private.mkdir(); (private/'baseline.json').write_bytes(b'{}')
            result={'status':'checkpoint_captured' if action=='capture' else 'restore_matches'}
            report.write_bytes(m.encode(result));return result
        argv=['joint',action,'--checkpoint',str(self.root/'checkpoint'),'--build-report',str(self.root/'build.json'),'--private-key',str(self.root/'private.pem'),'--public-key',str(self.root/'public.pem'),'--origin',self.origin,'--storage',str(self.root/'storage.json'),'--observation',str(self.root/'proof.json'),'--output',str(self.root/(action+'.json'))]
        if action == 'restore':
            capture = json.loads((self.root/'capture.json').read_text())
            argv += ['--expected-manifest-sha256', capture['manifest_sha256']]
        with patch.object(sys,'argv',argv), patch.object(m,'inspect_app',return_value={'Id':'fixture-container'}), patch.object(m,'database',database): m.main()
    def test_capture_and_restore_bind_exact_storage(self):
        self.invoke('capture');self.invoke('restore')
        result=json.loads((self.root/'restore.json').read_text())
        self.assertEqual(result['status'],'database_restored_browser_context_not_started')
        self.assertEqual(Path(result['storage_path']).read_bytes(),(self.root/'storage.json').read_bytes())
        self.assertEqual(self.calls,['capture','restore'])
    def test_mutated_manifest_rejected_before_restore(self):
        self.invoke('capture')
        path=self.root/'checkpoint/manifest.json'; manifest=json.loads(path.read_text())
        manifest['files'].pop('storage.json'); path.write_bytes(m.encode(manifest))
        with self.assertRaisesRegex(ValueError,'retained capture identity'):self.invoke('restore')
        self.assertEqual(self.calls,['capture'])
    def test_incomplete_manifest_rejected_even_with_matching_hash(self):
        self.invoke('capture')
        path=self.root/'checkpoint/manifest.json'; manifest=json.loads(path.read_text())
        manifest['files'].pop('storage.json'); path.write_bytes(m.encode(manifest))
        capture=self.root/'capture.json'; record=json.loads(capture.read_text())
        record['manifest_sha256']=m.digest(path.read_bytes());capture.write_bytes(m.encode(record))
        with self.assertRaisesRegex(ValueError,'Incomplete checkpoint'):self.invoke('restore')
        self.assertEqual(self.calls,['capture'])
    def test_changed_keys_reject_before_database_restore(self):
        self.invoke('capture');(self.root/'private.pem').write_bytes(b'changed')
        with self.assertRaisesRegex(ValueError,'keys changed'):self.invoke('restore')
        self.assertEqual(self.calls,['capture'])
    def test_corrupt_storage_rejects_before_database_restore(self):
        self.invoke('capture');(self.root/'checkpoint/storage.json').write_bytes(b'{}')
        with self.assertRaisesRegex(ValueError,'Corrupt joint'):self.invoke('restore')
        self.assertEqual(self.calls,['capture'])
    def test_incomplete_live_observation_prevents_capture(self):
        self.proof['browser_requests_settled']=False;self.save_proof()
        with self.assertRaisesRegex(ValueError,'prerequisites'):self.invoke('capture')
        self.assertEqual(self.calls,[])
    def test_foreign_origin_rejected(self):
        self.storage['origins'][0]['origin']='https://foreign.invalid'
        with self.assertRaisesRegex(ValueError,'Unexpected browser origin'):m.validate_storage(m.encode(self.storage),self.origin)
    def test_foreign_cookie_rejected(self):
        self.storage['cookies']=[{'domain':'foreign.invalid'}]
        with self.assertRaisesRegex(ValueError,'Unexpected cookie domain'):m.validate_storage(m.encode(self.storage),self.origin)
    def test_duplicate_credential_key_rejected(self):
        self.storage['origins'][0]['localStorage'].append({'name':'accessToken','value':'other'})
        with self.assertRaisesRegex(ValueError,'Duplicate'):m.validate_storage(m.encode(self.storage),self.origin)

if __name__ == '__main__':unittest.main()
