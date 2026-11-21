import copy,unittest
from zipline_score import authentication,creation,digest,edit,readback_record

def seal(s):
 for t in s['tables'].values():t['row_sha256']=[digest(r) for r in t['rows']]
 return s

def fixture():
 return seal({'metadata':{'schema':'fixture'},'sequences':{},'files':[], 'tables':{'public.Url':{'rows':[{'id':'record','userId':'actor','destination':'https://example.com/api','updatedAt':'2026-11-20T00:00:00.000Z','vanity':'ordinary','discordComponentEmbed':{'accentColor':'#336699'}}]},'public.UserSession':{'rows':[]},'public.User':{'rows':[{'id':'actor','role':'ADMIN'}]}}})
class Scoring(unittest.TestCase):
 def setUp(self):
  self.before=fixture();self.after=copy.deepcopy(self.before);r=self.after['tables']['public.Url']['rows'][0];r['destination']='https://example.com/edited';r['updatedAt']='2026-11-20T00:00:01.000Z';seal(self.after)
  self.request=dict(method='PATCH',path='/api/user/urls/record',body={'destination':'https://example.com/edited'})
 def check(self,after):return edit(self.before,after,'record',{'/destination':'https://example.com/edited'},self.request)
 def test_valid_edit(self):self.assertTrue(self.check(self.after))
 def test_plausible_http_success_cannot_hide_bad_persistence(self):
  for kind in ['unchanged','wrong_record','unrelated_field','extra_write','schema','sequence','file','forged_digest']:
   a=copy.deepcopy(self.after);r=a['tables']['public.Url']['rows'][0]
   if kind=='unchanged':a=copy.deepcopy(self.before)
   elif kind=='wrong_record':r['id']='different'
   elif kind=='unrelated_field':r['vanity']='damaged'
   elif kind=='extra_write':a['tables']['public.Url']['rows'].append(copy.deepcopy(r))
   elif kind=='schema':a['metadata']['schema']='changed'
   elif kind=='sequence':a['sequences']['unrelated']=[{'last_value':'2'}]
   elif kind=='file':a['files'].append({'path':'unexpected','sha256':'abc'})
   elif kind=='forged_digest':r['destination']='wrong'
   if kind!='forged_digest':seal(a)
   with self.subTest(kind=kind),self.assertRaises(ValueError):self.check(a)
 def test_wrong_native_target(self):
  self.request['path']='/api/user/urls/other'
  with self.assertRaises(ValueError):self.check(self.after)
 def test_authentication_checks_specific_insert(self):
  a=copy.deepcopy(self.before);sid='x'*32
  a['tables']['public.UserSession']['rows'].append(dict(id=sid,createdAt='2026-11-20T00:00:01Z',ua='browser',client='web',device='desktop',oauthProvider=None,oidcIdToken=None,userId='actor'));seal(a)
  self.assertEqual(authentication(self.before,a,'actor',set()),sid)
  with self.assertRaises(ValueError):authentication(self.before,a,'actor',{sid})
  a['tables']['public.User']['rows'][0]['role']='USER';seal(a)
  with self.assertRaises(ValueError):authentication(self.before,a,'actor',set())
 def test_readback_only_allows_declared_projections(self):
  persisted=dict(id='record',password=None,createdAt='2026-11-20T00:00:00+00:00',updatedAt='2026-11-20T00:00:01+00:00',destination='https://example.com/api')
  observed={**persisted,'password':False,'createdAt':'2026-11-20T00:00:00.000Z','updatedAt':'2026-11-20T00:00:01.000Z'}
  readback_record(persisted,observed)
  for key,value in [('password',True),('updatedAt','2026-11-20T00:00:02Z'),('destination','https://example.com/other')]:
   with self.subTest(field=key),self.assertRaises(ValueError):readback_record(persisted,{**observed,key:value})
 def test_creation_requires_independent_row(self):
  b=fixture();b['tables']['public.Url']['rows']=[];seal(b)
  creation(b,self.before,'record','actor',{'destination':'https://example.com/api'})
  with self.assertRaises(ValueError):creation(b,b,'record','actor',{'destination':'https://example.com/api'})
if __name__=='__main__':unittest.main()
