import copy,hashlib,json,pathlib,tempfile,unittest
from score_controls import score,ROOT
from shlink_sqlite import typed
class WholeControlGate(unittest.TestCase):
 def fixture(self,path):
  cases=json.loads((ROOT/'manifests/fresh-session-pastefy-pilot-inputs-v1.json').read_text())['cases'][:2]
  run=dict(status='schedule_finished_requires_independent_score',network=dict(interfaces=[{'ifname':'lo'}],routes=[]),cases=[])
  def save(name,value):
   name=name+'.json';(path/name).write_text(json.dumps(value));return name
  for case in cases:
   prefix=case['id'];ordinary=case['input'];owner='study001';key='abcdefgh';actor=dict(user_id=owner,key_sha256='fixture-hash');native_actor={**actor,'role':'USER'}
   row=dict(folder=None,expire_at=None,title=ordinary['title'],content=ordinary['content'],user_id=owner,forked_from=None,encrypted=0,type='PASTE',visibility='UNLISTED',storage_type='DATABASE',version=1,indexed_in_elastic=0,length=len(ordinary['content'].encode()),hash=hashlib.sha256(ordinary['content'].encode()).hexdigest(),key=key,id=1,created_at='2026-01-01 00:00:00',updated_at='2026-01-01 00:00:00')
   def obs(row):return dict(database=dict(schema=[],pragmas={},tables={'pastefy_pastes':dict(columns=[[i,k] for i,k in enumerate(row)],rows=[[typed(v) for v in row.values()]])}),files={})
   produced=obs(row);empty=copy.deepcopy(produced);empty['database']['tables']['pastefy_pastes']['rows']=[]
   def receipt(method,payload,body):return dict(method=method,path='/api/v2/paste'+('' if method=='POST' else '/'+key),status=200,request=payload,body=body)
   def readback(fields):return receipt('GET',None,dict(id=key,user_id=owner,exists=True,**fields))
   control=dict(id=prefix,status='executed_requires_score',jvm_stopped=True,database_stopped=True,key=key,actor=actor,identity={'status':200,'body':{'id':owner,'logged_in':True}},producer=receipt('POST',ordinary,dict(success=True,paste={'id':key})),producer_before=save(prefix+'-empty',empty),produced=save(prefix+'-produced',produced),producer_readback=readback({f:ordinary[f] for f in ['title','content']}),branches=[])
   control['probe_before']=control['produced'];control['probe_after']=control['produced'];expected={**ordinary,case['continuation']['field']:case['continuation']['value']}
   probe=dict(actor=native_actor,prediction='native_request_emitted',request=expected,writes=[dict(method='PUT',origin='http://127.0.0.1:1337',path='/api/v2/paste/'+key,disposition='aborted_before_forwarding',request=json.dumps(expected))]);control['probe']=save(prefix+'-probe',probe)
   for arm in ['sham','repair']:
    inter={**row,'version':2,'updated_at':'2026-01-01 00:00:01'};after={**inter,case['continuation']['field']:case['continuation']['value'],'version':3,'updated_at':'2026-01-01 00:00:02'}
    after['length']=len(after['content'].encode());after['hash']=hashlib.sha256(after['content'].encode()).hexdigest()
    browser=dict(status='native_action_completed',actor=native_actor,receipts=[dict(method='PUT',path='/api/v2/paste/'+key,status=200,request=json.dumps(expected),body=json.dumps({'success':True}))])
    control['branches'].append(dict(arm=arm,status='executed_requires_score',before=control['produced'],intervention=receipt('PUT',case[arm],{'success':True}),intervention_readback=control['producer_readback'],intervened=save(prefix+'-'+arm+'-inter',obs(inter)),after=save(prefix+'-'+arm+'-after',obs(after)),browser=save(prefix+'-'+arm+'-browser',browser),readback=readback({f:expected[f] for f in ['title','content']})))
   run['cases'].append(control)
  save('controls',run);return run
 def test_complete_pair_and_missing_branch(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);run=self.fixture(p);self.assertEqual(score(p)['status'],'ordinary_paired_controls_verified');run['cases'][0]['branches'].pop();(p/'controls.json').write_text(json.dumps(run))
   with self.assertRaisesRegex(ValueError,'complete_ordered_intervention_pair'):score(p)
 def test_forwarded_probe_refused(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);run=self.fixture(p);f=p/run['cases'][0]['probe'];probe=json.loads(f.read_text());probe['writes'][0]['disposition']='forwarded';f.write_text(json.dumps(probe))
   with self.assertRaisesRegex(ValueError,'one_blocked_probe_write'):score(p)
 def test_probe_actual_request_disagreement_refused(self):
  with tempfile.TemporaryDirectory() as d:
   p=pathlib.Path(d);run=self.fixture(p);f=p/run['cases'][0]['branches'][0]['browser'];b=json.loads(f.read_text());payload=json.loads(b['receipts'][0]['request']);payload['title']='unexpected';b['receipts'][0]['request']=json.dumps(payload);f.write_text(json.dumps(b))
   with self.assertRaisesRegex(ValueError,'probe_matches_actual_native_serialization'):score(p)
