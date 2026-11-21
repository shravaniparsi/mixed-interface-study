#!/usr/bin/env python3
"""Owned job-local Docker lifecycle. No downloads, image builds, uploads or retries."""
import hashlib,json,os,pathlib,secrets,shutil,subprocess,time,urllib.request
from source_check import require
from shlink_sqlite import snapshot as sqlite_snapshot
from shlink_files import inventory,compare_non_database
from shlink_redis import Redis,snapshot as redis_snapshot,restore_empty,logical as redis_logical
HERE=pathlib.Path(__file__).resolve().parent

def atomic(path,value):
 temporary=path.with_suffix(path.suffix+'.tmp');temporary.write_text(json.dumps(value,indent=2)+'\n');temporary.chmod(0o600);temporary.replace(path)
class Deployment:
 def __init__(self,base):
  self.base=pathlib.Path(base).resolve();self.private=self.base/'deployment.json';self.data=self.base/'persistent';self.evidence=self.base/'evidence';self.evidence.mkdir(exist_ok=True)
  self.info=json.loads(self.private.read_text()) if self.private.exists() else None
 def save(self):atomic(self.private,self.info)
 def command(self,args,label,timeout=30):
  require(self.info is not None,'initialized_deployment');require(time.time()<self.info['deadline_epoch'],'application_time_cap')
  index=len(self.info['commands']);row=dict(command=args,label=label);self.info['commands'].append(row);self.save();start=time.monotonic()
  path=self.evidence/('docker-%04d.log'%index)
  try:
   with path.open('wb') as log:
    path.chmod(0o600);cp=subprocess.run(args,stdout=log,stderr=subprocess.STDOUT,timeout=min(timeout,max(1,self.info['deadline_epoch']-time.time())))
   row['exit_code']=cp.returncode;require(cp.returncode==0,'docker_command',label=label,exit_code=cp.returncode)
   require(path.stat().st_size<=16*1024**2,'command_output_cap',label=label)
   return path.read_text()
  finally:row['elapsed_seconds']=time.monotonic()-start;self.save()
 def inspect(self,name):return json.loads(self.command(['docker','inspect',name],'inspect'))[0]
 def prepare(self):
  require(self.info is None and not self.data.exists(),'new_deployment_only')
  build=json.loads((self.base/'build-evidence/result.json').read_text());require(build['status']=='build_verified','verified_build_required')
  prefix='fresh-shlink-'+secrets.token_hex(5);key=secrets.token_urlsafe(32)
  self.info=dict(prefix=prefix,network=prefix+'-net',containers={},commands=[],images={k:build['images'][k]['id'] for k in ['backend-runtime','client-runtime','redis']},api_key=key,deadline_epoch=time.time()+1400,network_created=False);self.save()
  self.data.mkdir(mode=0o700);(self.data/'data').mkdir();(self.data/'config').mkdir();self.save()
  self.command(['docker','network','create','--internal',self.info['network']],'network-create');self.info['network_created']=True;self.save()
  self.command(['docker','network','inspect',self.info['network']],'network-identity')
  # Preserve the original image's config and data seed, before its entrypoint runs.
  name=prefix+'-extract';self.command(['docker','create','--name',name,'--label','study.owner='+prefix,self.info['images']['backend-runtime']],'seed-create');self.info['containers']['extract']=name;self.save()
  try:
   self.command(['docker','cp','-a',name+':/etc/shlink/config/params',str(self.data/'config')],'seed-config')
   self.command(['docker','cp','-a',name+':/etc/shlink/data/.',str(self.data/'data')],'seed-data')
  finally:self.remove('extract')
  for p in [self.data,self.data/'data',self.data/'config',self.data/'config/params']:
   p.chmod(0o755);os.chown(p,1001,1001)
  backend={'DB_DRIVER':'sqlite','DEFAULT_DOMAIN':'shlink.test','IS_HTTPS_ENABLED':'false','REDIS_SERVERS':'tcp://study-redis:6379','REDIS_PUB_SUB_ENABLED':'false','MERCURE_ENABLED':'false','RABBITMQ_ENABLED':'false','MATOMO_ENABLED':'false','AUTO_RESOLVE_TITLES':'true','SKIP_INITIAL_GEOLITE_DOWNLOAD':'true','WEB_WORKER_NUM':'1','TASK_WORKER_NUM':'1','INITIAL_API_KEY':key}
  client={'SHLINK_SERVER_URL':'http://127.0.0.1:58080','SHLINK_SERVER_API_KEY':key,'SHLINK_SERVER_NAME':'Study Shlink'}
  for name,values in [('backend',backend),('client',client)]:
   p=self.base/(name+'.env');p.write_text(''.join(k+'='+v+'\n' for k,v in values.items()));p.chmod(0o600)
  fixture=self.base/'fixture';fixture.mkdir();(fixture/'index.php').write_text('<?php header("Content-Type: text/html; charset=UTF-8"); echo "<title>Study fixture title</title>";')
  self.start_redis()
  self.run_container('fixture',self.info['images']['backend-runtime'],['--network-alias','study-fixture','--mount','type=bind,src='+str(fixture)+',dst=/study-fixture,readonly','--entrypoint','php'],['-S','0.0.0.0:8089','-t','/study-fixture','/study-fixture/index.php'])
  self.run_container('client',self.info['images']['client-runtime'],['--env-file',str(self.base/'client.env'),'-p','127.0.0.1:58081:8080'])
  self.start_backend()
 def run_container(self,role,image,options,arguments=None):
  require(role not in self.info['containers'],'unique_owned_role');name=self.info['prefix']+'-'+role
  # Record ownership before launch so a failed post-start command still has a cleanup target.
  self.info['containers'][role]=name;self.save()
  self.command(['docker','run','-d','--name',name,'--label','study.owner='+self.info['prefix'],'--network',self.info['network']]+options+[image]+(arguments or []),role+'-start')
  require(self.inspect(name)['State']['Running'],'container_running',role=role)
 def start_redis(self):
  self.run_container('redis',self.info['images']['redis'],['--network-alias','study-redis','-p','127.0.0.1:56379:6379'],['redis-server','--save','','--appendonly','no'])
  deadline=time.monotonic()+10
  while True:
   try:
    c=Redis();require(c.cmd('PING')==b'PONG','redis_ready');c.close();break
   except (ConnectionError,OSError):
    require(time.monotonic()<deadline,'redis_ready_deadline');time.sleep(.1)
 def start_backend(self):
  self.run_container('backend',self.info['images']['backend-runtime'],['--env-file',str(self.base/'backend.env'),'-p','127.0.0.1:58080:8080','--mount','type=bind,src='+str(self.data/'data')+',dst=/etc/shlink/data','--mount','type=bind,src='+str(self.data/'config/params')+',dst=/etc/shlink/config/params'])
  deadline=time.monotonic()+90
  while True:
   try:
    with urllib.request.urlopen('http://127.0.0.1:58080/rest/health',timeout=2) as response:
     if response.status==200:break
   except (OSError,ValueError):pass
   require(time.monotonic()<deadline,'backend_health_deadline');require(self.inspect(self.info['containers']['backend'])['State']['Running'],'backend_stayed_running');time.sleep(.25)
  # Observe the original configuration with no event dispatch or queue consumption.
  name=self.info['containers']['backend'];self.command(['docker','cp',str(HERE/'shlink_event_probe.php'),name+':/tmp/study-event-probe.php'],'probe-copy')
  result=self.command(['docker','exec','--env','RR_MODE=http',name,'php','/tmp/study-event-probe.php'],'event-probe')
  probe=json.loads(result);require(probe['status']=='no_enabled_async_listeners','async_listeners_disabled');atomic(self.evidence/('event-probe-'+str(len(self.info['commands']))+'.json'),probe)
  self.command(['docker','cp',str(HERE/'shlink_worker_probe.php'),name+':/tmp/study-worker-probe.php'],'worker-probe-copy')
  worker_result=json.loads(self.command(['docker','exec',name,'php','/tmp/study-worker-probe.php'],'worker-probe'))
  require(worker_result['status']=='worker_spawn_configuration_verified','worker_configuration_verified')
  require(worker_result['workers'][0]['initial_api_key_sha256']==hashlib.sha256(self.info['api_key'].encode()).hexdigest(),'worker_key_identity')
  atomic(self.evidence/('worker-probe-'+str(len(self.info['commands']))+'.json'),worker_result)

 def remove(self,role):
  name=self.info['containers'].get(role)
  if not name:return
  require(name==self.info['prefix']+'-'+role,'owned_container_name')
  matches=self.command(['docker','ps','-aq','--filter','name=^/'+name+'$'],role+'-existence').split()
  require(len(matches)<=1,'unique_owned_container')
  if matches:
   observed=self.inspect(name);require(observed['Config'].get('Labels',{}).get('study.owner')==self.info['prefix'],'owned_container_label')
   try:self.command(['docker','logs','--tail','1000',name],role+'-final-logs')
   except Exception as error:self.info.setdefault('diagnostic_errors',[]).append(dict(role=role,error=str(error)));self.save()
   self.command(['docker','rm','--force',name],role+'-remove')
  del self.info['containers'][role];self.save()
 def observe(self,label):
  require(label and all(c.isalnum() or c in '-_' for c in label),'safe_observation_label')
  name=self.info['containers']['backend'];require(self.inspect(name)['State']['Running'],'backend_running_before_observation')
  # Caller must first finish owned HTTP operations. Freeze the sole application writer
  # for the cross-store observation, without restarting its process or browser session.
  self.command(['docker','pause',name],'pause-writer')
  try:
   require(self.inspect(name)['State']['Paused'],'writer_pause_verified')
   c=Redis()
   try:cache=redis_snapshot(c)
   finally:c.close()
   value=dict(database=sqlite_snapshot(self.data/'data/database.sqlite'),filesystem=inventory(self.data),redis=cache)
   atomic(self.evidence/(label+'.json'),value);return value
  finally:self.command(['docker','unpause',name],'unpause-writer')
 def checkpoint(self):
  before=self.observe('root-before-stop');name=self.info['containers']['backend'];self.command(['docker','stop','--time','10',name],'root-stop');require(not self.inspect(name)['State']['Running'],'root_stopped')
  root=self.base/'root-persistent';require(not root.exists(),'new_root_checkpoint');self.command(['cp','-a',str(self.data),str(root)],'root-copy')
  copied=dict(database=sqlite_snapshot(root/'data/database.sqlite'),filesystem=inventory(root));require(copied['database']==before['database'],'root_database_copy');compare_non_database(copied['filesystem'],before['filesystem'])
  c=Redis()
  try:require(redis_logical(redis_snapshot(c))==redis_logical(before['redis']),'root_cache_unchanged')
  finally:c.close()
  atomic(self.base/'root-state.json',before);self.remove('backend');return before
 def restore(self):
  self.remove('backend');self.remove('redis');root=self.base/'root-persistent';require(root.is_dir() and not root.is_symlink(),'root_checkpoint_present')
  # Only the persistent directory created by this deployment may be replaced.
  require(self.data.parent==self.base and self.data.name=='persistent' and not self.data.is_symlink(),'owned_persistent_directory');shutil.rmtree(self.data)
  self.command(['cp','-a',str(root),str(self.data)],'restore-files');expected=json.loads((self.base/'root-state.json').read_text())
  require(sqlite_snapshot(self.data/'data/database.sqlite')==expected['database'],'restored_database');compare_non_database(inventory(self.data),expected['filesystem'])
  self.start_redis();c=Redis()
  try:restore_empty(c,expected['redis']);restored_cache=redis_snapshot(c)
  finally:c.close()
  restored=dict(database=sqlite_snapshot(self.data/'data/database.sqlite'),filesystem=inventory(self.data),redis=restored_cache)
  atomic(self.evidence/'last-restored-root.json',restored);self.start_backend()
 def cleanup(self):
  # Cleanup gets its own bounded window even when the application deadline elapsed.
  self.info['deadline_epoch']=time.time()+90;self.save();errors=[]
  for role in list(self.info['containers']):
   try:self.remove(role)
   except Exception as error:errors.append(dict(role=role,error=str(error)))
  if self.info['network_created']:
   try:self.command(['docker','network','rm',self.info['network']],'network-remove');self.info['network_created']=False
   except Exception as error:errors.append(dict(role='network',error=str(error)))
  self.info['cleanup_errors']=errors;self.save();require(not errors,'cleanup_complete',errors=errors)
if __name__=='__main__':
 import sys
 deployment=Deployment(sys.argv[1]);action=sys.argv[2];require(action in {'prepare','observe','checkpoint','restore','cleanup'},'known_action')
 value=getattr(deployment,action)(sys.argv[3]) if action=='observe' else getattr(deployment,action)()
 print(json.dumps({'action':action,'status':'completed'}))
