#!/usr/bin/env python3
"""Independent reset/prefix/continuation branches for a registered development pool."""
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


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ['subject','python','node','runtime-root','registry']:
        parser.add_argument('--'+name,type=Path,required=True)
    parser.add_argument('--candidate',action='append',help='Explicit subset for reproduction; does not alter the registered pool.')
    parser.add_argument('--repetitions',type=int,default=1)
    args=parser.parse_args()
    assert args.repetitions>=1
    project=Path(__file__).resolve().parents[1]
    subject=args.subject.resolve();frontend=subject/'fronts/vue3-realworld-example-app'
    script=Path(__file__).with_name('realworld_boundary_case.mjs')
    registry=json.loads(args.registry.read_text())
    selected=[c for c in registry['cases'] if not args.candidate or c['candidate_id'] in args.candidate]
    if not selected: raise ValueError('No selected candidates')
    for c in selected:
        if not c['candidate_id'].replace('-','').isalnum(): raise ValueError('Unsafe candidate ID')
    for port in [18765,18766]:
        with socket.socket() as sock:
            if sock.connect_ex(('127.0.0.1',port))==0: raise RuntimeError('Occupied port '+str(port))
    runtime=Path(tempfile.mkdtemp(prefix='boundary-routes-',dir=args.runtime_root))
    database=runtime/'active.sqlite3';snapshot=runtime/'fixture.sqlite3'
    output=project/'results'/dt.datetime.now(dt.timezone.utc).strftime('realworld-boundaries-%Y%m%dT%H%M%SZ')
    output.mkdir(exist_ok=False)
    env=dict(os.environ,DEBUG='True',DATABASE_URL='file:'+str(database),TZ='UTC',PYTHONDONTWRITEBYTECODE='1')
    report={'kind':'exploratory_boundary_and_continuation_pilot','status':'running','started_at':dt.datetime.now(dt.timezone.utc).isoformat(),
            'registry_sha256':sha(args.registry),'candidate_subset':args.candidate,'repetitions_per_branch':args.repetitions,
            'backend_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=subject,text=True).strip(),
            'frontend_commit':subprocess.check_output(['git','rev-parse','HEAD'],cwd=frontend,text=True).strip(),
            'frontend_dist_sha256':tree_sha(frontend/'dist'),'source_sha256':{},
            'reset':'Backend stopped; identical offline SQLite fixture copied before every independent prefix+continuation branch.',
            'comparison':'Descriptive paired replay, fixed order; no selector or equal-time comparison.',
            'normalization':'Generated slugs remain in raw traces and must resolve within each branch; slug text is excluded only from cross-branch business-state equality.',
            'branches':[],'additional_cash_usd':0}
    for source in [Path(__file__),script,Path(__file__).with_name('run_realworld_pilot.py')]:
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
        for repetition in range(1,args.repetitions+1):
            for candidate in selected:
                casefile=runtime/(candidate['candidate_id']+'.json');casefile.write_text(json.dumps(candidate))
                for interface in candidate['continuations']:
                    case_id=f'{candidate["candidate_id"]}-{interface}-r{repetition}'
                    shutil.copyfile(snapshot,database);reset_hash=sha(database);assert reset_hash==report['fixture_sha256']
                    started=time.monotonic();backend=start(case_id)
                    result_file=output/(case_id+'.json')
                    with open(output/(case_id+'-runner.log'),'w') as log:
                        command=[str(args.node),str(script),'--case',str(casefile),'--fixture',str(fixture_file),'--continuation',interface,'--output',str(result_file)]
                        completed=subprocess.run(command,cwd=subject,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=90)
                    stop(backend);backend=None
                    result=json.loads(result_file.read_text()) if result_file.exists() else {}
                    branch={'case_id':case_id,'candidate_id':candidate['candidate_id'],'continuation':interface,'repetition':repetition,
                            'reset_sha256':reset_hash,'execution_status':result.get('execution_status','missing_result'),
                            'prefix_status':result.get('observations',{}).get('prefix_status'),
                            'continuation_outcome':result.get('observations',{}).get('continuation_outcome'),
                            'exit_code':completed.returncode,'seconds_including_backend_restart':round(time.monotonic()-started,3),'evidence':result_file.name}
                    report['branches'].append(branch);save();print(json.dumps(branch),flush=True)
                    if completed.returncode!=0:raise RuntimeError('Runner failure, preserved evidence: '+case_id)
        report['status']='completed'
        report['outcome_counts']=dict(Counter(b['continuation_outcome'] for b in report['branches']))
    except Exception as exc:
        report['status']='incomplete_environment_or_runner_error';report['error']=str(exc)
    finally:
        stop(backend);stop(frontend_process)
        for handle in handles:handle.close()
        report['finished_at']=dt.datetime.now(dt.timezone.utc).isoformat();save()
        print(json.dumps({'status':report['status'],'summary':str(output/'summary.json'),'error':report.get('error')}),flush=True)
    return 0 if report['status']=='completed' else 1


if __name__=='__main__':raise SystemExit(main())
