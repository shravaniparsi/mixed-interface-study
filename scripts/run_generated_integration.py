#!/usr/bin/env python3
"""Validate real generated cases, calibrate controls, then exercise a common budget."""
import argparse
from dataclasses import replace
import datetime as dt
import hashlib
import json
import os
from pathlib import Path
import shutil
import signal
import socket
import statistics
import subprocess
import sys
import tempfile
import time
from urllib.request import Request,urlopen

PROJECT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(PROJECT/'src'))
from mixed_interface import generate_registry,ExecutionFeedback,Strategy
from mixed_interface.runtime import CaseExecution,run_registry
from run_realworld_pilot import sha,tree_sha,wait_http,stop
from realworld_case_worker import cleanup_browser

def dump(path,data):Path(path).write_text(json.dumps(data,indent=2)+'\n')
def object_sha(data):return hashlib.sha256(json.dumps(data,sort_keys=True,separators=(',',':')).encode()).hexdigest()

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ['subject','python','node','runtime-root']:parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--phase',choices=['deadline-smoke','controls','validation','all'],default='all')
    parser.add_argument('--calibration-gate',type=Path,help='Wait for this task-owned marker before timings, so other controlled study processes have stopped.')
    args=parser.parse_args();subject=args.subject.resolve();frontend=subject/'fronts/vue3-realworld-example-app'
    def interrupted(signum,frame):raise KeyboardInterrupt('controller interrupted')
    signal.signal(signal.SIGTERM,interrupted)
    registry=generate_registry(json.loads((PROJECT/'manifests/realworld-article-generation-v1.json').read_text()))
    assert len(registry.cases)==18
    frozen_pool=json.loads((PROJECT/'manifests/realworld-article-generated-pool-v1.json').read_text())
    assert json.loads(registry.to_json())==frozen_pool,'Regenerated pool differs from frozen pool'
    for port in [18765,18766]:
        with socket.socket() as sock:
            if sock.connect_ex(('127.0.0.1',port))==0:raise RuntimeError('Study port occupied: '+str(port))
    run_id=dt.datetime.now(dt.timezone.utc).strftime('generated-integration-%Y%m%dT%H%M%SZ')
    root=Path(tempfile.mkdtemp(prefix=run_id+'-',dir=args.runtime_root));evidence=root/'evidence';evidence.mkdir()
    output=PROJECT/'results'/run_id;database=root/'active.sqlite3';fixture=root/'fixture.sqlite3'
    (evidence/'original-pool.json').write_text(registry.to_json())
    source_paths=[Path(__file__),Path(__file__).with_name('realworld_generated_case.mjs'),Path(__file__).with_name('response_capture.mjs'),Path(__file__).with_name('realworld_case_worker.py'),Path(__file__).with_name('run_realworld_pilot.py')]
    source_paths.append(PROJECT/'protocol/runtime-integration-v1.md')
    source_paths+=list((PROJECT/'src/mixed_interface').glob('*.py'))
    hashes={}
    for path in source_paths:
        destination=evidence/'sources'/path.name;destination.parent.mkdir(exist_ok=True);shutil.copyfile(path,destination);hashes[path.name]=sha(path)
    case_runner=root/'realworld_generated_case.mjs';worker=root/'realworld_case_worker.py'
    shutil.copyfile(Path(__file__).with_name(case_runner.name),case_runner);shutil.copyfile(Path(__file__).with_name(worker.name),worker)
    shutil.copyfile(Path(__file__).with_name('response_capture.mjs'),root/'response_capture.mjs')
    report={'kind':'development_runtime_integration','run_id':run_id,'status':'running','phase':args.phase,'source_sha256':hashes,
            'protocol_sha256':sha(PROJECT/'protocol/runtime-integration-v1.md'),'original_pool_sha256':sha(evidence/'original-pool.json'),
            'validation':[],'calibration':[],'sessions':[],'cash_usd':0,'cleanup_reserve_s':1.0,
            'not_a_method_effectiveness_experiment':True}
    backend=preview=None;handles=[];setup_start=time.monotonic()
    def start_backend():
        log=open(evidence/'setup-backend.log','w');handles.append(log)
        process=subprocess.Popen([str(args.python),'manage.py','runserver','127.0.0.1:18765','--noreload'],cwd=subject,env=env,stdout=log,stderr=subprocess.STDOUT)
        try:wait_http('http://127.0.0.1:18765/api/tags',process)
        except Exception:stop(process);raise
        return process
    def terminate_group(process):
        if process.poll() is None:
            try:os.killpg(process.pid,signal.SIGTERM)
            except ProcessLookupError:return
            try:process.wait(timeout=.8)
            except subprocess.TimeoutExpired:
                try:os.killpg(process.pid,signal.SIGKILL)
                except ProcessLookupError:pass
                process.wait(timeout=.5)
    counter=0
    def execute(case,remaining,group):
        nonlocal counter
        deadline=time.monotonic()+remaining;counter+=1
        directory=evidence/group/f'{counter:04d}-{hashlib.sha256(case.case_id.encode()).hexdigest()[:12]}';directory.mkdir(parents=True)
        case_file=directory/'generated-case.json';dump(case_file,case.to_dict())
        remaining=deadline-time.monotonic()
        detail={'evidence':str(directory.relative_to(evidence)),'cleanup_reserve_s':1.0}
        if remaining<=1.0:return CaseExecution('timeout',None,details={**detail,'reason':'not_spawned_cleanup_reserve'})
        with open(directory/'worker.log','w') as log:
            process=subprocess.Popen([str(args.python),str(worker),'--environment',str(environment_file),'--case',str(case_file),'--output',str(directory)],env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
            timed_out=False
            try:process.wait(timeout=max(.01,deadline-time.monotonic()-1.0))
            except subprocess.TimeoutExpired:timed_out=True;terminate_group(process)
            except BaseException:terminate_group(process);raise
            finally:
                cleanup=cleanup_browser(directory/'browser-pid.json');dump(directory/'parent-browser-cleanup.json',cleanup)
        if not cleanup['ok']:return CaseExecution('error',None,details={**detail,'reason':'browser_cleanup_unconfirmed','cleanup':cleanup})
        with socket.socket() as sock:
            if sock.connect_ex(('127.0.0.1',18765))==0:return CaseExecution('error',None,details={**detail,'reason':'backend_cleanup_failed'})
        if timed_out:return CaseExecution('timeout',None,details={**detail,'reason':'external_process_deadline'})
        path=directory/'observation.json'
        if process.returncode!=0 or not path.exists():return CaseExecution('error',None,details={**detail,'reason':'worker_failed','exit_code':process.returncode})
        obs=json.loads(path.read_text())
        if obs['case_id']!=case.case_id or obs['status']!='completed':return CaseExecution('error',None,details={**detail,'reason':'invalid_observation'})
        if any(not check['passed'] for check in obs['checks'] if check['name'].endswith('_actual_payload')):
            return CaseExecution('error',None,details={**detail,'reason':'adapter_payload_mismatch'})
        observed=obs['coverage'];fields=[]
        if observed['data_consumed']:fields.append('article.slug')
        if observed['state_consumed']:fields.append('article.editable_state')
        edges=frozenset(e for e in case.candidate.dependencies if e.field_or_state in fields)
        obligations=frozenset(o for o in case.candidate.obligations if o.dependency in edges)
        feedback=ExecutionFeedback(case.case_id,frozenset(observed['reached_operations']),edges,obligations)
        detail.update(observation_sha256=sha(path),prefix_status=obs['prefix_status'])
        return CaseExecution('completed',obs['application_outcome'],feedback,detail)
    env=dict(os.environ,DEBUG='True',DATABASE_URL='file:'+str(database),TZ='UTC',PYTHONDONTWRITEBYTECODE='1')
    try:
        with open(evidence/'migrate.log','w') as log:subprocess.run([str(args.python),'manage.py','migrate','--noinput'],cwd=subject,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
        backend=start_backend()
        payload={'user':{'username':'pilotresearch','email':'pilot@example.com','password':'Pilot-Research-123!'}}
        request=Request('http://127.0.0.1:18765/api/users',data=json.dumps(payload).encode(),headers={'Content-Type':'application/json'},method='POST')
        with urlopen(request,timeout=10) as r:assert r.status==201
        stop(backend);backend=None;shutil.copyfile(database,fixture)
        config={'subject':str(subject),'python':str(args.python),'node':str(args.node),'case_runner':str(case_runner),'fixture':str(fixture),'database':str(database),'fixture_sha256':sha(fixture)}
        environment_file=root/'environment.json';dump(environment_file,config)
        log=open(evidence/'frontend.log','w');handles.append(log)
        preview=subprocess.Popen([str(args.node),'node_modules/vite/bin/vite.js','preview','--host','127.0.0.1','--port','18766','--strictPort'],cwd=frontend,env=env,stdout=log,stderr=subprocess.STDOUT)
        wait_http('http://127.0.0.1:18766',preview)
        resources={'backend_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=subject,text=True).strip(),
                   'frontend_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=frontend,text=True).strip(),
                   'frontend_dist_sha256':tree_sha(frontend/'dist'),'fixture_sha256':sha(fixture),'source_sha256':hashes,'database':'SQLite','timezone':'UTC'}
        report['resources']=resources;report['common_setup_seconds']=time.monotonic()-setup_start
        if args.phase=='deadline-smoke':
            # Separate engineering check; this subset and budget are never used
            # for the selector comparison or calibration.
            case=next(c for c in registry.cases if c.intervention=='route_only' and all(o.interface=='ui' for o in c.operations))
            smoke_registry=replace(registry,cases=(case,))
            smoke=run_registry(smoke_registry,Strategy.RANDOM,11,3.5,lambda c,remaining:execute(c,remaining,'deadline-smoke'),resource_id='deadline-cleanup-smoke',resource_metadata=resources).to_dict()
            dump(evidence/'deadline-smoke.json',smoke);report['deadline_smoke']=smoke
            assert smoke['stop_reason']=='case_timeout' and not any(c['feedback_credited'] for c in smoke['cases'])
            assert list((evidence/'deadline-smoke').rglob('browser-pid.json')),'Deadline did not exercise browser launch; preserve attempt without claiming browser-timeout validation'
            follow=execute(case,75,'after-deadline-control')
            report['after_deadline_control']={'status':follow.status,'outcome':follow.outcome,'details':follow.details}
            assert follow.status=='completed' and follow.outcome=='passed','Fresh reset/control failed after forced timeout'
        validation_cases=(() if args.phase=='deadline-smoke' else tuple(c for c in registry.cases if c.intervention=='route_only') if args.phase=='controls' else registry.cases)
        if args.phase=='controls':assert len(validation_cases)==4
        for case in validation_cases:
            started=time.monotonic();r=execute(case,75,'validation');entry={'case_id':case.case_id,'route':[o.interface for o in case.operations],'status':r.status,'outcome':r.outcome,'seconds':time.monotonic()-started,'details':r.details}
            report['validation'].append(entry);dump(evidence/'summary.json',report);print(json.dumps({'phase':'validation',**entry}),flush=True)
            if r.status!='completed':raise RuntimeError('Validation adapter failure: '+case.case_id)
        if args.phase=='all':
            wait_started=time.monotonic()
            if args.calibration_gate:
                print(json.dumps({'phase':'awaiting_calibration_gate','path':str(args.calibration_gate)}),flush=True)
                while not args.calibration_gate.exists():
                    if time.monotonic()-wait_started>900:raise TimeoutError('Calibration gate not opened')
                    time.sleep(.25)
            report['outside_budget_gate_wait_seconds']=time.monotonic()-wait_started
            controls=[c for c in registry.cases if c.intervention=='route_only'];assert len(controls)==4
            costs={}
            for repeat in range(2):
                for case in controls:
                    start=time.monotonic();r=execute(case,75,'calibration');seconds=time.monotonic()-start;route='-'.join(o.interface for o in case.operations)
                    assert r.status=='completed' and r.outcome=='passed','Calibration control failed'
                    costs.setdefault(route,[]).append(seconds);report['calibration'].append({'case_id':case.case_id,'route':route,'repeat':repeat+1,'seconds':seconds,'details':r.details})
            medians={route:statistics.median(values) for route,values in costs.items()}
            sidecar={'original_pool_sha256':report['original_pool_sha256'],'method':'median of two valid route controls; no failure labels','route_seconds':medians,'samples':costs}
            dump(evidence/'calibrated-costs.json',sidecar)
            effective=replace(registry,cases=tuple(replace(c,candidate=replace(c.candidate,estimated_cost_s=medians['-'.join(o.interface for o in c.operations)])) for c in registry.cases))
            (evidence/'effective-pool.json').write_text(effective.to_json())
            budget=2*sum(medians.values());report['budget_seconds']=budget;report['cost_sidecar_sha256']=sha(evidence/'calibrated-costs.json')
            setup={'common_setup_seconds':report['common_setup_seconds'],'original_pool_sha256':report['original_pool_sha256'],'cost_sidecar_sha256':report['cost_sidecar_sha256'],'cleanup_reserve_s':1.0,'final_export_outside_budget':True}
            orders=[[Strategy.RANDOM,Strategy.DEPENDENCY_GREEDY,Strategy.ROUTE_GREEDY],[Strategy.DEPENDENCY_GREEDY,Strategy.ROUTE_GREEDY,Strategy.RANDOM],[Strategy.ROUTE_GREEDY,Strategy.RANDOM,Strategy.DEPENDENCY_GREEDY]]
            for seed,order in zip([11,29,47],orders):
                for strategy in order:
                    name=f'seed-{seed}-{strategy.value}';record=run_registry(effective,strategy,seed,budget,lambda case,remaining:execute(case,remaining,'sessions/'+name),resource_id='realworld-local-pinned',setup_metadata=setup,resource_metadata=resources).to_dict()
                    dump(evidence/(name+'.json'),record);report['sessions'].append({'seed':seed,'strategy':strategy.value,'record':name+'.json','stop_reason':record['stop_reason'],'elapsed_s':record['elapsed_s']})
                    dump(evidence/'summary.json',report);print(json.dumps({'phase':'budget_session',**report['sessions'][-1]}),flush=True)
                    if record['stop_reason']=='execution_error' or any(c['callback_status']=='error' for c in record['cases']):
                        raise RuntimeError('Budget session adapter failure (including cleanup failure after deadline)')
            assert len({json.loads((evidence/s['record']).read_text())['hashes']['comparison_context_sha256'] for s in report['sessions']})==1
        report['status']='completed'
    except (Exception,KeyboardInterrupt) as exc:
        report['status']='incomplete';report['error']=type(exc).__name__+': '+str(exc)
    finally:
        stop(backend);stop(preview)
        for handle in handles:handle.close()
        report['finished_at']=dt.datetime.now(dt.timezone.utc).isoformat();dump(evidence/'summary.json',report)
        shutil.copytree(evidence,output);print(json.dumps({'status':report['status'],'summary':str(output/'summary.json'),'error':report.get('error')}),flush=True)
    return 0 if report['status']=='completed' else 1

if __name__=='__main__':raise SystemExit(main())
