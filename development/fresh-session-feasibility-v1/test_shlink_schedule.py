"""Full fabricated schedule over real SQLite snapshots; no application outcomes."""
import copy,hashlib,json,pathlib,sqlite3,tempfile,unittest
from matrix_check import ROOT
from shlink_sqlite import snapshot
from shlink_database_score import locate,change
from shlink_score import score

def evidence():
 matrix=json.loads((ROOT/'manifests/fresh-session-ordinary-matrix-v1.json').read_text());plan=matrix['systems'][1];fingerprint='a'*64;docs={}
 with tempfile.TemporaryDirectory() as tmp:
  db=pathlib.Path(tmp)/'db.sqlite';con=sqlite3.connect(db)
  con.executescript('''CREATE TABLE api_keys(id INTEGER PRIMARY KEY, key TEXT, enabled INTEGER, expiration_date TEXT);
CREATE TABLE api_key_roles(id INTEGER PRIMARY KEY, api_key_id INTEGER, role_name TEXT);
CREATE TABLE short_urls(id INTEGER PRIMARY KEY AUTOINCREMENT, original_url TEXT, long_url_hash BLOB, short_code TEXT UNIQUE, title TEXT, title_was_auto_resolved INTEGER, forward_query INTEGER, domain_id INTEGER, author_api_key_id INTEGER REFERENCES api_keys(id));
CREATE TABLE short_urls_in_tags(short_url_id INTEGER REFERENCES short_urls(id),tag_id INTEGER);
CREATE TABLE unrelated(id INTEGER PRIMARY KEY,value TEXT); INSERT INTO unrelated VALUES(1,'ordinary');''')
  con.execute('INSERT INTO api_keys VALUES(1,?,1,NULL)',(fingerprint,));con.commit();empty=snapshot(db)
  def insert(code):
   b=plan['api'];con.execute('INSERT INTO short_urls(original_url,long_url_hash,short_code,title,title_was_auto_resolved,forward_query,domain_id,author_api_key_id) VALUES(?,?,?,?,0,1,NULL,1)',(b['longUrl'],hashlib.sha256(b['longUrl'].encode()).digest(),code,b['title']));con.commit();return snapshot(db)
  native=insert('native');root=insert('api');con.close()
 def state(db):return {'database':copy.deepcopy(db),'filesystem':{'files':[],'database_physical':[{'path':'data/database.sqlite','sha256':'synthetic'}]},'redis':{'database':0,'entries':[]}}
 def readback(s,identity):
  r=locate(s['database'],identity)[1];return {'shortCode':r['short_code'],'longUrl':r['original_url'],'title':r['title'],'domain':None,'tags':[]}
 root=state(root);docs['root-state']=root;docs['native-before']=state(empty);docs['native-after']=state(native);docs['api-before']=state(native);docs['api-after']=root
 docs['result']=dict(status='controls_completed',cleanup_complete=True,record_id=2,native_record_id=1,actor_id=1,api_key_sha256=fingerprint,short_code='api');docs['actor-key']={'sha256':fingerprint}
 docs['native-api-readback']=readback(docs['native-after'],1);docs['api-created-readback']=readback(root,2)
 docs['api-trace']=[dict(label='api-create',method='POST',path='/rest/v3/short-urls',body=plan['api'],status=200,response=json.dumps(readback(root,2)),api_key_sha256=fingerprint)]
 docs['api-create-response']=readback(root,2)
 for label,filename,code in [('native-readback','native-api-readback','native'),('api-created-readback','api-created-readback','api')]:
  docs['api-trace'].append(dict(label=label,method='GET',path='/rest/v3/short-urls/'+code,body=None,status=200,response=json.dumps(docs[filename]),api_key_sha256=fingerprint))
 def context(prefix):
  docs[prefix+'-initial-context']={'cookies':[],'origins':[]};docs[prefix+'-browser-errors']=[];docs[prefix+'-selected-server']={'api_key_sha256':fingerprint};docs[prefix+'-browser-trace']=[];docs[prefix+'-response-capture']=[]
 def operation(prefix,label,actions,before,after,identity,method='PATCH'):
  request=dict(method=method,path='/rest/v3/short-urls'+('/api' if method=='PATCH' else ''),query='',body={p[1:]:v for p,v in actions.items()})
  text=json.dumps(readback(after,identity));response={'status':200,'text':text};pre=readback(before,identity) if method=='PATCH' else {'longUrl':'','title':''}
  action_rows=[dict(pointer=p,value=v) for p,v in actions.items()]
  docs[prefix+'-'+label+'-request']=request;docs[prefix+'-'+label+'-response']=response;docs[prefix+'-'+label+'-writes']=[request];docs[prefix+'-'+label+'-control']=dict(label=label,actions=action_rows,request=request,response_status=200,form_before={k:pre[k] for k in ['longUrl','title']})
  trace=docs[prefix+'-browser-trace'];trace.extend(dict(phase=label,kind='native_fill',**r) for r in action_rows);request_id=len(trace)+1
  trace.append(dict(phase=label,kind='request',id=request_id,url='http://127.0.0.1:58080'+request['path'],method=method,body=json.dumps(request['body']),api_key_sha256=fingerprint))
  docs[prefix+'-response-capture'].append(dict(phase=label,id=request_id,status=200,url='http://127.0.0.1:58080'+request['path'],capture={'status':'complete','body':text}))
 context('native');operation('native','create',{'/longUrl':plan['native']['longUrl'],'/title':plan['native']['title']},docs['native-before'],docs['native-after'],1,'POST')
 def start(prefix):context(prefix);docs[prefix+'-restored']=root;docs[prefix+'-loaded']=root;return copy.deepcopy(root)
 def edited(prefix,label,before,changes,actions=None):
  after=copy.deepcopy(before)
  for pointer,value in changes.items():
   if pointer=='/title':change(after['database'],2,'title',value)
   else:change(after['database'],2,'original_url',value);change(after['database'],2,'long_url_hash',hashlib.sha256(value.encode()).digest())
  operation(prefix,label,actions or changes,before,after,2);docs[label+'-after']=after;docs[label+'-api-readback']=readback(after,2)
  docs['api-trace'].append(dict(label=label+'-readback',method='GET',path='/rest/v3/short-urls/api',body=None,status=200,response=json.dumps(readback(after,2)),api_key_sha256=fingerprint))
  return after
 docs['control-cycles']=[]
 for i,f in enumerate(plan['fields']):
  prefix='cycle-'+str(i);loaded=start(prefix);after=edited(prefix,prefix+'-replace',loaded,{f['pointer']:f['replacement']});docs[prefix+'-reset-before']=after;edited(prefix,prefix+'-reset',after,{f['pointer']:f['ordinary']});docs['control-cycles'].append({'label':prefix,'field':f['pointer']})
 docs['branches']=[]
 for b in plan['branches']:
  label=b['id'];loaded=start(label);target=next(f for f in plan['fields'] if f['pointer']==b['target']);other=next(f for f in plan['fields'] if f['pointer']==b['unrelated']);changes={other['pointer']:other['replacement']};actions={**({target['pointer']:target['ordinary']} if b['arm']=='noop_repair' else {}),**changes};edited(label,label,loaded,changes,actions);docs['branches'].append({'id':label})
 return matrix,docs
