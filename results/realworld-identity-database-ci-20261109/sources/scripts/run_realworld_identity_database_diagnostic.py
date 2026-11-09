#!/usr/bin/env python3
"""Isolated committed-state diagnostic; never resumes the halted continuation campaign."""
import json,os,shutil,socket,subprocess,sys,time
from pathlib import Path
from urllib.request import Request,urlopen
from urllib.error import HTTPError
import hashlib
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts/ci'))
from run_realworld_pilot import wait_http
from owned_process_scope import stop_owned_group,interruption_as_exception,defer_stop_signals
from realworld_identity_db_state_v1 import backup,sha
SOURCES=['manifests/realworld-boundary-registry-v1.json','.github/workflows/realworld_identity_db.yml','scripts/run_realworld_identity_database_diagnostic.py','scripts/validate_realworld_identity_database_diagnostic.py','scripts/realworld_identity_db_state_v1.py','scripts/ci/prepare_realworld_diagnostic.py','scripts/ci/prepare_realworld.py','scripts/ci/owned_process_scope.py','scripts/run_realworld_pilot.py','manifests/realworld-python-lock.txt','manifests/realworld-identity-database-diagnostic-v1.json','protocol/realworld-identity-database-diagnostic-v1.md']
BACKEND='87dd078c883a046f5ff20269df2fb004d8b5f83f'


def write(path,value):Path(path).write_text(json.dumps(value,indent=2)+'\n')
def clean(value):
    if isinstance(value,dict):return {k:'[REDACTED]' if k.lower() in ('password','token','authorization') else clean(v) for k,v in value.items()}
    if isinstance(value,list):return [clean(v) for v in value]
    return value


