"""Fabricated evidence only: test complete scoring and refusal of plausible false passes."""
import copy,json,pathlib,tempfile,unittest
from matrix_check import ROOT
from zipline_score import digest,put,score

def sealed(value):
 value=copy.deepcopy(value)
 for table in value['tables'].values():table['row_sha256']=[digest(r) for r in table['rows']]
 return value

def evidence():
 matrix=json.loads((ROOT/'manifests/fresh-session-ordinary-matrix-v1.json').read_text());plan=matrix['systems'][0];docs={};trace=[]
 base=sealed(dict(metadata={'schema':'synthetic'},tables={'public.Url':{'rows':[]},'public.UserSession':{'rows':[]},'public.User':{'rows':[{'id':'actor','role':'ADMIN'}]}},sequences={},files=[]))
 native={**copy.deepcopy(plan['native']),'id':'native','userId':'actor','updatedAt':'2026-11-20T00:00:00Z','password':None}
 api={**copy.deepcopy(plan['api']),'id':'api','userId':'actor','updatedAt':'2026-11-20T00:00:00Z','password':None}
 docs['native-before.json']=base;native_state=copy.deepcopy(base);native_state['tables']['public.Url']['rows']=[native];native_state=sealed(native_state)
 docs['native-after.json']=native_state;docs['native-create-response.json']={'status':201,'record':native};docs['api-before.json']=native_state
 root=copy.deepcopy(native_state);root['tables']['public.Url']['rows'].append(api);root=sealed(root)
 for name in ['root-state','api-after','root-backup-verified']:docs[name+'.json']=root
 docs['api-create-response.json']=api
 docs['result.json']=dict(status='controls_completed',cleanup_complete=True,record_id='api',actor_id='actor',actor_role='ADMIN')
 docs['response-capture.json']=[{'capture':{'status':'complete'}}]
 counter=0
 def restored(label):
  nonlocal counter
  counter+=1;after=copy.deepcopy(root);after['tables']['public.UserSession']['rows'].append(dict(id=str(counter).zfill(32),createdAt='2026-11-20T00:00:01Z',ua='browser',client='web',device='desktop',oauthProvider=None,oidcIdToken=None,userId='actor'));after=sealed(after)
  docs[label+'-restored.json']=root;docs[label+'-loaded.json']=after
  return after
 def edited(label,before,changes):
  after=copy.deepcopy(before);r=next(r for r in after['tables']['public.Url']['rows'] if r['id']=='api');body=copy.deepcopy(r)
  for pointer,value in changes.items():put(r,pointer,value);put(body,pointer,value)
  r['updatedAt']='2026-11-20T00:00:02Z';after=sealed(after)
  request=dict(method='PATCH',path='/api/user/urls/api',body=body)
  docs[label+'-request.json']=request;docs[label+'-writes.json']=[request];docs[label+'-response.json']={'status':200};docs[label+'-after.json']=after
  docs[label+'-api-readback.json']=[{**row,'password':row['password'] is not None} for row in after['tables']['public.Url']['rows']]
  trace.append(dict(phase=label,channel='browser-request',method='PATCH',url='http://127.0.0.1:3100/api/user/urls/api',body=json.dumps(body)))
  return after
 common=dict(context_initial={'cookies':[],'origins':[]},browser_actor={'id':'actor','role':'ADMIN'},api_actor={'id':'actor','role':'ADMIN'})
 cycles=[]
 for i,field in enumerate(plan['fields']):
  label='cycle-'+str(i);loaded=restored(label);docs[label+'-before.json']=loaded
  after=edited(label+'-replace',loaded,{field['pointer']:field['replacement']});docs[label+'-reset-before.json']=after;edited(label+'-reset',after,{field['pointer']:field['ordinary']})
  cycles.append(dict(label=label,field=field['pointer'],**common))
 docs['control-cycles.json']=cycles;branches=[]
 for b in plan['branches']:
  label=b['id'];loaded=restored(label);field=next(f for f in plan['fields'] if f['pointer']==b['unrelated']);target=next(f for f in plan['fields'] if f['pointer']==b['target'])
  changes={field['pointer']:field['replacement']};edited(label,loaded,changes)
  docs[label+'-actions.json']=([{'pointer':target['pointer'],'value':target['ordinary']}] if b['arm']=='noop_repair' else [])+[{'pointer':field['pointer'],'value':field['replacement']}]
  branches.append(dict(id=label,**common))
 docs['branches.json']=branches;docs['trace.json']=trace
 return matrix,docs

class ScheduleScoring(unittest.TestCase):
 def execute(self,matrix,docs):
  with tempfile.TemporaryDirectory() as d:
   for name,value in docs.items():(pathlib.Path(d)/name).write_text(json.dumps(value))
   return score(d,matrix)
 def test_complete_synthetic_schedule(self):
  m,d=evidence();r=self.execute(m,d);self.assertEqual((r['branches'],r['field_reset_cycles']),(24,4))
 def test_corrupted_complete_looking_schedule_is_refused(self):
  for corruption in ['missing_branch','wrong_actor','reused_context','missing_reset','missing_capture','wrong_readback','no_noop_action','duplicated_write','changed_restored_root']:
   m,d=evidence();label=m['systems'][0]['branches'][0]['id']
   if corruption=='missing_branch':d['branches.json'].pop()
   elif corruption=='wrong_actor':d['branches.json']=copy.deepcopy(d['branches.json']);d['branches.json'][0]['browser_actor']['role']='USER'
   elif corruption=='reused_context':d['branches.json']=copy.deepcopy(d['branches.json']);d['branches.json'][0]['context_initial']['origins']=[{'origin':'http://127.0.0.1:3100'}]
   elif corruption=='missing_reset':del d['cycle-3-reset-after.json']
   elif corruption=='missing_capture':d['response-capture.json'][0]['capture']['status']='body_timeout'
   elif corruption=='wrong_readback':d[label+'-api-readback.json'][1]['vanity']='wrong'
   elif corruption=='no_noop_action':
    repair=next(b['id'] for b in m['systems'][0]['branches'] if b['arm']=='noop_repair');d[repair+'-actions.json'].pop(0)
   elif corruption=='duplicated_write':d[label+'-writes.json']*=2
   elif corruption=='changed_restored_root':d[label+'-restored.json']=copy.deepcopy(d[label+'-restored.json']);d[label+'-restored.json']['files'].append({'path':'extra'})
   with self.subTest(corruption=corruption),self.assertRaises((ValueError,KeyError)):self.execute(m,d)
if __name__=='__main__':unittest.main()
