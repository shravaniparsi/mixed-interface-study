import copy,importlib.util,pathlib,unittest
root=pathlib.Path(__file__).resolve().parents[2];spec=importlib.util.spec_from_file_location('score',root/'scripts/extension/verify_redesign_zipline_scientific_v1.py');score=importlib.util.module_from_spec(spec);spec.loader.exec_module(score)
class ScorerTests(unittest.TestCase):
 def setUp(self):
  self.row={'id':'native','destination':'native','updatedAt':'2026-01-01T00:00:00Z'}
  self.before={'tables':{'public.Url':{'rows':[self.row],'row_sha256':[score.digest(self.row)]},'public.User':{'rows':[{'role':'USER'}],'row_sha256':['original']}},'sequences':{'counter':1},'files':[]}
  self.after=copy.deepcopy(self.before);self.new={'id':'created','destination':'ordinary','updatedAt':'2026-01-01T00:00:00.07Z','discordComponentEmbed':{'accentColor':'#336699','content':'unchanged'}};self.after['tables']['public.Url']['rows'].insert(0,self.new)
 def test_creation_only(self):score.same_creation(self.before,self.after,'created')
 def test_collateral_creation_rejected(self):
  for mutation in [lambda x:x['sequences'].update(counter=2),lambda x:x['files'].append({'path':'new'}),lambda x:x['tables']['public.User']['rows'][0].update(role='ADMIN'),lambda x:x['tables']['public.Url']['rows'][1].update(destination='changed')]:
   value=copy.deepcopy(self.after);mutation(value)
   with self.assertRaises(AssertionError):score.same_creation(self.before,value,'created')
 def test_duplicate_record_rejected(self):
  self.after['tables']['public.Url']['rows'].append(copy.deepcopy(self.new))
  with self.assertRaises(AssertionError):score.same_creation(self.before,self.after,'created')
 def test_nested_edit_and_collateral_detection(self):
  b=copy.deepcopy(self.after);b['tables']['public.Url']['row_sha256']=[score.digest(r) for r in b['tables']['public.Url']['rows']];a=copy.deepcopy(b);a['tables']['public.Url']['rows'][0]['discordComponentEmbed']['accentColor']='#669933';changes={'/discordComponentEmbed/accentColor':'#669933'}
  self.assertTrue(score.correct_frame(b,a,'created',changes));a['tables']['public.Url']['rows'][0]['discordComponentEmbed']['content']=None;self.assertFalse(score.correct_frame(b,a,'created',changes))
if __name__=='__main__':unittest.main()