def main():
    output=Path(os.environ['CI_ARTIFACT_DIR'])/'identity-database-diagnostic';output.mkdir(exist_ok=False)
    runtime=Path(os.environ['STUDY_RUNTIME'])/'identity-db';runtime.mkdir(exist_ok=False)
    subject=Path(os.environ['STUDY_RUNTIME'])/'realworld/realworld-django-ninja';python=Path(os.environ['STUDY_RUNTIME'])/'realworld/venv/bin/python'
    with socket.socket() as sock:
        if sock.connect_ex(('127.0.0.1',18765))==0:raise RuntimeError('Diagnostic port occupied')
    revision=subprocess.check_output(['git','rev-parse','HEAD'],cwd=subject,text=True).strip()
    if revision!=BACKEND:raise ValueError('Backend revision differs')
    subprocess.run(['git','diff','--exit-code','HEAD','--'],cwd=subject,check=True)
    selection=json.loads((ROOT/'manifests/realworld-identity-database-diagnostic-v1.json').read_bytes())
    report={'status':'running','source_commit':os.environ.get('GITHUB_SHA'),'backend_commit':revision,'selection':selection,'sources':{n:sha(ROOT/n) for n in SOURCES},'cases':[],'fixture_trace':[],'primary_freeze_complete':False,'frontend_executed':False}
    for name in SOURCES:
        target=output/'sources'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(ROOT/name,target)
    app_sources={}
    for name in ['apps/accounts/api.py','apps/accounts/schemas.py','apps/accounts/models.py','apps/articles/api.py','apps/articles/schemas.py']:
        target=output/'application_sources'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(subject/name,target);app_sources[name]=sha(target)
    report['application_sources']=app_sources
    shutil.copyfile(Path(os.environ['CI_ARTIFACT_DIR'])/'diagnostic-bootstrap.json',output/'bootstrap.json');report['bootstrap_sha256']=sha(output/'bootstrap.json')
    database=runtime/'active.sqlite3';env=dict(os.environ,DEBUG='True',DATABASE_URL='file:'+str(database),TZ='UTC',PYTHONDONTWRITEBYTECODE='1')
    process=None;handles=[];active=None;token=None
    def save():write(output/'report.json',report)
    def event(trace,kind,**values):trace.append({'sequence':len(trace)+1,'type':kind,**clean(values)});save();return trace[-1]['sequence']
    def start(label):
        nonlocal process
        log=(output/(label+'-backend.log')).open('w');handles.append(log)
        process=subprocess.Popen([str(python),'manage.py','runserver','127.0.0.1:18765','--noreload'],cwd=subject,env=env,stdout=log,stderr=subprocess.STDOUT,start_new_session=True)
        wait_http('http://127.0.0.1:18765/api/tags',process)
    def stop():
        nonlocal process
        with defer_stop_signals():
            if process is None:return None
            value=stop_owned_group(process);process=None
            if not value.get('exit_confirmed') or value.get('errors'):raise RuntimeError('Owned backend cleanup not confirmed')
            return value
    def request(trace,stage,method,path,payload=None):
        event(trace,'request',stage=stage,method=method,path=path,payload=payload)
        headers={'Content-Type':'application/json'}
        if token:headers['Authorization']='Token '+token
        req=Request('http://127.0.0.1:18765'+path,data=None if payload is None else json.dumps(payload).encode(),headers=headers,method=method)
        try:response=urlopen(req,timeout=12)
        except HTTPError as error:response=error
        with response:
            body=response.read();status=response.status
        try:data=json.loads(body)
        except (ValueError,UnicodeDecodeError):data={'non_json':True,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()}
        event(trace,'response',stage=stage,method=method,path=path,status=status,data=data)
        return status,data
    def snap(case,stage):
        target=output/case['candidate_id']/(stage+'.sqlite3');value=backup(database,target);value['file']=str(target.relative_to(output));case['snapshots'][stage]=value
        event(case['trace'],'database_snapshot',stage=stage,file=value['file'],sha256=value['sha256'])
    save()
    try:
        with (output/'migration.log').open('w') as log:subprocess.run([str(python),'manage.py','migrate','--noinput'],cwd=subject,env=env,stdout=log,stderr=subprocess.STDOUT,check=True,timeout=60)
        start('fixture')
        status,data=request(report['fixture_trace'],'fixture','POST','/api/users',{'user':{'username':'pilotresearch','email':'pilot@example.com','password':'Pilot-Research-123!'}})
        if status!=201:raise RuntimeError('Fixture user creation failed')
        token=data['user']['token']
        status,_=request(report['fixture_trace'],'fixture','PUT','/api/user',{'user':{'bio':'Baseline profile biography.'}})
        if status!=200:raise RuntimeError('Fixture profile initialization failed')
        articles=[]
        for i in range(3):
            title='Unique fixture article' if i==0 else 'Duplicate fixture title'
            status,data=request(report['fixture_trace'],'fixture','POST','/api/articles',{'article':{'title':title,'description':'Fixture description','body':'Fixture body.','tagList':[]}})
            if status!=201:raise RuntimeError('Fixture article creation failed')
            articles.append(data['article'])
        report['fixture_cleanup']=stop();report['fixture']=backup(database,output/'fixture.sqlite3');report['article_slugs']=[a['slug'] for a in articles];save()
        for spec in selection['cases']:
            for name,h in report['sources'].items():
                if sha(ROOT/name)!=h:raise ValueError('Source changed during diagnostic')
            shutil.copyfile(output/'fixture.sqlite3',database);token=None
            case={'candidate_id':spec['candidate_id'],'spec':spec,'reset_sha256':sha(database),'snapshots':{},'trace':[],'status':'running'};report['cases'].append(case);active=case
            (output/case['candidate_id']).mkdir(exist_ok=False);save();start(case['candidate_id'])
            event(case['trace'],'backend_started',stage='initial')
            status,data=request(case['trace'],'login','POST','/api/users/login',{'user':{'email':'pilot@example.com','password':'Pilot-Research-123!'}})
            if status!=200 or data['user']['username']!='pilotresearch':raise RuntimeError('Fixture actor login failed')
            token=data['user']['token'];snap(case,'before')
            status,_=request(case['trace'],'prefix','PUT','/api/user',{'user':spec['prefix_payload']});case['prefix_status']=status
            snap(case,'immediate')
            for path in ['/api/user']+['/api/articles/'+s for s in report['article_slugs']]:request(case['trace'],'readback','GET',path)
            cleanup=stop();case['cleanup_before_restart']=cleanup;event(case['trace'],'backend_stopped',stage='before_restart',cleanup=cleanup)
            snap(case,'after_stop');start(case['candidate_id']+'-restart');event(case['trace'],'backend_started',stage='restart')
            for path in ['/api/user']+['/api/articles/'+s for s in report['article_slugs']]:request(case['trace'],'restart_readback','GET',path)
            snap(case,'after_restart');cleanup=stop();case['cleanup_final']=cleanup;event(case['trace'],'backend_stopped',stage='final',cleanup=cleanup)
            case['status']='completed';active=None;save()
        subprocess.run(['git','diff','--exit-code','HEAD','--'],cwd=subject,check=True)
        report['status']='completed';report['application_source_modified']=False
    except BaseException as error:
        report.update(status='incomplete',error_type=type(error).__name__,error=str(error));raise
    finally:
        try:
            cleanup=stop()
            if cleanup:report['emergency_cleanup']=cleanup
        finally:
            for handle in handles:handle.close()
            save()
    print('Completed three exposed username database diagnostics')


if __name__=='__main__':
    with interruption_as_exception():main()
