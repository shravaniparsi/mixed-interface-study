"""Synthetic command/report tests; no Docker or Go compiler runs."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch
from build_seatsurfing_runtime_v1 import schema_dockerfile
from run_seatsurfing_schema_probe_v1 import run_schema_probe, schema_command, ROOT


class SchemaExecution(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(prefix='study-seatsurfing-schema-')
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.image = 'sha256:' + 'a' * 64
        self.report = self.root / 'build.json'
        self.report.write_text(json.dumps({'status':'source_build_verified_and_inventory_complete',
            'application_revision':'9953f452324bab6fb8f7106dd8965cc401aa456c','study_commit':'fixture',
            'original_schema':{'status':'compiled_not_executed','image_id':self.image,'probe_source_sha256':hashlib.sha256((ROOT / 'scripts/extension/seatsurfing_original_schema_v1.go').read_bytes()).hexdigest()}}))
        self.env = patch.dict(os.environ, {'GITHUB_ACTIONS':'true','GITHUB_REPOSITORY':'shravaniparsi/mixed-interface-study','GITHUB_SHA':'fixture'})
        self.env.start();self.addCleanup(self.env.stop)
        image = {'Id':self.image,'Os':'linux','Architecture':'amd64','Config':{'User':'65532:65532','Entrypoint':['/study-schema/probe']}}
        self.check = patch('run_seatsurfing_schema_probe_v1.subprocess.check_output',side_effect=[b'',json.dumps([image]).encode()])
        self.check.start();self.addCleanup(self.check.stop)

    def test_compile_keeps_original_module_and_disables_dependency_network(self):
        recipe = schema_dockerfile('gcr.io/distroless/base-debian13@sha256:' + 'b'*64)
        self.assertIn('FROM study-seatsurfing-server-builder:qualification-v1 AS schema-builder',recipe)
        self.assertIn('RUN --network=none',recipe)
        self.assertIn('go build -mod=readonly',recipe)
        self.assertNotIn('go get',recipe)
        with self.assertRaises(AssertionError): schema_dockerfile('unverified:latest')

    def test_execution_uses_isolated_read_only_image_and_retains_container(self):
        command = schema_command(self.image)
        self.assertEqual(command[command.index('--network')+1],'none')
        self.assertIn('--read-only',command)
        self.assertNotIn('--rm',command)
        self.assertEqual(command[-1],self.image)

    def test_original_response_retained_without_handler_claim(self):
        value={'baseline':'original_request_decode_and_tag_validation','schema_type':'router.CreateLocationRequest','handler_invoked_by_probe':False,'accepted':True,'decoded_model':{'name':'fixture'}}
        with patch('run_seatsurfing_schema_probe_v1.subprocess.run',return_value=subprocess.CompletedProcess([],0,json.dumps(value).encode(),b'')) as run:
            result=run_schema_probe(self.report,b'{"name":"fixture"}',self.root/'result.json')
        self.assertEqual(result['status'],'original_schema_observed')
        self.assertFalse(result['handler_or_persistence_qualified'])
        self.assertEqual(run.call_count,1)
        self.assertEqual(run.call_args.kwargs['input'],b'{"name":"fixture"}')
        self.assertEqual((self.root/'result.json').stat().st_mode & 0o777,0o600)

    def test_bad_output_is_instrument_failure_not_schema_rejection(self):
        with patch('run_seatsurfing_schema_probe_v1.subprocess.run',return_value=subprocess.CompletedProcess([],0,b'not-json',b'')):
            result=run_schema_probe(self.report,b'{}',self.root/'result.json')
        self.assertEqual(result['status'],'schema_instrument_failure')
        self.assertNotIn('result',result)

    def test_timeout_preserves_pending_status_without_retry(self):
        with patch('run_seatsurfing_schema_probe_v1.subprocess.run',side_effect=subprocess.TimeoutExpired(['docker'],20,output=b'partial')) as run:
            result=run_schema_probe(self.report,b'{}',self.root/'result.json')
        self.assertEqual(result['status'],'schema_observation_deadline')
        self.assertTrue(result['container_may_still_be_running'])
        self.assertEqual(result['stdout'],'partial')
        self.assertEqual(run.call_count,1)


if __name__=='__main__':unittest.main()
