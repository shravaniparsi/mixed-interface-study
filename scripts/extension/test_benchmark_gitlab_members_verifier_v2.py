"""Adversarial tooling checks; these are not application observations."""
import copy
import unittest
from verify_benchmark_gitlab_members_controls_v2 import FIELDS, INITIAL, FINAL, state_checks

class MembershipEvidenceTests(unittest.TestCase):
    def setUp(self):
        state=dict.fromkeys(FIELDS,None)
        state.update(name='llm_bulk_inference',path='llm_bulk_inference',path_with_namespace='byteblaze/llm_bulk_inference',visibility='private',empty_repo=True,owner_id=2330)
        self.row={'ordinary_control_passed':True,'actor':{'id':2330,'username':'byteblaze'},'preflight_project_absent':True,'api_requests':[{'method':'GET','path':'/api/v4/projects/byteblaze%2Fllm_bulk_inference','status':404}],'producer_state':state,'final_state':copy.deepcopy(state),'initial_members':copy.deepcopy(INITIAL),'final_members':copy.deepcopy(FINAL),'browser_cleanup_confirmed':True,'stage':'complete','scientific_cases_executed':0}
    def test_complete_state_evidence(self):
        self.assertTrue(all(state_checks(self.row).values()))
    def test_missing_evidence_cannot_qualify(self):
        for key in self.row:
            with self.subTest(key=key):
                row=copy.deepcopy(self.row);row.pop(key)
                self.assertFalse(all(state_checks(row).values()))
    def test_reported_success_cannot_override_wrong_role_or_extra_member(self):
        row=copy.deepcopy(self.row);row['final_members'][0]['access_level']=40
        self.assertFalse(state_checks(row)['final_members'])
        row=copy.deepcopy(self.row);row['final_members'].append({'id':999,'access_level':30})
        self.assertFalse(state_checks(row)['final_members'])
    def test_preservation_and_projection_are_required(self):
        row=copy.deepcopy(self.row);row['final_state']['visibility']='public'
        self.assertFalse(state_checks(row)['project_preserved'])
        row=copy.deepcopy(self.row)
        for key in ('producer_state','final_state'):row[key].pop('description')
        self.assertTrue(state_checks(row)['project_preserved'])
        self.assertFalse(state_checks(row)['projection_complete'])
    def test_failed_instrument_does_not_qualify(self):
        self.row['error_type']='TimeoutError'
        self.assertFalse(state_checks(self.row)['complete_stage'])
if __name__=='__main__':unittest.main()