class FullSchedule(unittest.TestCase):
 def execute(self,matrix,docs):
  with tempfile.TemporaryDirectory() as tmp:
   for name,value in docs.items():(pathlib.Path(tmp)/(name+'.json')).write_text(json.dumps(value))
   return score(tmp,matrix)
 def test_full_schedule(self):
  m,d=evidence();r=self.execute(m,d);self.assertEqual((r['branches'],r['field_reset_cycles']),(12,2))
 def test_corrupted_schedule_refused(self):
  for fault in ['missing_branch','stale_context','missing_reset','wrong_key','wrong_record','extra_file','changed_cache','wrong_readback','missing_capture','extra_write','wrong_captured_body','wrong_form','detached_api_trace']:
   m,d=evidence();label=m['systems'][1]['branches'][0]['id']
   if fault=='missing_branch':d['branches'].pop()
   elif fault=='stale_context':d[label+'-initial-context']['origins']=[{'origin':'http://127.0.0.1:58081'}]
   elif fault=='missing_reset':del d['cycle-1-reset-after']
   elif fault=='wrong_key':d[label+'-selected-server']['api_key_sha256']='b'*64
   elif fault=='wrong_record':change(d[label+'-after']['database'],2,'id',99)
   elif fault=='extra_file':d[label+'-after']['filesystem']['files'].append({'path':'unexpected'})
   elif fault=='changed_cache':d[label+'-after']['redis']['entries'].append(dict(key='eA==',type='string',pttl=-1,value='eQ==',dump='eQ=='))
   elif fault=='wrong_readback':d[label+'-api-readback']['title']='wrong'
   elif fault=='missing_capture':d[label+'-response-capture']=[]
   elif fault=='extra_write':d[label+'-'+label+'-writes']*=2
   elif fault=='wrong_captured_body':d[label+'-response-capture'][0]['capture']['body']='{}'
   elif fault=='wrong_form':d[label+'-'+label+'-control']['form_before']['title']='stale'
   elif fault=='detached_api_trace':next(r for r in d['api-trace'] if r['label']==label+'-readback')['response']='{}'
   with self.subTest(fault=fault),self.assertRaises((ValueError,KeyError)):self.execute(m,d)
if __name__=='__main__':unittest.main()
