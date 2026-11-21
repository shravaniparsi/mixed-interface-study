import copy,json,pathlib,unittest
from matrix_check import verify,ROOT
class MatrixTests(unittest.TestCase):
 def setUp(self):self.m=json.loads((ROOT/'manifests/fresh-session-ordinary-matrix-v1.json').read_text())
 def test_complete(self):self.assertEqual(sum(x['branches'] for x in verify(self.m).values()),36)
 def test_missing_duplicate_or_stale_branch(self):
  for kind in ['missing','duplicate','stale','wrong_edit']:
   m=copy.deepcopy(self.m);s=m['systems'][0]
   if kind=='missing':s['branches'].pop()
   if kind=='duplicate':s['branches'][-1]=copy.deepcopy(s['branches'][0])
   if kind=='stale':s['branches'][0]['fresh_browser_context']=False
   if kind=='wrong_edit':s['branches'][0]['unrelated']=s['branches'][0]['target']
   with self.subTest(kind=kind),self.assertRaises(ValueError):verify(m)
 def test_defect_inputs_refused(self):
  for kind in ['producer','null','omitted']:
   m=copy.deepcopy(self.m);s=m['systems'][0]
   if kind=='producer':s['producer_order']=['ordinary','title_null']
   if kind=='null':s['api']['destination']=None
   if kind=='omitted':del s['api']['destination']
   with self.subTest(kind=kind),self.assertRaises((ValueError,KeyError)):verify(m)
if __name__=='__main__':unittest.main()
