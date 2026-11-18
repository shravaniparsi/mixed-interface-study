"""Mocked launcher verification: no network, Docker or application execution."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
import launch_seatsurfing_api_v1 as launcher


class ApiLauncher(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory(prefix='seatsurfing-api-launcher-'); self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        self.storage = self.root / 'storage.json'; self.storage.write_text('{"cookies":[]}')
        self.build = self.root / 'build.json'; self.build.write_text('{"study_commit":"commit"}')
        self.kw = dict(operation='ordinary_create', storage=self.storage, storage_sha256=hashlib.sha256(self.storage.read_bytes()).hexdigest(), build_report=self.build, private_directory=self.root / 'operation')
        env = patch.dict(os.environ, GITHUB_ACTIONS='true', GITHUB_REPOSITORY='shravaniparsi/mixed-interface-study', GITHUB_SHA='commit'); env.start(); self.addCleanup(env.stop)
        bind = patch.object(launcher, 'bind_build', return_value='app-image'); bind.start(); self.addCleanup(bind.stop)
        self.app = {'Id':'app', 'Image':'app-image', 'Config':{'Labels':{'org.mixed-interface.study':'seatsurfing-qualification-v1'}}, 'State':{'Running':True,'Paused':False,'Restarting':False}, 'HostConfig':{'NetworkMode':'container:pg'}}
        self.pg = {**self.app, 'Id':'pg', 'Image':launcher.PG_IMAGE_ID, 'HostConfig':{'NetworkMode':'none'}}
        def check(argv, **kwargs):
            if argv[1] == 'ps': return b''
            if argv[1] == 'inspect': return json.dumps([self.app,self.pg]).encode()
            return json.dumps([{'Id':launcher.BROWSER_IMAGE_ID,'Os':'linux','Architecture':'amd64'}]).encode()
        check_patch = patch.object(launcher.subprocess,'check_output',side_effect=check); check_patch.start(); self.addCleanup(check_patch.stop)
    def fake_run(self, argv, **kwargs):
        private = self.kw['private_directory']; config = private/'config.json'
        result = {'status':'api_operation_observed','operation':'ordinary_create','storageSha256':self.kw['storage_sha256'],'configSha256':hashlib.sha256(config.read_bytes()).hexdigest(),'result':{'outcome':'ordinary_create_http_observed'}}
        (private/'worker/result.json').write_text(json.dumps(result))
        return subprocess.CompletedProcess(argv,0,b'',b'')
    def test_isolated_command_mounts_only_storage_not_parent_directory(self):
        command=launcher.api_command('worker',Path('/config'),Path('/storage'),Path('/evidence'))
        self.assertEqual(command[command.index('--network')+1],'container:'+launcher.PG)
        self.assertIn('/storage:/input/storage.json:ro',command);self.assertIn('--read-only',command);self.assertNotIn('--rm',command)
        self.assertEqual(command[command.index('--user')+1], f'{os.getuid()}:{os.getgid()}')
        self.assertNotIn('-p',command);self.assertNotIn('--privileged',command)
    def test_success_binds_retained_private_result_to_inputs(self):
        with patch.object(launcher.subprocess,'run',side_effect=self.fake_run) as run:
            result=launcher.run_api_operation(**self.kw)
        self.assertEqual(result['status'],'api_worker_result_retained');self.assertEqual(run.call_count,1)
        self.assertEqual((self.kw['private_directory']/'launch-result.json').stat().st_mode & 0o777,0o600)
    def test_timeout_never_retries_or_classifies_http_rejection(self):
        with patch.object(launcher.subprocess,'run',side_effect=subprocess.TimeoutExpired(['docker'],95,output=b'partial')) as run:
            result=launcher.run_api_operation(**self.kw)
        self.assertEqual(result['status'],'api_worker_deadline');self.assertTrue(result['container_may_still_be_running']);self.assertEqual(run.call_count,1)
    def test_result_input_tampering_rejected(self):
        def changed(argv, **kwargs):
            result=self.fake_run(argv,**kwargs); path=self.kw['private_directory']/'worker/result.json'
            value=json.loads(path.read_text());value['storageSha256']='wrong';path.write_text(json.dumps(value));return result
        with patch.object(launcher.subprocess,'run',side_effect=changed): result=launcher.run_api_operation(**self.kw)
        self.assertEqual(result['status'],'api_worker_instrument_failure')
    def test_wrong_namespace_refused_before_dispatch(self):
        self.app['HostConfig']['NetworkMode']='bridge'
        with patch.object(launcher.subprocess,'run') as run:
            with self.assertRaisesRegex(RuntimeError,'namespace'):launcher.run_api_operation(**self.kw)
            run.assert_not_called()
    def test_wrong_storage_hash_refused_before_dispatch(self):
        self.kw['storage_sha256']='wrong'
        with patch.object(launcher.subprocess,'run') as run:
            with self.assertRaisesRegex(ValueError,'hash'):launcher.run_api_operation(**self.kw)
            run.assert_not_called()


if __name__ == '__main__': unittest.main()
