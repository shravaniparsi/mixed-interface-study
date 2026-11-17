"""Adversarial checks of ordinary README evidence, not scientific observations."""
import copy, unittest
from verify_benchmark_gitlab_readme_controls_v1 import state_checks,FIELDS,EXPECTED

def valid():
 before={k:False for k in FIELDS};before.update(name='nolan_young_fans',path='nolan_young_fans',path_with_namespace='byteblaze/nolan_young_fans',visibility='private',empty_repo=True,default_branch=None,description='',owner_id=2330)
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
if __name__=='__main__':unittest.main()
