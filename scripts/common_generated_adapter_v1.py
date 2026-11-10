"""Common bridge adapter using unchanged generated worker and source-qualified loaders."""
import os,sys,subprocess,time,socket
from pathlib import Path
from realworld_generated_bindings_v1 import ROOT,case_for,extract
from realworld_generated_runtime_v2 import branch as control_branch
from realworld_generated_runtime_v3 import branch as mutation_branch
from realworld_generated_terminal_v1 import compare as control_compare
from realworld_generated_terminal_v3 import compare as mutation_compare
from realworld_case_worker import cleanup_browser
from mixed_interface.common_execution_v1 import read,write,sha
from mixed_interface.repetition import require
sys.path.insert(0,str(ROOT/'scripts/ci'))
from owned_process_scope import stop_owned_group,defer_stop_signals

def closed():
    with socket.socket() as s:return s.connect_ex(('127.0.0.1',18765))!=0

class Adapter:
    def __init__(self,profile,config_path=None,env=None,fixture_sha=None):
        require(profile in ('generated_control_v2','generated_mutation_v3'),'Unsupported generated profile')
        self.profile=profile;self.config_path=config_path;self.env=env;self.fixture_sha=fixture_sha
        self.loader=control_branch if profile=='generated_control_v2' else mutation_branch
        self.compare=control_compare if profile=='generated_control_v2' else mutation_compare
    def execute(self,directory,bound):
        job=bound['runtime_job'];write(directory/'job.json',job)
        write(directory/'dispatch.json',{'binding_sha256':bound['binding_sha256'],'job':job,'profile':self.profile})
        config=read(self.config_path);python=config['python'];env=self.env;fixture_sha=config['fixture_sha256']
        for declared in job['branches']:
            channel=declared['channel'];spec=case_for(job,channel);d=directory/channel;d.mkdir();write(d/'case.json',spec)
            began=time.monotonic();worker=None;timed_out=False
            try:
                with (d/'worker.log').open('w') as log:
                    worker=subprocess.Popen([python,str(ROOT/'scripts/realworld_generated_worker_v2.py'),'--environment',str(self.config_path),'--case',str(d/'case.json'),'--output',str(d)],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                    worker.wait(timeout=80)
            except subprocess.TimeoutExpired:timed_out=True
            finally:
                with defer_stop_signals():
                    execution=stop_owned_group(worker) if worker else {'exit_confirmed':False,'errors':['not_started']}
                    write(d/'execution.json',execution)
                    parent=cleanup_browser(d/'browser-pid.json');write(d/'parent-browser-cleanup.json',parent)
                    port={'backend_port_closed':closed()};write(d/'port-check.json',port)
            run={'case_id':spec['case_id'],'route':[o['interface'] for o in spec['operations']],'status':'completed','exit_code':worker.returncode if worker else -1,'timed_out':timed_out,'cleanup_confirmed':execution['exit_confirmed'] and not execution['errors'] and parent['ok'] and port['backend_port_closed'],'reset_sha256':fixture_sha}
            # Validation belongs inside the monotonic branch interval.
            try:
                raw=read(d/'observation.json');run['raw_sha256']=sha(d/'observation.json');reduced=extract(job,channel,raw,run)
                assert sha(d/'reset.sqlite3')==fixture_sha and read(d/'cleanup.json')['ok'] and run['cleanup_confirmed'],'Reset or cleanup not qualified'
            finally:
                ended=time.monotonic();run.update(started_monotonic=began,finished_monotonic=ended,branch_total_s=ended-began);write(d/'run.json',run)
            self.loader(d,job,channel,fixture_sha)
    def load(self,directory,bound):
        job=bound['runtime_job'];dispatch=read(directory/'dispatch.json')
        require(read(directory/'job.json')==job and dispatch=={'binding_sha256':bound['binding_sha256'],'job':job,'profile':self.profile},'Generated dispatch differs')
        require({p.name for p in directory.iterdir() if p.is_dir()}=={'api','ui'},'Branch inventory differs')
        branches={c:self.loader(directory/c,job,c,self.fixture_sha) for c in ('api','ui')}
        return self.compare(job,branches,{c:sha(directory/c/'observation.json') for c in branches})
