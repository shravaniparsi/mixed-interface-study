"""Source-qualified native runtime dispatch for immutable diagnostic units."""
from pathlib import Path
import os,sys,subprocess,shutil,time,importlib,socket,json
from urllib.request import Request,urlopen
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'src'));sys.path.insert(0,str(ROOT/'scripts/ci'))
from mixed_interface.common_execution_v1 import read,write,sha
from mixed_interface.repetition import require
from owned_process_scope import stop_owned_group,defer_stop_signals
from run_realworld_pilot import wait_http
from common_generated_adapter_v1 import Adapter as Generated
from common_petclinic_adapter_v1 import Adapter as PetClinic
from run_quartz_pairs import run_bounded

class Runtime:
    def __init__(self,application,output,artifact,runtime):
        self.application=application;self.output=Path(output);self.artifact=Path(artifact);self.root=Path(runtime)
        self.processes=[];self.handles=[];self.env=dict(os.environ);self.generated_config=None
        self.setup={'common_setup_s':None,'cleanup':{}}
    def launch(self,cmd,cwd,label,env=None):
        log=(self.output/(label+'.log')).open('x');self.handles.append(log)
        p=subprocess.Popen(cmd,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        self.processes.append((label,p));return p
    def prepare(self,jobs):
        began=time.monotonic()
        if self.application=='petclinic':
            self.bootstrap=read(self.artifact/'petclinic-bootstrap.json')
            p=self.launch(['node','node_modules/@angular/cli/bin/ng.js','serve','--host','127.0.0.1','--port','19766'],self.root/'petclinic/frontend','frontend')
            wait_http('http://127.0.0.1:19766',p,timeout=90)
        elif self.application=='realworld':
            self.bootstrap=read(self.artifact/'realworld-bootstrap.json')
            if any(j['runtime']['profile'].startswith('generated_') for j in jobs):self.prepare_generated()
        else:self.bootstrap=read(self.artifact/'quartz-bootstrap.json')
        self.setup['common_setup_s']=time.monotonic()-began;write(self.output/'setup.json',self.setup)
    def prepare_generated(self):
        b=self.bootstrap;subject=Path(b['subject']);frontend=subject/'fronts/vue3-realworld-example-app'
        d=self.root/'primary-generated';d.mkdir(exist_ok=False);database=d/'active.sqlite3';fixture=self.output/'fixture.sqlite3'
        for repo,expected in ((subject,b['backend_commit']),(frontend,b['frontend_commit'])):
            require(subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()==expected,'Application revision differs')
            subprocess.run(['git','diff','--exit-code','HEAD','--'],cwd=repo,check=True,timeout=20)
        env=dict(os.environ,DEBUG='True',DATABASE_URL='file:'+str(database),TZ='UTC',PYTHONDONTWRITEBYTECODE='1');self.env=env
        with (self.output/'migrate.log').open('x') as log:subprocess.run([b['python'],'manage.py','migrate','--noinput'],cwd=subject,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
        backend=self.launch([b['python'],'manage.py','runserver','127.0.0.1:18765','--noreload'],subject,'setup-backend',env)
        wait_http('http://127.0.0.1:18765/api/tags',backend)
        request=Request('http://127.0.0.1:18765/api/users',data=json.dumps({'user':{'username':'pilotresearch','email':'pilot@example.com','password':'Pilot-Research-123!'}}).encode(),headers={'Content-Type':'application/json'},method='POST')
        with urlopen(request,timeout=10) as response:require(response.status==201,'Fixture user failed')
        cleanup=stop_owned_group(backend);require(cleanup['exit_confirmed'] and not cleanup['errors'],'Setup backend cleanup failed')
        self.setup['cleanup']['setup-backend']=cleanup;self.processes.remove(('setup-backend',backend))
        shutil.copyfile(database,fixture)
        config={'subject':str(subject),'python':b['python'],'node':b['node'],'case_runner':str(ROOT/'scripts/realworld_generated_case.mjs'),
                'fixture':str(fixture),'database':str(database),'fixture_sha256':sha(fixture)}
        self.generated_config=d/'environment.json';write(self.generated_config,config)
        p=self.launch([b['node'],'node_modules/vite/bin/vite.js','preview','--host','127.0.0.1','--port','18766','--strictPort'],frontend,'frontend',env)
        wait_http('http://127.0.0.1:18766',p)
    def close(self):
        with defer_stop_signals():
            began=time.monotonic()
            for label,p in self.processes:self.setup['cleanup'][label]=stop_owned_group(p)
            for h in self.handles:h.close()
            self.setup['common_teardown_s']=time.monotonic()-began
            self.setup['cleanup_confirmed']=all(v['exit_confirmed'] and not v['errors'] for v in self.setup['cleanup'].values())
            write(self.output/'setup.json',self.setup)
        return self.setup['cleanup_confirmed']
    def execute(self,d,attempt):
        r=attempt['runtime'];profile=r['profile'];job=r['job'];bound=adapter_bound(attempt)
        if profile=='petclinic_v4':return PetClinic(self.bootstrap).execute(d,bound)
        if profile.startswith('generated_'):
            return Generated(profile,self.generated_config,self.env,sha(self.output/'fixture.sqlite3')).execute(d,bound)
        if profile=='quartz_v2':return self.quartz(d,attempt)
        registry=d/'registry.json';write(registry,r.get('registry') or read(ROOT/r['registry_path']))
        write(d/'job.json',job);(d/'run').mkdir();execution_root=self.root/'primary-native';execution_root.mkdir(exist_ok=True)
        command=[sys.executable,str(ROOT/r['runner']),'--subject',self.bootstrap['subject'],'--python',self.bootstrap['python'],'--node',self.bootstrap['node'],
                 '--runtime-root',str(execution_root),'--registry',str(registry),'--job',str(d/'job.json'),'--output-root',str(d/'run')]
        write(d/'dispatch.json',{'attempt_id':attempt['attempt_id'],'job':job,'command':command});child=None;execution={}
        try:
            with (d/'runner.log').open('x') as log:
                child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);child.wait(timeout=240)
        finally:
            with defer_stop_signals():
                if child is not None:execution=stop_owned_group(child)
                write(d/'execution.json',execution)
    def quartz(self,d,attempt):
        r=attempt['runtime'];job=r['job'];registry=ROOT/r['registry_path']
        order={'schema_version':1,'scope':'quartz_repeat_pair','registry_sha256':sha(registry),'case_ids':[b['case_id'] for b in job['branches']]};write(d/'order.json',order)
        command=['node',str(ROOT/r['runner']),'--runtime',str(self.root/'quartz'),'--java',os.environ['JAVA_HOME']+'/bin/java','--node',shutil.which('node'),'--python',sys.executable,
                 '--registry',str(registry),'--output',str(d/'run'),'--mode','boundary-pair','--case-order-file',str(d/'order.json'),'--case-timeout-ms','75000',
                 '--playwright-module',os.environ['PLAYWRIGHT_MODULE_PATH'],'--chrome-executable',os.environ['CHROME_EXECUTABLE']]
        write(d/'dispatch.json',{'attempt_id':attempt['attempt_id'],'job':job,'command':command,'order_sha256':sha(d/'order.json')})
        execution=run_bounded(command,ROOT,d/'runner.log',timeout=180,grace=110,kill_wait=5);write(d/'execution.json',execution)
        require(execution['exit_confirmed'] and not execution['hard_kill'] and not execution['timed_out'] and not execution['interrupted'] and execution.get('returncode') in (0,1),'Quartz runner lifecycle incomplete')


def adapter_bound(attempt):
    r=attempt['runtime']
    return {'runtime_job':r['job'],'runtime_context':r['context'],'binding_sha256':attempt['binding_sha256']}

def load(d,attempt,fixture_sha=None):
    r=attempt['runtime'];profile=r['profile'];job=r['job'];d=Path(d)
    if profile=='petclinic_v4':value=PetClinic().load(d,adapter_bound(attempt));costs={c:v['branch_total_s'] for c,v in value['branch_costs'].items()}
    elif profile.startswith('generated_'):
        value=Generated(profile,fixture_sha=fixture_sha).load(d,adapter_bound(attempt))
        costs={c:read(d/c/'run.json')['branch_total_s'] for c in ('api','ui')}
    elif profile=='quartz_v2':
        dispatch=read(d/'dispatch.json');execution=read(d/'execution.json')
        require(dispatch['job']==job and dispatch['attempt_id']==attempt['attempt_id'] and dispatch['order_sha256']==sha(d/'order.json'),'Quartz dispatch differs')
        require(execution['exit_confirmed'] and not execution['hard_kill'] and not execution['timed_out'] and not execution['interrupted'] and execution.get('returncode') in (0,1),'Quartz lifecycle differs')
        value=importlib.import_module(r['loader']).read_job(d/'run',job,read(ROOT/r['registry_path']),sha(ROOT/r['runner']))
        s=read(d/'run/summary.json');costs={b['continuation']:e['elapsed_ms']/1000 for b,e in zip(job['branches'],s['cases'])}
    else:
        registry=r.get('registry') or read(ROOT/r['registry_path']);dispatch=read(d/'dispatch.json')
        require(read(d/'registry.json')==registry and dispatch['job']==job and dispatch['attempt_id']==attempt['attempt_id'],'Native dispatch differs')
        value=importlib.import_module(r['loader']).read_job(d,job,registry,read(d/'execution.json'))
        s=read(next((d/'run').glob('*/summary.json')));costs={b['continuation']:b['total_s'] for b in s['branches']}
        if profile=='rw_identity':value={**value,'terminal':value['legacy_result']['terminal']}
    import math
    require(set(costs)==set(r['branch_order']) and all(type(t) in (int,float) and math.isfinite(t) and t>0 for t in costs.values()),'Branch cost unavailable')
    return {'runtime_result':value,'branch_total_s':costs}
