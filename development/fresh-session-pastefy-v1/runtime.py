"""Own one original JVM and disposable SQLite state. Run inside isolated network namespace.
No application is launched merely by importing this module.
"""
import json,os,pathlib,signal,subprocess,sys,time,urllib.request
from checkpoint import State,inventory
from fixture import seed
from shlink_sqlite import snapshot
from source_check import require
class Runtime:
 def __init__(self,base,jar,java='java'):
  self.state=State(pathlib.Path(base).resolve());self.jar=pathlib.Path(jar).resolve();require(self.jar.is_file(),'built_jar_present');self.java=java;self.process=None;self.log=None;self.starts=0
  live=self.state.live;(live/'tmp').mkdir()
  env={'DATABASE_DRIVER':'sqlite','DATABASE_FILE':str(live/'study.sqlite'),'DATABASE_POOL_MIN':'1','DATABASE_POOL_MAX':'1','HTTP_SERVER_PORT':'1337','HTTP_SERVER_CORS':'*','SERVER_NAME':'http://127.0.0.1:1337','OAUTH2_OIDC_CLIENT_ID':'disposable-study','OAUTH2_OIDC_CLIENT_SECRET':'local-fixture-only','OAUTH2_OIDC_AUTH_ENDPOINT':'http://127.0.0.1:9/auth','OAUTH2_OIDC_TOKEN_ENDPOINT':'http://127.0.0.1:9/token','OAUTH2_OIDC_USERINFO_ENDPOINT':'http://127.0.0.1:9/user','AI_PROVIDER':''}
  (live/'.env').write_text(''.join(k+'='+v+'\n' for k,v in env.items()));os.chmod(live/'.env',0o600)
 def command(self,mode):return [self.java,'-Xmx512m','-Djava.io.tmpdir='+str(self.state.live/'tmp'),'-jar',str(self.jar),mode]
 def launch(self,mode):
  require(self.process is None or self.process.poll() is not None,'single_live_jvm');self.starts+=1;self.log=(self.state.base/('jvm-'+str(self.starts)+'.log')).open('wb')
  self.process=subprocess.Popen(self.command(mode),cwd=self.state.live,env={'PATH':os.environ['PATH'],'HOME':str(self.state.live),'LANG':'C.UTF-8'},stdout=self.log,stderr=subprocess.STDOUT,start_new_session=True);self.state.track(self.process)
 def stop(self):
  if self.process is not None and self.process.poll() is None:
   os.killpg(self.process.pid,signal.SIGTERM)
   try:self.process.wait(timeout=15)
   except subprocess.TimeoutExpired:os.killpg(self.process.pid,signal.SIGKILL);self.process.wait(timeout=5)
  if self.log is not None:self.log.close();self.log=None
  self.state.stopped()
 def initialize(self):
  self.launch('automigrate')
  try:require(self.process.wait(timeout=90)==0,'original_migration_exit')
  finally:self.stop()
  return seed(self.state.live/'study.sqlite',self.state.base/'credentials.json')
 def start(self):
  self.launch('start');deadline=time.monotonic()+60
  while time.monotonic()<deadline:
   require(self.process.poll() is None,'jvm_running_during_start')
   try:
    with urllib.request.urlopen('http://127.0.0.1:1337/api/v2/app',timeout=1) as r:
     if r.status==200:return dict(status='http_ready',starts=self.starts)
   except (OSError,TimeoutError):pass
   time.sleep(.2)
  self.stop();raise ValueError('startup_deadline')
 def observe(self):
  self.state.stopped();return dict(database=snapshot(self.state.live/'study.sqlite'),files=inventory(self.state.live))
 def dispatch(self,action):
  if action=='initialize':return self.initialize()
  if action=='start':return self.start()
  if action=='stop':self.stop();return dict(status='stopped')
  if action=='observe':return self.observe()
  if action=='checkpoint':return self.state.checkpoint()
  if action=='restore':return self.state.restore()
  raise ValueError('unknown_runtime_action')
if __name__=='__main__':
 runtime=Runtime(sys.argv[1],sys.argv[2],sys.argv[3] if len(sys.argv)>3 else 'java')
 try:
  for line in sys.stdin:
   try:answer=dict(ok=True,result=runtime.dispatch(json.loads(line)['action']))
   except Exception as e:answer=dict(ok=False,error_type=type(e).__name__,error=str(e))
   print(json.dumps(answer),flush=True)
 finally:runtime.stop()
