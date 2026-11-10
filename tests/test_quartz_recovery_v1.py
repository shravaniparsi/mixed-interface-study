from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from quartz_recovery_preflight_v1 import PREPARATION,FREEZE,read,units
from prepare_quartz_recovery_v1 import derive
from verify_quartz_recovery_release_v1 import preparation_verified,ci_accepted
class RecoveryTests(unittest.TestCase):
    def test_absent_release_prevents_dispatch(self):
        import tempfile
        from unittest.mock import patch
        import quartz_recovery_preflight_v1 as module
        with tempfile.TemporaryDirectory() as folder, patch.object(module,'FREEZE',Path(folder)/'absent.json'):
            with self.assertRaises(FileNotFoundError):module.units('initial')
    def test_exact_16_unstarted_cases_with_unchanged_runtime(self):
        prep=preparation_verified();self.assertEqual(len(prep['plan']['initial_batches']),16)
        originals={u['batch_id']:u for u in read(ROOT/'manifests/quartz-form-correction-preparation-v1.json')['plan']['initial_batches']}
        for u in prep['plan']['initial_batches']:
            old=originals[prep['original_case_links'][u['batch_id']]['original_batch_id']]
            self.assertNotEqual(u['batch_id'],old['batch_id'])
            self.assertEqual([j['runtime'] for j in u['jobs']],[j['runtime'] for j in old['jobs']])
    def test_started_unit_cannot_enter_recovery(self):
        old=read(ROOT/'manifests/quartz-form-correction-preparation-v1.json');v=read(ROOT/'manifests/quartz-correction-initial-attempt1-retention-v1.json')
        v['records'][v['unstarted_batch_ids'][0]]['steps_executed']=1
        with self.assertRaisesRegex(ValueError,'started unit'):derive(old,v)
    def test_failed_hosted_ci_cannot_release(self):
        with self.assertRaisesRegex(ValueError,'has not passed'):ci_accepted({'status':'completed','conclusion':'failure'},'commit')
    def test_other_source_ci_cannot_release(self):
        with self.assertRaisesRegex(ValueError,'source differs'):ci_accepted({'status':'completed','conclusion':'success','name':'Unit checks','head_sha':'old'},'current')
    def test_runtime_wrappers_change_only_context_names(self):
        for name in ('run_quartz_correction_unit_v1.py','validate_quartz_correction_unit_v1.py'):
            expected=(ROOT/'scripts'/name).read_text().replace('quartz_correction','quartz_recovery').replace('quartz-correction','quartz-recovery')
            self.assertEqual((ROOT/'scripts'/name.replace('quartz_correction','quartz_recovery')).read_text(),expected)
