"""Adversarial checks of ordinary README evidence, not scientific observations."""
import unittest
from verify_benchmark_gitlab_readme_controls_v2 import state_checks,path_checks,matched_business_states,FIELDS,EXPECTED

def valid():
 before={k:False for k in FIELDS};before.update(name='nolan_young_fans',path='nolan_young_fans',path_with_namespace='byteblaze/nolan_young_fans',visibility='private',empty_repo=True,default_branch='main',description=None,owner_id=2330)
 after=dict(before,empty_repo=False,default_branch='main')
 return dict(ordinary_control_passed=True,actor={'id':2330,'username':'byteblaze'},preflight_project_absent=True,api_requests=[{'method':'GET','path':'/api/v4/projects/byteblaze%2Fnolan_young_fans','status':404}],producer_state=before,final_state=after,final_file={'path':'README.md','content':EXPECTED,'commit_id':'a'*40},final_tree=[{'path':'README.md','type':'blob','mode':'100644'}],final_branches=[{'name':'main','default':True}],final_commits=[{'id':'a'*40,'parent_ids':[],'message':'Add Nolan film README'}],browser_cleanup_confirmed=True,stage='complete',scientific_cases_executed=0)
class Checks(unittest.TestCase):
 def test_complete_row(self):self.assertTrue(all(state_checks(valid()).values()))
 def test_wrong_contents_fail_even_with_success_flag(self):
  r=valid();r['final_file']['content']+='- Oppenheimer\n';self.assertFalse(state_checks(r)['exact_readme'])
 def test_unrelated_project_change(self):
  r=valid();r['final_state']['visibility']='public';self.assertFalse(state_checks(r)['project_preserved'])
 def test_extra_file(self):
  r=valid();r['final_tree'].append({'path':'extra','type':'blob','mode':'100644'});self.assertFalse(state_checks(r)['exact_tree'])
 def test_existing_commit(self):
  r=valid();r['final_commits'][0]['parent_ids']=['b'*40];self.assertFalse(state_checks(r)['one_root_commit'])
 def test_unbound_readback(self):
  r=valid();r['final_file']['commit_id']='b'*40;self.assertFalse(state_checks(r)['commit_binding'])
 def test_missing_projection(self):
  r=valid();del r['producer_state']['lfs_enabled'];self.assertFalse(state_checks(r)['projection_complete'])
 def test_false_report_alone_insufficient(self):
  r=valid();del r['final_file'];self.assertFalse(all(state_checks(r).values()))
class Paths(unittest.TestCase):
 def native(self):
  return {'project_id':194,'api_requests':[],'native_writes':[{'method':'POST','path':'/projects','status':302},{'method':'POST','path':'/api/v4/projects/194/repository/commits','status':201}]}
 def test_native_path(self):self.assertTrue(all(path_checks(self.native(),'native_native').values()))
 def test_wrong_target(self):
  r=self.native();r['native_writes'][1]['path']='/api/v4/projects/195/repository/commits';self.assertFalse(path_checks(r,'native_native')['assigned_native_repository_writes'])
 def test_duplicate_commit(self):
  r=self.native();r['native_writes'].append(dict(r['native_writes'][1]));self.assertFalse(path_checks(r,'native_native')['assigned_native_repository_writes'])
 def test_api_fallback_disallowed(self):
  r=self.native();r['api_requests']=[{'method':'POST','path':'/api/v4/projects/194/repository/files/README.md','status':201}];self.assertFalse(path_checks(r,'native_native')['assigned_api_writes'])
 def test_unrecorded_api_baseline(self):self.assertFalse(all(path_checks({'project_id':194},'api_api').values()))
class Matching(unittest.TestCase):
 def test_exact_three_way_match(self):self.assertTrue(matched_business_states([valid(),valid(),valid()]))
 def test_null_empty_mismatch_is_not_normalized(self):
  rows=[valid(),valid(),valid()];rows[1]['producer_state']['description']='';rows[1]['final_state']['description']='';self.assertFalse(matched_business_states(rows))
 def test_missing_branch(self):self.assertFalse(matched_business_states([valid(),valid()]))
 def test_omitted_description_api_payload(self):
  r={'project_id':194,'api_requests':[{'method':'POST','path':'/api/v4/projects','body':{'name':'nolan_young_fans','path':'nolan_young_fans','visibility':'private','initialize_with_readme':False},'status':201}],'native_writes':[{'method':'POST','path':'/api/v4/projects/194/repository/commits','status':201}]}
  self.assertTrue(all(path_checks(r,'api_native').values()))
  r['api_requests'][0]['body']['description']='';self.assertFalse(path_checks(r,'api_native')['assigned_api_writes'])
if __name__=='__main__':unittest.main()
