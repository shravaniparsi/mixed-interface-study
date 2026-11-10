"""Catch mismatched workflow entry points before any application work starts."""
import sys,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from verify_quartz_recovery_dispatch_v3 import failure_verified
class DispatchTests(unittest.TestCase):
    def test_all_runtime_entry_points_use_released_v2_context(self):
        text=(ROOT/'.github/workflows/quartz_recovery_dispatch_v3.yml').read_text()
        for stem in ('quartz_recovery_matrix','run_quartz_recovery_unit','validate_quartz_recovery_unit'):
            self.assertIn(stem+'_v2.py',text)
            self.assertNotIn(stem+'_v1.py',text)
        self.assertEqual(text.count('python scripts/verify_quartz_recovery_dispatch_v3.py'),2)
        self.assertIn('$CI_ARTIFACT_DIR/quartz-recovery-unit-v2',text)
    def test_provider_proves_no_application_execution(self):
        self.assertEqual(len(failure_verified()),3)
if __name__=='__main__':unittest.main()
