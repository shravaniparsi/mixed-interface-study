#!/usr/bin/env python3
"""Execute only the six exposed PetClinic controls under terminal campaign v2."""
import os,shutil,subprocess,sys,time,urllib.request
from pathlib import Path
from petclinic_terminal_campaign import ROOT,CONTROL,REGISTRY,RUNNER,BINDING,read,write,sha,contract,validate_job,read_job
sys.path.insert(0,str(ROOT/'scripts/ci'))
from owned_process_scope import interruption_as_exception,defer_stop_signals,stop_owned_group
from mixed_interface.campaign_v2 import drive
SOURCES=['.github/workflows/applications.yml','scripts/ci/run_applications.sh','scripts/ci/prepare_petclinic.py',CONTROL,REGISTRY,RUNNER,BINDING,'scripts/petclinic_terminal_campaign.py','scripts/run_petclinic_terminal_campaign.py','scripts/validate_petclinic_terminal_campaign.py','scripts/petclinic_terminal_outcomes.py','scripts/summarize_petclinic_integrity_components.py','scripts/summarize_petclinic_oracle_components.py','scripts/validate_petclinic_integrity.py','scripts/petclinic_integrity.mjs','scripts/petclinic_response_capture.mjs','scripts/petclinic_cleanup.mjs','scripts/ci/owned_process_scope.py','src/mixed_interface/terminal_outcomes.py','src/mixed_interface/campaign_v2.py','src/mixed_interface/repetition.py','protocol/petclinic-terminal-dispatch-v2.md']

def main():
    artifact=Path(os.environ['CI_ARTIFACT_DIR']);runtime=Path(os.environ['STUDY_RUNTIME'])/'petclinic'
    output=artifact/'petclinic-terminal-controls';output.mkdir(exist_ok=False)
    c=contract();bootstrap=read(artifact/'petclinic-bootstrap.json')
    cert={'source_commit':os.environ['GITHUB_SHA'],'plan':c['plan'],'sources':{n:sha(ROOT/n) for n in SOURCES},'environment':{},'primary_freeze_complete':False,'pair_timeout_s':120,'campaign_timeout_s':480,'scope':'Six previously exposed controls; no new boundaries; no resume'}
    for n in SOURCES:
        dest=output/'sources'/n;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/n,dest)
    for n in ('petclinic-bootstrap.json','runtime-versions.json','browser.json'):
        shutil.copyfile(artifact/n,output/n);cert['environment'][n]=sha(output/n)
    write(output/'plan.json',cert)
    frontend=None;cleanup={}
    with interruption_as_exception():
        try:
            with (output/'frontend.log').open('x') as log:
                frontend=subprocess.Popen(['node','node_modules/@angular/cli/bin/ng.js','serve','--host','127.0.0.1','--port','19766'],cwd=runtime/'frontend',stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            deadline=time.monotonic()+90
            while True:
                if frontend.poll() is not None:raise RuntimeError('Frontend exited during startup')
                try:
                    with urllib.request.urlopen('http://127.0.0.1:19766',timeout=1) as response:
                        if response.status==200:break
                except (OSError,TimeoutError):pass
                if time.monotonic()>deadline:raise TimeoutError('Frontend readiness deadline')
                time.sleep(.25)
            def execute(job):
                validate_job(job)
                for n,h in cert['sources'].items():
                    if sha(ROOT/n)!=h:raise ValueError('Live source changed: '+n)
                d=output/job['job_id'];d.mkdir(exist_ok=False);write(d/'job.json',job)
                command=['node',str(ROOT/RUNNER),'--registry',str(ROOT/REGISTRY),'--controls',str(ROOT/CONTROL),'--job',str(d/'job.json'),'--output',str(d/'run'),'--jar',bootstrap['jar'],'--java',os.environ['JAVA_HOME']+'/bin/java','--playwright-module',os.environ['PLAYWRIGHT_MODULE_PATH'],'--chrome-executable',os.environ['CHROME_EXECUTABLE']]
                write(d/'dispatch.json',{'job':job,'command':command});child=None;execution={}
                try:
                    with (d/'runner.log').open('x') as log:
                        child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);child.wait(timeout=120)
                finally:
                    with defer_stop_signals():
                        if child is not None:execution=stop_owned_group(child)
                        write(d/'execution.json',execution)
                result=read_job(d,job,execution);write(d/'observations.json',result);return result['terminal']
            state=drive(c['plan'],execute,lambda s:write(output/'campaign.json',s))
        finally:
            with defer_stop_signals():
                if frontend is not None:cleanup['frontend']=stop_owned_group(frontend)
                write(output/'cleanup.json',cleanup)
    if not cleanup['frontend']['exit_confirmed'] or cleanup['frontend']['errors']:raise RuntimeError('Frontend cleanup failed')
    if state['status']!='completed_observations':raise RuntimeError('Campaign did not complete')
    print('Completed PetClinic terminal control campaign')
if __name__=='__main__':main()
