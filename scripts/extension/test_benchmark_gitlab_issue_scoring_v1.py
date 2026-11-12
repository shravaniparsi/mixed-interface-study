"""Adversarial synthetic checks; these are not application experiments."""
import copy
import unittest
from score_benchmark_gitlab_issue_v1 import classify_triple,semantic_pass,TITLE

def clean():
    before={'project_id':183,'title':TITLE,'description':'Café 東京','confidential':False,'issue_type':'issue','state':'opened','labels':[],'milestone_id':None,'assignee_ids':[],'due_date':None}
    return {'actor':{'id':2330,'username':'byteblaze'},'optional_field_patch':{'description':'Café 東京'},'producer_state':before,'final_state':dict(before,assignee_ids=[2264],due_date='2033-04-01'),'case_passed':True,'browser_cleanup_confirmed':True,'preflight':{'exact_title_count':0,'may_be_truncated':False},'assignee_membership_setup':'added_developer','native_writes':[],'stage':'complete'}
def triple():return {b:copy.deepcopy(clean()) for b in ('native_native','api_native','api_api')}
class ScoringTests(unittest.TestCase):
    def test_clean(self):self.assertEqual(classify_triple(triple(),True)['classification'],'all_paths_preserve')
    def test_silent_title_damage_despite_reported_success(self):
        rows=triple();rows['api_native']['final_state']['title']='damaged'
        self.assertFalse(semantic_pass(rows['api_native']))
        self.assertTrue(classify_triple(rows,True)['candidate_incremental_signal'])
    def test_api_preservation_check_receives_credit(self):
        rows=triple()
        for b in ('api_api','api_native'):rows[b]['final_state']['title']='damaged'
        self.assertFalse(classify_triple(rows,True)['candidate_incremental_signal'])
    def test_state_mismatch_blocks_incremental_claim(self):
        rows=triple();rows['native_native']['producer_state']['confidential']=True;rows['api_native']['final_state']['title']='damaged'
        self.assertEqual(classify_triple(rows,True)['classification'],'producer_state_mismatch')
    def test_timeout_is_not_application_defect(self):
        rows=triple();del rows['api_native']['final_state'];rows['api_native']['case_passed']=False;rows['api_native']['stage']='continuation'
        self.assertFalse(classify_triple(rows,True)['candidate_incremental_signal'])
    def test_control_failure_blocks_claim(self):
        rows=triple();rows['api_native']['final_state']['title']='damaged'
        self.assertEqual(classify_triple(rows,False)['classification'],'unqualified_batch_controls')
    def test_missing_branch_is_not_clean(self):
        rows=triple();rows['api_api']=None
        self.assertEqual(classify_triple(rows,True)['classification'],'incomplete_triple')
    def test_reused_state_not_clean(self):
        rows=triple();rows['api_native']['preflight']['exact_title_count']=1
        self.assertNotEqual(classify_triple(rows,True)['classification'],'all_paths_preserve')
if __name__=='__main__':unittest.main()
