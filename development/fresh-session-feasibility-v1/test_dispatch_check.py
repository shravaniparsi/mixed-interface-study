import copy,datetime,unittest
from dispatch_check import validate
class DispatchGuard(unittest.TestCase):
 def setUp(self):
  self.study={'ready_for_application_dispatch':True,'gates':{'G1_build_chain_audit':'passed','G2_both_adapters_observers_scorers':'passed'},'preparation_deadline_utc':'2026-11-23T03:23:28Z'}
  self.plan={'status':'reviewed','publication_status':'authorized_sanitized_public_logs','authorized_systems':['shlink'],'max_workflow_attempts':3,'max_runner_minutes':180,'previous_runs':{},'sha256':{'fixture':'hash'}}
  self.history=[dict(id=1,run_attempt=1,display_title='Fresh-session feasibility / shlink',status='in_progress',conclusion=None)]
  self.now=datetime.datetime(2026,11,21,tzinfo=datetime.timezone.utc)
 def test_initial_registered_run(self):self.assertTrue(validate(self.study,self.plan,'shlink',self.history,1,self.now))
 def test_missing_review_wrong_target_retry_and_budget_refused(self):
  for fault in ['review','publication','target','retry','unknown_prior','deadline','budget']:
   study=copy.deepcopy(self.study);plan=copy.deepcopy(self.plan);history=copy.deepcopy(self.history);now=self.now
   if fault=='review':study['ready_for_application_dispatch']=False
   elif fault=='publication':plan['publication_status']='pending'
   elif fault=='target':plan['authorized_systems']=['zipline']
   elif fault=='retry':history[0]['run_attempt']=2
   elif fault=='unknown_prior':history.append(dict(id=2,run_attempt=1))
   elif fault=='deadline':now=datetime.datetime(2026,11,24,tzinfo=datetime.timezone.utc)
   elif fault=='budget':history[0]['run_attempt']=4
   with self.subTest(fault=fault),self.assertRaises(ValueError):validate(study,plan,'shlink',history,1,now)
if __name__=='__main__':unittest.main()
