"""Deployment status must never be mistaken for scientific qualification."""
import importlib.util,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('screen',ROOT/'scripts/extension/deployment_screen_v1.py')
screen=importlib.util.module_from_spec(spec);spec.loader.exec_module(screen)

class DeploymentScreenTests(unittest.TestCase):
    def test_pull_failure_is_retained_without_claiming_case_results(self):
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'evidence'
            def failed(args,**kwargs):return subprocess.CompletedProcess(args,1,'simulated image unavailable')
            with patch.object(sys,'argv',['screen','--app','memos','--output',str(out)]),patch.object(screen.subprocess,'run',side_effect=failed),patch.object(screen.signal,'signal'),patch.object(screen.platform,'platform',return_value='test-host'):
                self.assertEqual(screen.main(),1)
            report=json.loads((out/'report.json').read_text())
            self.assertEqual(report['status'],'incomplete')
            self.assertFalse(report['case_outcomes_observed'])
            self.assertIn('commands.json',report['files_sha256'])
            self.assertEqual(report['images'],{})

    def test_six_registered_subjects_not_outcome_filtered(self):
        v=json.loads(screen.REGISTRY.read_text())
        self.assertEqual({x['id'] for x in v['applications']},{'linkding','vikunja','memos','gitea','paperless','grocy'})
        self.assertFalse(v['case_execution_authorized'])
        self.assertEqual(v['maximum_screen_attempts_per_app'],2)
        self.assertTrue(all(len(x['commit'])==40 for x in v['applications']))

if __name__=='__main__':unittest.main()
