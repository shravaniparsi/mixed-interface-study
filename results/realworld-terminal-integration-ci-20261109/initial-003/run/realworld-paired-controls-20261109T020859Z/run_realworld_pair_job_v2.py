#!/usr/bin/env python3
"""Execute one validated RealWorld baseline job; preserve non-passing observations."""
import argparse
from collections import Counter
import datetime as dt
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
from urllib.request import Request, urlopen

from run_realworld_pilot import sha, tree_sha, wait_http, stop
from realworld_terminal_campaign import validate_job


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['subject','python','node','runtime-root','registry']:
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--job',type=Path,required=True)
    parser.add_argument('--output-root',type=Path,help='Evidence parent directory; defaults to the project results directory.')
    args=parser.parse_args()
    job=json.loads(args.job.read_bytes())
    project=Path(__file__).resolve().parents[1]
    subject=args.subject.resolve();frontend=subject/'fronts/vue3-realworld-example-app'
    script=Path(__file__).with_name('realworld_paired_case.mjs')
    registry=json.loads(args.registry.read_text())
    candidate=validate_job(job,registry)
    if sha(args.registry)!=sha(project/'manifests/realworld-paired-controls-v1.json'):raise ValueError('Unregistered control selection')
    selected=[candidate]
    for c in selected:
        if not c['candidate_id'].replace('-','').isalnum(): raise ValueError('Unsafe candidate ID')
    for port in [18765,18766]:
        with socket.socket() as sock:
            if sock.connect_ex(('127.0.0.1',port))==0: raise RuntimeError('Occupied port '+str(port))
    runtime=Path(tempfile.mkdtemp(prefix='boundary-routes-',dir=args.runtime_root))
    database=runtime/'active.sqlite3';snapshot=runtime/'fixture.sqlite3'
    output=(args.output_root or project/'results')/dt.datetime.now(dt.timezone.utc).strftime('realworld-paired-controls-%Y%m%dT%H%M%SZ')
    output.mkdir(exist_ok=False)
    env=dict(os.environ,DEBUG='True',DATABASE_URL='file:'+str(database),TZ='UTC',PYTHONDONTWRITEBYTECODE='1')
    report={'kind':'prospective_runner_engineering_controls','status':'running','started_at':dt.datetime.now(dt.timezone.utc).isoformat(),
            'registry_sha256':sha(args.registry),'job':job,'job_sha256':sha(args.job),'repetitions_per_branch':1,
            'backend_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=subject,text=True).strip(),
            'frontend_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=frontend,text=True).strip(),
            'frontend_dist_sha256':tree_sha(frontend/'dist'),'source_sha256':{},
            'reset':'Backend stopped; identical offline SQLite fixture copied before every independent prefix+continuation branch.',
            'comparison':'One scheduled baseline pair; independent resets; engineering qualification only.',
            'primary_freeze_complete':False, 'source_commit':os.environ.get('GITHUB_SHA'), 'pairs':[],
            'cost_scope':'Branch reset through backend teardown; adapter subspans nested, never added to parent total. Common fixture/frontend setup separate.',
            'normalization':'Generated slugs remain in raw traces and must resolve within each branch; slug text is excluded only from cross-branch business-state equality.',
            'branches':[],'additional_cash_usd':0}
    for source in [Path(__file__),script,Path(__file__).with_name('run_realworld_pilot.py'),Path(__file__).with_name('response_capture.mjs'),Path(__file__).with_name('realworld_integrity.mjs'),Path(__file__).with_name('phase_clock.mjs'),Path(__file__).with_name('realworld_normalization.mjs'),Path(__file__).with_name('validate_realworld_paired_controls.py'),Path(__file__).with_name('summarize_realworld_oracle_components.py'),project/'src/mixed_interface/normalization.py']:
        shutil.copyfile(source,output/source.name);report['source_sha256'][source.name]=sha(source)
    shutil.copyfile(args.registry,output/'registered-candidates.json')
    backend=frontend_process=None;handles=[]
    def save(): (output/'summary.json').write_text(json.dumps(report,indent=2)+'\n')
    def start(label):
        log=open(output/(label+'-backend.log'),'w');handles.append(log)
        process=subprocess.Popen([str(args.python),'manage.py','runserver','127.0.0.1:18765','--noreload'],cwd=subject,env=env,stdout=log,stderr=subprocess.STDOUT)
        try:wait_http('http://127.0.0.1:18765/api/tags',process)
        except Exception:stop(process);raise
        return process
    def fixture_call(path,payload,token=None,method='POST'):
        headers={'Content-Type':'application/json'}
        if token:headers['Authorization']='Token '+token
        request=Request('http://127.0.0.1:18765'+path,data=json.dumps(payload).encode(),method=method,headers=headers)
        with urlopen(request,timeout=10) as response:return json.load(response)
    setup_started=time.monotonic()
    report['schedule']=[{'candidate_id':candidate['candidate_id'],'order':[b['continuation'] for b in job['branches']]}]
    save()
    try:
        with open(output/'migration.log','w') as log:
            subprocess.run([str(args.python),'manage.py','migrate','--noinput'],cwd=subject,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
        backend=start('fixture')
        user=fixture_call('/api/users',{'user':{'username':'pilotresearch','email':'pilot@example.com','password':'Pilot-Research-123!'}})['user'];token=user['token']
        fixture_call('/api/user',{'user':{'bio':'Baseline profile biography.'}},token,'PUT')
        base=fixture_call('/api/articles',{'article':{'title':'Unique fixture article','description':'Fixture description','body':'Fixture body.','tagList':[]}},token)['article']
        duplicate_payload={'article':{'title':'Duplicate fixture title','description':'Duplicate fixture description','body':'Duplicate fixture body.','tagList':[]}}
        first=fixture_call('/api/articles',duplicate_payload,token)['article']
        second=fixture_call('/api/articles',duplicate_payload,token)['article']
        fixture={'base':base,'duplicate_first':first,'duplicate':second}
        fixture_file=output/'fixture-references.json';fixture_file.write_text(json.dumps(fixture,indent=2)+'\n')
        stop(backend);backend=None;shutil.copyfile(database,snapshot);report['fixture_sha256']=sha(snapshot)
        log=open(output/'frontend.log','w');handles.append(log)
        frontend_process=subprocess.Popen([str(args.node),'node_modules/vite/bin/vite.js','preview','--host','127.0.0.1','--port','18766','--strictPort'],cwd=frontend,env=env,stdout=log,stderr=subprocess.STDOUT)
        wait_http('http://127.0.0.1:18766',frontend_process)
        report['common_fixture_frontend_setup_s']=time.monotonic()-setup_started
        for index,candidate in enumerate(selected):
            casefile=runtime/(candidate['candidate_id']+'.json');casefile.write_text(json.dumps(candidate))
            pair_results={}
            for interface in report['schedule'][index]['order']:
                case_id=f'{candidate["candidate_id"]}-{interface}-r1'
                branch={'case_id':case_id,'candidate_id':candidate['candidate_id'],'continuation':interface,'status':'running','timing':[]}
                report['branches'].append(branch)
                started=time.monotonic();at=started;active_phase='reset'
                def mark(phase):
                    nonlocal at
                    end=time.monotonic();branch['timing'].append({'phase':phase,'start_s':at-started,'end_s':end-started});at=end
                try:
                    shutil.copyfile(snapshot,database);reset_hash=sha(database)
                    assert reset_hash==report['fixture_sha256'];branch['reset_sha256']=reset_hash;mark('reset');active_phase='backend_startup'
                    backend=start(case_id);mark('backend_startup');active_phase='adapter_process'
                    result_file=output/(case_id+'.json')
                    try:
                        with open(output/(case_id+'-runner.log'),'w') as log:
                            command=[str(args.node),str(script),'--case',str(casefile),'--fixture',str(fixture_file),'--continuation',interface,'--output',str(result_file)]
                            completed=subprocess.run(command,cwd=subject,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=90)
                    finally:
                        mark('adapter_process');active_phase='backend_teardown'
                        stop(backend);branch['backend_exit_confirmed']=backend.poll() is not None;backend=None;mark('backend_teardown');active_phase='parent_evidence_validation'
                    result=json.loads(result_file.read_text())
                    branch.update(evidence=result_file.name,exit_code=completed.returncode,prefix_status=result['observations']['prefix_status'])
                    if completed.returncode!=0 or result['execution_status']!='completed':raise RuntimeError('Incomplete adapter')
                    spans=result['timing']['spans']
                    if any(s['end_s']<s['start_s'] for s in spans) or any(a['end_s']!=b['start_s'] for a,b in zip(spans,spans[1:])):raise RuntimeError('Invalid adapter timing')
                    parent_span=next(x for x in branch['timing'] if x['phase']=='adapter_process')
                    branch['adapter_uninstrumented_process_s']=parent_span['end_s']-parent_span['start_s']-result['timing']['total_s']
                    if branch['adapter_uninstrumented_process_s']<0:raise RuntimeError('Adapter timing exceeds parent interval')
                    pair_results[interface]=result;branch['status']='completed'
                except Exception as error:
                    branch['status']='failed';branch['error']=str(error);raise
                finally:
                    mark(active_phase);branch['total_s']=at-started;save()
        report['status']='completed'
        report['outcome_counts']=dict(Counter(b['status'] for b in report['branches']))
    except Exception as exc:
        report['status']='incomplete_environment_or_runner_error';report['error']=str(exc)
    finally:
        stop(backend);stop(frontend_process)
        report['frontend_exit_confirmed']=frontend_process is None or frontend_process.poll() is not None
        for handle in handles:handle.close()
        report['finished_at']=dt.datetime.now(dt.timezone.utc).isoformat();save()
        print(json.dumps({'status':report['status'],'summary':str(output/'summary.json'),'error':report.get('error')}),flush=True)
    return 0 if report['status']=='completed' else 1


if __name__=='__main__':raise SystemExit(main())
