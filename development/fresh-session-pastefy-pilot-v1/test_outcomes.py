import copy,json,pathlib,tempfile,unittest
from outcomes import producer,continuation
import test_score_controls
from score_controls import ROOT
class Outcomes(unittest.TestCase):
 def setUp(self):
  self.temp=tempfile.TemporaryDirectory();self.p=pathlib.Path(self.temp.name);self.r=test_score_controls.WholeControlGate().fixture(self.p)['cases'][0];self.c=json.loads((ROOT/'manifests/fresh-session-pastefy-pilot-inputs-v1.json').read_text())['cases'][0]
 def tearDown(self):self.temp.cleanup()
 def read(self,name):return json.loads((self.p/name).read_text())
 def test_ordinary_creation_and_collateral_creation_effect(self):
  before=self.read(self.r['producer_before']);after=self.read(self.r['produced']);self.assertTrue(producer(self.c,self.r,before,after)['qualified']);after['files']['unexpected']={};self.assertFalse(producer(self.c,self.r,before,after)['qualified'])
 def test_rejection_is_not_success_and_500_is_not_validation(self):
  before=self.read(self.r['producer_before']);r=copy.deepcopy(self.r);r['producer'].update(status=400,body={'success':False});self.assertEqual(producer(self.c,r,before,before)['outcome'],'producer_rejected');r['producer'].update(status=500,body='error');self.assertEqual(producer(self.c,r,before,before)['outcome'],'producer_error_or_unconfirmed')
 def test_exact_continuation(self):
  b=self.r['branches'][0];result=continuation(self.read(b['intervened']),self.read(b['after']),self.read(b['browser']),self.r['key'],self.r['actor']['user_id'],self.c['continuation'],b['readback']);self.assertEqual(result['outcome'],'exact_intended_edit')
 def test_timeout_is_never_positive_block(self):
  before=self.read(self.r['produced']);n={'status':'unavailable','error':'TimeoutError','receipts':[]};result=continuation(before,before,n,'abcdefgh','study001',self.c['continuation'],{});self.assertFalse(result['available']);self.assertEqual(result['outcome'],'unavailable')
 def test_positive_block_requires_observed_control_and_no_effect(self):
  before=self.read(self.r['produced']);n={'status':'positive_client_blocking','control':{'disabled':True},'receipts':[]};self.assertEqual(continuation(before,before,n,'abcdefgh','study001',self.c['continuation'],{})['outcome'],'positive_client_blocking');after=copy.deepcopy(before);after['files']['changed']={};self.assertFalse(continuation(before,after,n,'abcdefgh','study001',self.c['continuation'],{})['available'])
 def test_runtime_error_is_distinct_from_validation(self):
  before=self.read(self.r['produced']);n={'status':'client_runtime_error','pageErrors':['TypeError'],'receipts':[]};self.assertEqual(continuation(before,before,n,'abcdefgh','study001',self.c['continuation'],{})['outcome'],'client_runtime_error')
