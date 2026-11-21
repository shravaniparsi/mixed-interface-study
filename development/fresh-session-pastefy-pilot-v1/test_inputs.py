import copy,unittest
from freeze_inputs import cases,validator
class PilotInputs(unittest.TestCase):
 def test_registered_schema_boundary(self):
  rows=cases()['cases'];self.assertEqual([r['id'] for r in rows],['ordinary-content','ordinary-title','content-omit','content-null','title-omit','title-null'])
  self.assertEqual([r['schema_prediction']['valid'] for r in rows],[True,True,False,False,True,False])
 def test_single_mutation_and_unrelated_continuation(self):
  rows=cases()['cases'];ordinary=rows[0]['input']
  for r in rows[2:]:
   self.assertNotEqual(r['target'],r['continuation']['field'])
   self.assertEqual({k:v for k,v in r['input'].items() if k!=r['target']},{k:v for k,v in ordinary.items() if k!=r['target']})
   self.assertEqual(r['repair'],{r['target']:ordinary[r['target']]});self.assertEqual(r['sham'],{})
 def test_original_ref_and_nullable_rules_are_executed(self):
  payload=copy.deepcopy(cases()['cases'][0]['input']);payload['visibility']='NOT_A_VISIBILITY'
  self.assertTrue(list(validator().iter_errors(payload)))
  payload['visibility']='UNLISTED';payload['title']=None
  self.assertTrue(list(validator().iter_errors(payload)))
