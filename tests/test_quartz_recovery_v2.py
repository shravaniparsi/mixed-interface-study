"""Public-host recovery keeps frozen execution semantics and release gates."""
import re,sys,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from primary_preflight_v1 import read,environment
from verify_quartz_recovery_release_v2 import ci_accepted

class PublicRecoveryTests(unittest.TestCase):
    def test_execution_wrappers_change_only_context(self):
        for prefix in ('run','validate'):
            old=(ROOT/f'scripts/{prefix}_quartz_recovery_unit_v1.py').read_text()
            expected=old.replace('quartz_recovery_preflight_v1','quartz_recovery_preflight_v2').replace('quartz-recovery-unit-v1','quartz-recovery-unit-v2')
            self.assertEqual((ROOT/f'scripts/{prefix}_quartz_recovery_unit_v2.py').read_text(),expected)

    def test_old_two_core_environment_is_rejected(self):
        prep=read(ROOT/'manifests/quartz-public-qualification-preparation-v1.json')
        old=read(ROOT/'manifests/quartz-correction-smoke-runtime-v1.json')
        folder=next((ROOT/old['archive_root']).glob('*/quartz-correction-unit-v1'))
        versions=read(folder/'runtime-versions.json')
        with self.assertRaisesRegex(ValueError,'Machine class'):
            environment(prep,'quartz',versions,read(folder/'browser.json'),read(folder/'quartz-bootstrap.json'))
        versions['logical_cpus']=4
        environment(prep,'quartz',versions,read(folder/'browser.json'),read(folder/'quartz-bootstrap.json'))

    def test_failed_ci_cannot_release(self):
        with self.assertRaisesRegex(ValueError,'has not passed'):
            ci_accepted({'status':'completed','conclusion':'failure'},'commit')

    def test_absent_release_prevents_dispatch(self):
        import quartz_recovery_preflight_v2 as module
        prep=read(ROOT/'manifests/quartz-recovery-preparation-v1.json')
        with tempfile.TemporaryDirectory() as folder:
            path=Path(folder)/'prep.json';path.write_text(__import__('json').dumps(prep))
            with patch.object(module,'PREPARATION',path),patch.object(module,'FREEZE',Path(folder)/'absent.json'):
                with self.assertRaises(FileNotFoundError):module.units('initial')

if __name__=='__main__':unittest.main()
