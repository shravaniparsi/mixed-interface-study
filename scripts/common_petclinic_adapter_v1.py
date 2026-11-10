"""PetClinic adapter for the common fresh-attempt bridge; v4 raw loader retained."""
import os,subprocess,sys
from petclinic_timed_jobs_v4 import ROOT,CONTROL,REGISTRY,RUNNER,read,write,validate_job,read_job
sys.path.insert(0,str(ROOT/'scripts/ci'))
from owned_process_scope import defer_stop_signals,stop_owned_group

class Adapter:
    profile='petclinic_timing_v1'
    def __init__(self,bootstrap=None):self.bootstrap=bootstrap
    def execute(self,d,bound):
        job=bound['runtime_job'];batch=bound['runtime_context']['batch'];validate_job(job,batch)
        write(d/'job.json',job)
        command=['node',str(ROOT/RUNNER),'--registry',str(ROOT/REGISTRY),'--controls',str(ROOT/CONTROL),'--batch',batch,
                 '--job',str(d/'job.json'),'--output',str(d/'run'),'--jar',self.bootstrap['jar'],
                 '--java',os.environ['JAVA_HOME']+'/bin/java','--playwright-module',os.environ['PLAYWRIGHT_MODULE_PATH'],
                 '--chrome-executable',os.environ['CHROME_EXECUTABLE']]
        write(d/'dispatch.json',{'binding_sha256':bound['binding_sha256'],'job':job,'batch':batch,'command':command})
        child=None;execution={}
        try:
            with (d/'runner.log').open('x') as log:
                child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
                child.wait(timeout=120)
        finally:
            with defer_stop_signals():
                if child is not None:execution=stop_owned_group(child)
                write(d/'execution.json',execution)
    def load(self,d,bound):
        from mixed_interface.repetition import require
        dispatch=read(d/'dispatch.json');job=bound['runtime_job'];batch=bound['runtime_context']['batch']
        require(dispatch['binding_sha256']==bound['binding_sha256'] and dispatch['job']==job and dispatch['batch']==batch,'Runtime dispatch differs')
        return read_job(d,job,read(d/'execution.json'),batch)
