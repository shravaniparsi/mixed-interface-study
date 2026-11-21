"""Ordinary paired controls only. No altered input can be selected by this entrypoint."""
import hashlib,json,os,pathlib,signal,subprocess,sys,time,urllib.request,urllib.error
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'fresh-session-pastefy-v1'))
from runtime import Runtime
from source_check import require
ROOT=pathlib.Path(__file__).resolve().parents[2]
HERE=pathlib.Path(__file__).resolve().parent

def main(base,jar):
 base=pathlib.Path(base).resolve();require(not base.exists(),'fresh_control_execution');base.mkdir(mode=0o700);out=base/'evidence';out.mkdir()
 report=dict(status='running',phase='ordinary_paired_controls',cases=[])
 def save():(out/'controls.json').write_text(json.dumps(report,indent=2)+'\n')
 interfaces=json.loads(subprocess.check_output(['ip','-json','address'],text=True));routes=json.loads(subprocess.check_output(['ip','-json','route'],text=True))
 require({x['ifname'] for x in interfaces}=={'lo'} and not routes,'loopback_only_no_routes');report['network']=dict(interfaces=interfaces,routes=routes)
 schedule=json.loads((ROOT/'manifests/fresh-session-pastefy-pilot-inputs-v1.json').read_text())['cases'][:2]
 require([c['id'] for c in schedule]==['ordinary-content','ordinary-title'] and all(c['mutation']=='ordinary' for c in schedule),'ordinary_controls_only')
 for case in schedule:
  prefix=case['id'];rt=Runtime(base/('state-'+prefix),jar,os.environ.get('JAVA_BIN','java'));record=dict(id=prefix,status='running',branches=[]);report['cases'].append(record);save()
  def observe(label):
   rt.stop();name=prefix+'-'+label+'.json';(out/name).write_text(json.dumps(rt.observe(),indent=2)+'\n');return name
  def api(method,path,payload=None):
   req=urllib.request.Request('http://127.0.0.1:1337'+path,data=None if payload is None else json.dumps(payload).encode(),method=method,headers={'Authorization':'Bearer '+credentials['api_key'],'Content-Type':'application/json'})
   try:response=urllib.request.urlopen(req,timeout=15)
   except urllib.error.HTTPError as error:response=error
   with response:raw=response.read().decode();status=response.status
   try:body=json.loads(raw)
   except ValueError:body=raw
   return dict(method=method,path=path,request=payload,status=status,body=body)
  def browser(label,probe=False):
   name=prefix+'-'+label;input_path=base/(name+'-input.json');output=out/(name+'-browser.json')
   inp=dict(action='edit',credentials=str(rt.state.base/'credentials.json'),key=record['key'],**case['continuation']);input_path.write_text(json.dumps(inp));os.chmod(input_path,0o600)
   script=HERE/'probe.mjs' if probe else HERE.parent/'fresh-session-pastefy-v1/browser_cli.mjs'
   subprocess.run([os.environ.get('NODE_BIN','node'),str(script),str(input_path),str(output)],check=True,timeout=120)
   return output.name
  try:
   record['fixture']=rt.initialize();credentials=json.loads((rt.state.base/'credentials.json').read_text());record['actor']=dict(user_id=credentials['user_id'],key_sha256=hashlib.sha256(credentials['api_key'].encode()).hexdigest())
   record['producer_before']=observe('producer-before');rt.start();record['identity']=api('GET','/api/v2/user');record['producer']=api('POST','/api/v2/paste',case['input']);save()
   require(record['producer']['status']==200 and record['producer']['body'].get('success') is True,'ordinary_producer_success')
   record['key']=record['producer']['body']['paste']['id'];record['producer_readback']=api('GET','/api/v2/paste/'+record['key']);record['produced']=observe('produced');rt.state.checkpoint('native');save()
   rt.state.restore('native');record['probe_before']=observe('probe-before');rt.start();record['probe']=browser('probe',True);record['probe_after']=observe('probe-after');save()
   for arm in ['sham','repair']:
    branch=dict(arm=arm,status='running');record['branches'].append(branch);save()
    try:
     rt.state.restore('native');branch['before']=observe(arm+'-before');rt.start();branch['intervention']=api('PUT','/api/v2/paste/'+record['key'],case[arm]);branch['intervention_readback']=api('GET','/api/v2/paste/'+record['key']);branch['intervened']=observe(arm+'-intervened');save()
     rt.start();branch['browser']=browser(arm);branch['readback']=api('GET','/api/v2/paste/'+record['key']);branch['after']=observe(arm+'-after');branch['status']='executed_requires_score'
    except Exception as error:
     branch.update(status='unavailable',error_type=type(error).__name__,error=str(error));rt.stop()
    finally:save()
   record['status']='executed_requires_score'
  except Exception as error:
   record.update(status='unavailable',error_type=type(error).__name__,error=str(error))
   if rt.process is not None and rt.process.poll() is None:os.kill(rt.process.pid,signal.SIGQUIT);time.sleep(.5)
  finally:
   rt.stop();record['jvm_stopped']=all(p.poll() is not None for p in rt.state.writers);rt.state.close_database();record['database_stopped']=rt.state.db_process is None or rt.state.db_process.poll() is not None;save()
 report['status']='schedule_finished_requires_independent_score';save()
if __name__=='__main__':main(sys.argv[1],sys.argv[2])
