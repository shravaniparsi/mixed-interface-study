#!/usr/bin/env python3
"""Bounded generated mutation qualification; preserve semantic halts and every attempt."""
import os,sys,shutil,json,subprocess,time,socket
from pathlib import Path
from urllib.request import Request,urlopen
from realworld_generated_execution_v3 import ROOT,SOURCES,jobs,read,branch
from realworld_generated_mutations_v3 import plan,drive
from realworld_generated_bindings_v1 import case_for,extract
from realworld_generated_loader_v1 import sha
from realworld_generated_terminal_v3 import compare
from realworld_case_worker import cleanup_browser
from run_realworld_pilot import wait_http
sys.path.insert(0,str(ROOT/'scripts/ci'))
from owned_process_scope import stop_owned_group,defer_stop_signals,interruption_as_exception

def write(p,v):Path(p).write_text(json.dumps(v,indent=2)+'\n')
def closed():
    with socket.socket() as s:return s.connect_ex(('127.0.0.1',18765))!=0

def main():
    artifact=Path(os.environ['CI_ARTIFACT_DIR']);out=artifact/'realworld-generated-v3';out.mkdir()
    runtime=Path(os.environ['STUDY_RUNTIME'])/'generated-v3';runtime.mkdir()
    bootstrap=read(artifact/'realworld-bootstrap.json');subject=Path(bootstrap['subject']);python=bootstrap['python'];node=bootstrap['node'];frontend=subject/'fronts/vue3-realworld-example-app'
    for name in ('realworld-bootstrap.json','runtime-versions.json','browser.json'):shutil.copyfile(artifact/name,out/name)
    for source in SOURCES:
        dest=out/'sources'/source;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/source,dest)
    for repo,expected in ((subject,bootstrap['backend_commit']),(frontend,bootstrap['frontend_commit'])):
        assert subprocess.check_output(['git','rev-parse','HEAD'],cwd=repo,text=True).strip()==expected
        subprocess.run(['git','diff','--exit-code','HEAD','--'],cwd=repo,check=True,timeout=20)
    write(out/'plan.json',{'jobs':jobs(),'sources':{s:sha(ROOT/s) for s in SOURCES},'source_commit':os.environ['GITHUB_SHA'],'worker_timeout_s':80,'outer_timeout_s':1800,'mutation_plan':plan(),'primary_freeze_complete':False})
    database=runtime/'active.sqlite3';fixture=out/'fixture.sqlite3'
    env=dict(os.environ,DEBUG='True',DATABASE_URL='file:'+str(database),TZ='UTC',PYTHONDONTWRITEBYTECODE='1')
    backend=preview=None;handles=[];report={'status':'incomplete','completed_jobs':[],'new_primary_samples':0,'primary_freeze_complete':False};started=time.monotonic()
    try:
        assert closed(),'Backend port occupied'
        with (out/'migrate.log').open('w') as log:subprocess.run([python,'manage.py','migrate','--noinput'],cwd=subject,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
        def launch(cmd,cwd,name):
            log=(out/name).open('w');handles.append(log)
            return subprocess.Popen(cmd,cwd=cwd,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        backend=launch([python,'manage.py','runserver','127.0.0.1:18765','--noreload'],subject,'setup-backend.log');wait_http('http://127.0.0.1:18765/api/tags',backend)
        request=Request('http://127.0.0.1:18765/api/users',data=json.dumps({'user':{'username':'pilotresearch','email':'pilot@example.com','password':'Pilot-Research-123!'}}).encode(),headers={'Content-Type':'application/json'},method='POST')
        with urlopen(request,timeout=10) as response:assert response.status==201
        cleanup=stop_owned_group(backend);assert cleanup['exit_confirmed'] and not cleanup['errors'];backend=None
        shutil.copyfile(database,fixture);fixture_sha=sha(fixture)
        config={'subject':str(subject),'python':python,'node':node,'case_runner':str(ROOT/'scripts/realworld_generated_case.mjs'),'fixture':str(fixture),'database':str(database),'fixture_sha256':fixture_sha}
        write(runtime/'environment.json',config)
        preview=launch([node,'node_modules/vite/bin/vite.js','preview','--host','127.0.0.1','--port','18766','--strictPort'],frontend,'frontend.log');wait_http('http://127.0.0.1:18766',preview)
        report['common_setup_s']=time.monotonic()-started
        def execute(job):
            directory=out/job['job_id'];directory.mkdir();write(directory/'job.json',job);branches={};evidence={}
            for declared in job['branches']:
                channel=declared['channel'];spec=case_for(job,channel);d=directory/channel;d.mkdir();write(d/'case.json',spec)
                began=time.monotonic();worker=None;timed_out=False
                try:
                    with (d/'worker.log').open('w') as log:
                        worker=subprocess.Popen([python,str(ROOT/'scripts/realworld_generated_worker_v2.py'),'--environment',str(runtime/'environment.json'),'--case',str(d/'case.json'),'--output',str(d)],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
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
                branches[channel]=branch(d,job,channel,fixture_sha);evidence[channel]=sha(d/'observation.json')
            result=compare(job,branches,evidence);write(directory/'observations.json',result)
            return result
        campaign=drive(execute,lambda value:write(out/'campaign.json',value))
        report['status']=campaign['status']
        report['completed_jobs']=campaign['completed_jobs']
    except BaseException as error:
        report['error']=type(error).__name__+': '+str(error)
    finally:
        with defer_stop_signals():
            for label,process in [('setup_backend',backend),('frontend',preview)]:
                if process is not None:
                    result=stop_owned_group(process);report[label+'_cleanup']=result
                    if not result['exit_confirmed'] or result['errors']:report['status']='incomplete'
            for log in handles:log.close()
            write(out/'report.json',report)
    return 0 if report['status']=='completed_bounded_diagnostic' else 1

if __name__=='__main__':
    with interruption_as_exception():raise SystemExit(main())
