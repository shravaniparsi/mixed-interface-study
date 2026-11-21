"""Fixed ordinary native/API producer schedule. Must execute in owned loopback namespace."""
import hashlib,json,os,pathlib,subprocess,sys,urllib.request
from runtime import Runtime
from source_check import require
ROOT=pathlib.Path(__file__).resolve().parents[2]
def main(base,jar):
 base=pathlib.Path(base).resolve();require(not base.exists(),'fresh_execution');base.mkdir(mode=0o700);out=base/'evidence';out.mkdir();rt=Runtime(base/'state',jar,os.environ.get("JAVA_BIN","java"));report=dict(status='running',phase='ordinary_qualification',branches=[],creations=[])
 def save():(out/'execution.json').write_text(json.dumps(report,indent=2)+'\n')
 def observe(name):
  rt.stop();d=rt.observe();(out/(name+'.json')).write_text(json.dumps(d,indent=2)+'\n');return name+'.json'
 def api(method,path,payload=None):
  req=urllib.request.Request('http://127.0.0.1:1337'+path,data=None if payload is None else json.dumps(payload).encode(),method=method,headers={'Authorization':'Bearer '+credentials['api_key'],'Content-Type':'application/json'})
  with urllib.request.urlopen(req,timeout=15) as response:body=json.load(response);status=response.status
  return dict(method=method,path=path,request=payload,status=status,body=body)
 def native(name,action,**kwargs):
  inp=dict(action=action,credentials=str(rt.state.base/'credentials.json'),**kwargs);p=base/(name+'-input.json');p.write_text(json.dumps(inp));os.chmod(p,0o600);target=out/(name+'-browser.json')
  subprocess.run([os.environ.get('NODE_BIN','node'),str(pathlib.Path(__file__).with_name('browser_cli.mjs')),str(p),str(target)],check=True,timeout=120)
  return json.loads(target.read_text()),target.name
 try:
  require(pathlib.Path('/proc/self/ns/net').exists(),'linux_namespace_required')
  interfaces=json.loads(subprocess.check_output(['ip','-json','address'],text=True));routes=json.loads(subprocess.check_output(['ip','-json','route'],text=True))
  require({x['ifname'] for x in interfaces}=={'lo'} and not routes,'loopback_only_no_routes');report['network']=dict(interfaces=interfaces,routes=routes)
  report['fixture']=rt.initialize();credentials=json.loads((rt.state.base/'credentials.json').read_text());report['actor']=dict(user_id=credentials['user_id'],key_sha256=hashlib.sha256(credentials['api_key'].encode()).hexdigest())
  ordinary=json.loads((ROOT/'manifests/fresh-session-pastefy-ordinary-input-v1.json').read_text())['producer'];rt.state.checkpoint('root')
  for arm in ['native','api']:
   rt.state.restore('root');before=observe(arm+'-create-before');rt.start()
   identity=api('GET','/api/v2/user');require(identity['body']['id']==credentials['user_id'] and identity['body']['logged_in'] is True,'api_same_owner')
   if arm=='native':record,path=native(arm+'-create','create',input=ordinary);body=record['body'];transport=dict(browser=path)
   else:record=api('POST','/api/v2/paste',ordinary);body=record['body'];transport=dict(api=record)
   require(body.get('success') is True,'producer_success');key=body['paste']['id'];readback=api('GET','/api/v2/paste/'+key);after=observe(arm+'-create-after');rt.state.checkpoint(arm)
   report['creations'].append(dict(arm=arm,before=before,after=after,key=key,identity=identity,readback=readback,**transport));save()
   for field,value in [('title','study-note-edited.txt'),('content','Disposable revised study text.')]:
    rt.state.restore(arm);name=arm+'-'+field;before=observe(name+'-before');rt.start();record,path=native(name,'edit',key=key,field=field,value=value);readback=api('GET','/api/v2/paste/'+key);after=observe(name+'-after')
    report['branches'].append(dict(arm=arm,field=field,value=value,key=key,before=before,after=after,browser=path,readback=readback));save()
  report['status']='ordinary_execution_completed_requires_independent_score'
 finally:rt.stop();report['jvm_stopped']=all(p.poll() is not None for p in rt.state.writers);rt.state.close_database();report['database_stopped']=rt.state.db_process is None or rt.state.db_process.poll() is not None;save()
if __name__=='__main__':main(sys.argv[1],sys.argv[2])
