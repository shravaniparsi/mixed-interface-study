"""Parent failure-path checks with no network, build or application execution."""
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock,patch
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts/extension'))
import qualify_nginx_ordinary_v1 as m

class QualificationParentTests(unittest.TestCase):
    def test_local_execution_rejected_before_any_command(self):
        with patch.dict(os.environ,{},clear=True),patch.object(m.subprocess,'check_output') as call:
            with self.assertRaisesRegex(ValueError,'hosted'):m.verify_registration()
            call.assert_not_called()
    def test_actions_rerun_rejected_before_build_or_registration_reads(self):
        env={'GITHUB_ACTIONS':'true','GITHUB_REPOSITORY':'shravaniparsi/mixed-interface-study','RUNNER_OS':'Linux','GITHUB_RUN_ATTEMPT':'2'}
        with patch.dict(os.environ,env,clear=True),patch.object(m.subprocess,'check_output') as call:
            with self.assertRaisesRegex(ValueError,'rerun'):m.verify_registration()
            call.assert_not_called()
    def test_first_provisioning_failure_stops_and_retains_public_summary_only(self):
        with tempfile.TemporaryDirectory() as temporary:
            root=Path(temporary)/'run';process=Mock();process.wait.return_value=1;process.poll.return_value=1
            def sealed(source,recipient,destination):
                self.assertTrue((source/'failure.json').is_file())
                destination.mkdir();(destination/'private-evidence.cms').write_bytes(b'synthetic-ciphertext-placeholder')
                return {'ciphertext_sha256':'synthetic-placeholder'}
            with patch.object(m,'verify_registration',return_value=({},'synthetic-commit')),patch.object(sys,'argv',['parent','--workspace',str(root)]),patch.object(m.subprocess,'Popen',return_value=process) as spawned,patch.object(m.subprocess,'run'),patch.object(m.subprocess,'check_output',return_value=''),patch.object(m,'seal',side_effect=sealed),patch.object(m,'provision_ordinary_scenarios') as scenarios:
                with self.assertRaises(SystemExit):m.main()
                self.assertEqual(spawned.call_count,1);scenarios.assert_not_called()
            report=json.loads((root/'public/qualification-result.json').read_text())
            self.assertEqual(report['failed_stage'],'browser_provisioning')
            self.assertEqual(report['scientific_cases'],0)
            self.assertTrue(report['application_and_browser_absent'])
            self.assertEqual({p.relative_to(root/'public').as_posix() for p in (root/'public').rglob('*') if p.is_file()},{'qualification-result.json','sealed/private-evidence.cms'})

if __name__=='__main__':unittest.main()
