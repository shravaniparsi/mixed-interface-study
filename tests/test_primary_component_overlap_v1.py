"""Shared observations never become channel-exclusive continuation credit."""
from pathlib import Path
from copy import deepcopy
import sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from mixed_interface.common_execution_v1 import read
from analyze_primary_units_v1 import component_overlap

class ComponentOverlapTests(unittest.TestCase):
    def fixture(self):return {'runtime_result':read(ROOT/'results/realworld-expanded-integration-ci-20261109/initial-000/observations.json')}
    def test_clean_and_shared_only_mismatches_have_no_exclusive_assigned_credit(self):
        v=self.fixture();self.assertEqual(component_overlap(v)['category'],'neither_assigned_mismatch')
        # Synthetic attribution-only fixture; never emitted as application evidence.
        r=v['runtime_result'];r['terminal']['kind']='completed_mismatch';r['terminal']['outcome']['check_failure']=True
        r['branches']['ui']['components']['components']['shared_final_native_read']['mismatch_observed']=True
        self.assertEqual(component_overlap(v)['category'],'neither_assigned_mismatch')
    def test_unavailable_comparison_and_unknown_policy_remain_unresolved(self):
        v=self.fixture();v['runtime_result']['branches']['ui']['components']['components']['assigned_native_continuation']['comparison_eligible']=False
        self.assertEqual(component_overlap(v)['category'],'not_comparison_eligible')
        v=self.fixture();v['runtime_result']['terminal']['kind']='unresolved_policy'
        self.assertEqual(component_overlap(v)['category'],'unresolved')
    def test_actual_rejection_does_not_receive_continuation_credit(self):
        v={'runtime_result':read(ROOT/'results/petclinic-timing-ci-20261110/petclinic-timing-v1/cost-001/observations.json')}
        self.assertEqual(component_overlap(v)['category'],'prefix_rejected')
