"""Adversarial outcome checks using archived ordinary controls as valid fixtures."""
import copy,json,unittest
from pathlib import Path
from score_benchmark_gitlab_readme_v1 import classify,qualified,BRANCHES,ROOT

def good(branch):
 p=ROOT/f'results/benchmark-gitlab-readme-controls-v2-ci-44030229250/gitlab-readme-control-v2-{branch}-44030229250/readme-control.json'
 r=json.loads(p.read_text());r.update(case_passed=True,optional_field_patch={},scientific_cases_executed=1)
 r['producer_repository']={'project':copy.deepcopy(r['producer_state']),'file':None}
 r['final_repository']={'project':copy.deepcopy(r['final_state']),'file':copy.deepcopy(r['final_file'])}
 return r

def triple():return {b:good(b) for b in BRANCHES}
class Scorer(unittest.TestCase):
 def test_ordinary_all_preserve(self):self.assertEqual(classify(triple(),True)['classification'],'all_paths_preserve')
 def test_no_controls_no_signal(self):self.assertFalse(classify(triple(),False)['candidate_incremental_signal'])
 def test_missing_branch(self):
  r=triple();r['api_api']=None;self.assertEqual(classify(r,True)['classification'],'incomplete_triple')
 def test_wrong_contents_override_pass_flag(self):
  r=good('api_api');r['final_file']['content']='wrong';self.assertFalse(qualified(r))
 def test_explicit_description_payload_checked(self):
  r=good('api_api');r['optional_field_patch']={'description':'x'};self.assertFalse(qualified(r))
 def test_native_unrepresentable_retained(self):
  r=triple();n=r['native_native'];n.update(native_representability='unsupported_explicit_description',native_description_field_count=0,scientific_cases_executed=0,case_passed=False,optional_field_patch={'description':'x'},native_writes=[]);del n['producer_state'];self.assertEqual(classify(r,True)['classification'],'native_input_not_representable')
 def test_fake_exclusion_after_production_fails(self):
  r=triple();r['native_native'].update(native_representability='unsupported_explicit_description',native_description_field_count=0);self.assertEqual(classify(r,True)['classification'],'invalid_representability_evidence')
 def test_lifecycle_not_incremental(self):
  r=triple()
  for x in r.values():x['optional_field_patch']={'initialize_with_readme':True}
  v=classify(r,True);self.assertEqual(v['classification'],'lifecycle_control_requires_separate_interpretation');self.assertFalse(v['candidate_incremental_signal'])
 def test_null_empty_mismatch(self):
  r=triple();r['api_native']['producer_state']['description']='';self.assertEqual(classify(r,True)['classification'],'producer_state_mismatch')
 def test_timeout_without_changed_state_not_signal(self):
  r=triple();n=r['api_native'];n.update(case_passed=False,stage='continuation',native_writes=[],failure_repository={'project':copy.deepcopy(n['producer_state']),'file':None});del n['final_state'];self.assertFalse(classify(r,True)['candidate_incremental_signal'])
 def test_bound_commit_rejection_candidate_not_confirmed(self):
  r=triple();n=r['api_native'];n.update(case_passed=False,stage='continuation',native_writes=[{'method':'POST','path':f"/api/v4/projects/{n['project_id']}/repository/commits",'status':400}]);v=classify(r,True);self.assertTrue(v['candidate_incremental_signal']);self.assertFalse(v['confirmed_natural_defect'])
 def test_external_or_wrong_project_error_not_signal(self):
  r=triple();n=r['api_native'];n.update(case_passed=False,stage='continuation',native_writes=[{'method':'POST','path':'/api/v4/projects/9999/repository/commits','status':400}]);self.assertFalse(classify(r,True)['candidate_incremental_signal'])
 def test_shared_api_failure_blocks_signal(self):
  r=triple();r['api_native'].update(case_passed=False,stage='continuation',native_writes=[{'method':'POST','path':'/api/v4/projects/194/repository/commits','status':400}]);r['api_api']['case_passed']=False;self.assertFalse(classify(r,True)['candidate_incremental_signal'])
 def test_partial_final_snapshot_fails_without_crash(self):
  r=good('api_api');r['final_repository']['file']=None;self.assertFalse(qualified(r))
if __name__=='__main__':unittest.main()
