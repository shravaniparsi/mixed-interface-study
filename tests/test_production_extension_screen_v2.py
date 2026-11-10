"""The second screen retains failures and never persists process-only secrets."""
import importlib.util,json,subprocess,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
spec=importlib.util.spec_from_file_location('screen2',ROOT/'scripts/extension/deployment_screen_v2.py');screen=importlib.util.module_from_spec(spec);spec.loader.exec_module(screen)
class SecondScreenTests(unittest.TestCase):
    def test_ephemeral_value_is_redacted_even_in_failure_output(self):
        marker='unit-test-redaction-marker'
        with tempfile.TemporaryDirectory() as tmp:
            out=Path(tmp)/'evidence'
            def failed(args,**kwargs):return subprocess.CompletedProcess(args,1,'failure '+marker)
            with patch.object(sys,'argv',['screen','--app','paperless','--output',str(out)]),patch.object(screen.subprocess,'run',side_effect=failed),patch.object(screen.secrets,'token_urlsafe',return_value=marker),patch.object(screen.signal,'signal'),patch.object(screen.platform,'platform',return_value='test-host'):
                self.assertEqual(screen.main(),1)
            self.assertNotIn(marker,''.join(p.read_text() for p in out.iterdir()))
            self.assertIn('[ephemeral-value-redacted]',(out/'commands.json').read_text())
    def test_only_failed_apps_enter_second_attempt(self):
        registry=json.loads(screen.REGISTRY.read_text())
        self.assertEqual({a['id'] for a in registry['applications']},{'vikunja','paperless','grocy'})
        for app in registry['applications']:
            self.assertEqual(json.loads((ROOT/app['prior_failure_report']).read_text())['status'],'incomplete')
            self.assertTrue('@sha256:' in app['image'])
if __name__=='__main__':unittest.main()
