"""Synthetic rejection-evidence checks; not application observations."""
import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
import validate_petclinic_integrity as v

def fixture():
 case={'id':'owner_omit_firstName','prefix_status':400}
 registered=next(c for c in v.read(v.ROOT/'manifests/petclinic-candidates-v1.json')['candidates'] if c['id']==case['id'])
 graph=[{'id':1,'pets':[]}];command={'method':'POST','path':'/owners','payload':registered['payload']}
 trace=[{'source':'direct_api','phase':'pre_candidate_state','method':'GET','path':'/owners','status':200,'response':copy.deepcopy(graph)},
        {'source':'direct_api','phase':'candidate_prefix','method':'POST','path':'/owners','request':registered['payload'],'status':400,'response':{}},
        {'source':'direct_api','phase':'post_prefix_state','method':'GET','path':'/owners','status':200,'response':copy.deepcopy(graph)}]
 r={'template':'owner_address_edit','oracle':'api_semantic','prefix_status':400,'backend_cleanup':{'confirmed':True},'page_errors':[],
    'status':'prefix_rejected','continuation_reachable':False,'post_prefix_graph':copy.deepcopy(graph),'trace':trace,
    'capture_integrity':{'errors':[],'contexts':[]},'integrity':{'version':1,'guards':[
     {'name':'pre_candidate_state_readable','expected':True,'observed':True,'passed':True},
     {'name':'candidate_prefix_command','expected':command,'observed':copy.deepcopy(command),'passed':True}],
     'before':{'readable':True,'data':copy.deepcopy(graph)},'rejection':{'status':'unchanged','after':{'readable':True,'data':copy.deepcopy(graph)}}}}
 return r,case

class PetClinicIntegrityTests(unittest.TestCase):
 def test_complete_rejection_record(self):
  r,c=fixture();self.assertEqual(v.validate_case(r,c)['rejection_state'],'unchanged')
 def test_count_preserving_mutation_is_not_unchanged(self):
  r,c=fixture();r['integrity']['rejection']['after']['data'][0]['city']='changed'
  with self.assertRaises(ValueError):v.validate_case(r,c)
 def test_forged_guard_verdict_is_rejected(self):
  r,c=fixture();r['integrity']['guards'][1]['observed']['path']='/owners/99'
  with self.assertRaises(ValueError):v.validate_case(r,c)
 def test_missing_guard_is_rejected(self):
  r,c=fixture();r['integrity']['guards'].pop()
  with self.assertRaises(ValueError):v.validate_case(r,c)
 def test_snapshot_must_match_raw_trace(self):
  r,c=fixture();r['trace'][0]['response']=[]
  with self.assertRaises(ValueError):v.validate_case(r,c)
 def test_backend_exit_must_be_confirmed(self):
  r,c=fixture();r['backend_cleanup']['confirmed']=False
  with self.assertRaises(ValueError):v.validate_case(r,c)
 def test_server_error_is_not_the_declared_400_control(self):
  r,c=fixture();r['prefix_status']=500
  with self.assertRaises(ValueError):v.validate_case(r,c)
 def test_continuation_write_after_rejection_is_rejected(self):
  r,c=fixture();r['trace'].append({'method':'PUT'})
  with self.assertRaises(ValueError):v.validate_case(r,c)
