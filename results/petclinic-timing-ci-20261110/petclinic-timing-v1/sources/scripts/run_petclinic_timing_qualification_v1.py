#!/usr/bin/env python3
"""Single bounded exposed timing qualification; retain every attempt, no repeats."""
import os,shutil,subprocess,sys,time,urllib.request
from pathlib import Path
from petclinic_timed_jobs_v4 import ROOT,CONTROL,REGISTRY,RUNNER,read,write,sha,validate_job,read_job
from petclinic_timing_qualification_v1 import plan,drive,PAIR_TIMEOUT_S,OUTER_TIMEOUT_S
from run_petclinic_expanded_campaign import SOURCES as PREVIOUS_SOURCES
sys.path.insert(0,str(ROOT/'scripts/ci'))
from owned_process_scope import interruption_as_exception,defer_stop_signals,stop_owned_group
SOURCES=sorted(set(PREVIOUS_SOURCES+[RUNNER,'scripts/petclinic_branch_cost_v1.mjs',
    'scripts/petclinic_branch_cost_validation_v1.py','scripts/petclinic_timed_jobs_v4.py',
    'scripts/petclinic_timing_qualification_v1.py','scripts/run_petclinic_timing_qualification_v1.py',
    'scripts/validate_petclinic_timing_qualification_v1.py','.github/workflows/petclinic_timing_v1.yml',
    'protocol/petclinic-timing-qualification-v1.md']))

def main():
    artifact=Path(os.environ['CI_ARTIFACT_DIR']);runtime=Path(os.environ['STUDY_RUNTIME'])/'petclinic'
    output=artifact/'petclinic-timing-v1';output.mkdir(exist_ok=False);bootstrap=read(artifact/'petclinic-bootstrap.json')
    cert={'source_commit':os.environ['GITHUB_SHA'],'plan':plan(),'sources':{s:sha(ROOT/s) for s in SOURCES},
          'environment':{},'pair_timeout_s':PAIR_TIMEOUT_S,'outer_timeout_s':OUTER_TIMEOUT_S,
          'primary_freeze_complete':False,'new_primary_samples':0}
    for name in SOURCES:
        dest=output/'sources'/name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,dest)
    for name in ('petclinic-bootstrap.json','runtime-versions.json','browser.json'):
        shutil.copyfile(artifact/name,output/name);cert['environment'][name]=sha(output/name)
    write(output/'plan.json',cert)
    frontend=None;report={'status':'incomplete','new_primary_samples':0,'primary_freeze_complete':False}
    started=time.monotonic()
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
        report['common_frontend_setup_s']=time.monotonic()-started
        def execute(slot):
            job=slot['job'];batch=slot['batch'];validate_job(job,batch)
            for name,h in cert['sources'].items():
                if sha(ROOT/name)!=h:raise ValueError('Source changed: '+name)
            d=output/slot['slot_id'];d.mkdir(exist_ok=False);write(d/'slot.json',slot);write(d/'job.json',job)
            command=['node',str(ROOT/RUNNER),'--registry',str(ROOT/REGISTRY),'--controls',str(ROOT/CONTROL),'--batch',batch,'--job',str(d/'job.json'),'--output',str(d/'run'),'--jar',bootstrap['jar'],'--java',os.environ['JAVA_HOME']+'/bin/java','--playwright-module',os.environ['PLAYWRIGHT_MODULE_PATH'],'--chrome-executable',os.environ['CHROME_EXECUTABLE']]
            write(d/'dispatch.json',{'slot':slot,'command':command});child=None;execution={}
            try:
                with (d/'runner.log').open('x') as log:
                    child=subprocess.Popen(command,stdout=log,stderr=subprocess.STDOUT,start_new_session=True);child.wait(timeout=PAIR_TIMEOUT_S)
            finally:
                with defer_stop_signals():
                    if child is not None:execution=stop_owned_group(child)
                    write(d/'execution.json',execution)
            value=read_job(d,job,execution,batch);write(d/'observations.json',value);return value
        campaign=drive(execute,lambda value:write(output/'campaign.json',value));report['status']=campaign['status']
    except BaseException as e:report['error']=type(e).__name__+': '+str(e)
    finally:
        with defer_stop_signals():
            began=time.monotonic()
            if frontend is not None:
                cleanup=stop_owned_group(frontend);report['frontend_cleanup']=cleanup
                if not cleanup['exit_confirmed'] or cleanup['errors']:report['status']='incomplete'
            report['common_frontend_teardown_s']=time.monotonic()-began;write(output/'report.json',report)
    return 0 if report['status']=='completed_bounded_diagnostic' else 1

if __name__=='__main__':
    with interruption_as_exception():raise SystemExit(main())
