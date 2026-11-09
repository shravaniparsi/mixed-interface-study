#!/usr/bin/env python3
"""Reconstruct ordered HTTP/SQLite observations without assuming rollback or acceptance policy."""
import json,sys
from pathlib import Path
from realworld_identity_db_state_v1 import sha,project
from run_realworld_identity_database_diagnostic import ROOT,SOURCES,BACKEND


def require(ok,message):
    if not ok:raise ValueError(message)

def read(path):return json.loads(Path(path).read_bytes())


def validate(directory):
    d=Path(directory);report=read(d/'report.json')
    require(report['status']=='completed' and report['backend_commit']==BACKEND and report['application_source_modified'] is False,'Diagnostic execution incomplete or modified')
    require(set(report['sources'])==set(SOURCES),'Source inventory differs')
    for name,h in report['sources'].items():require(sha(d/'sources'/name)==h==sha(ROOT/name),'Source differs: '+name)
    require(set(report['application_sources'])=={'apps/accounts/api.py','apps/accounts/schemas.py','apps/accounts/models.py','apps/articles/api.py','apps/articles/schemas.py'},'Application source inventory differs')
    for name,h in report['application_sources'].items():require(sha(d/'application_sources'/name)==h,'Application source snapshot differs')
    require(sha(d/'bootstrap.json')==report['bootstrap_sha256'],'Bootstrap differs')
    bootstrap=read(d/'bootstrap.json');require(bootstrap['status']=='prepared_not_started' and bootstrap['backend_commit']==BACKEND and bootstrap['python_lock_sha256']==sha(ROOT/'manifests/realworld-python-lock.txt'),'Bootstrap revision/lock differs')
    selection=read(d/'sources/manifests/realworld-identity-database-diagnostic-v1.json');require(report['selection']==selection,'Selection differs')
    registry=read(ROOT/'manifests/realworld-boundary-registry-v1.json');require(selection['registry_sha256']==sha(ROOT/'manifests/realworld-boundary-registry-v1.json'),'Registry differs')
    require([c['candidate_id'] for c in selection['cases']]==['profile-username-null','profile-username-length60','profile-username-length61'] and selection['repetitions']==1,'Unregistered diagnostic selection')
    for c in selection['cases']:require(c==next(v for v in registry['cases'] if v['candidate_id']==c['candidate_id']),'Registered payload or policy differs')
    def snapshot(record):
        name=record['file'];path=d/name
        require(not Path(name).is_absolute() and '..' not in Path(name).parts,'Snapshot path escapes archive')
        require(sha(path)==record['sha256'],'Database snapshot hash differs')
        value=project(path);require(value==record['projection'],'Database projection differs')
        require(value['read_uncommitted']==0 and value['query_only']==1 and not value['foreign_key_violations'],'Unsafe read or foreign-key violation')
        return value
    fixture=snapshot(report['fixture']);require(fixture['user']['username']=='pilotresearch','Baseline username differs')
    require(set(report['article_slugs'])=={a['slug'] for a in fixture['articles']},'Fixture article references differ')
    def cleanup(value):require(value.get('exit_confirmed') is True and not value.get('errors'),'Cleanup unconfirmed')
    cleanup(report['fixture_cleanup'])
    require([c['candidate_id'] for c in report['cases']]==[c['candidate_id'] for c in selection['cases']],'Case order/count differs')
    fixture_trace=report['fixture_trace']
    require([e['sequence'] for e in fixture_trace]==list(range(1,11)) and [e['type'] for e in fixture_trace]==['request','response']*5,'Fixture trace inventory differs')
    expected_fixture=[('POST','/api/users',201),('PUT','/api/user',200)]+[('POST','/api/articles',201)]*3
    for i,(method,path,status) in enumerate(expected_fixture):
        req,res=fixture_trace[2*i:2*i+2]
        require(req['stage']==res['stage']=='fixture' and req['method']==res['method']==method and req['path']==res['path']==path and res['status']==status,'Fixture operation differs')
        if i==0:require(req['payload']=={'user':{'username':'pilotresearch','email':'pilot@example.com','password':'[REDACTED]'}},'Fixture actor differs')
        elif i==1:require(req['payload']=={'user':{'bio':'Baseline profile biography.'}},'Fixture profile differs')
        else:
            require(req['payload']=={'article':{'title':'Unique fixture article' if i==2 else 'Duplicate fixture title','description':'Fixture description','body':'Fixture body.','tagList':[]}},'Fixture article command differs')
            article=res['data']['article'];require(article['slug']==report['article_slugs'][i-2],'Fixture returned reference differs')
            row=next(a for a in fixture['articles'] if a['slug']==article['slug'])
            require(all(row[k]==article[k] for k in ('slug','title','description','body')),'Fixture response/database differs')
    results=[];expected_files={'fixture.sqlite3'}
    for case,spec in zip(report['cases'],selection['cases']):
        require(case['status']=='completed' and case['spec']==spec and case['reset_sha256']==report['fixture']['sha256'],'Case/reset differs')
        cleanup(case['cleanup_before_restart']);cleanup(case['cleanup_final'])
        require(set(case['snapshots'])=={'before','immediate','after_stop','after_restart'},'Snapshot stage inventory differs')
        states={stage:snapshot(record) for stage,record in case['snapshots'].items()}
        for stage,record in case['snapshots'].items():
            require(record['file']==case['candidate_id']+'/'+stage+'.sqlite3','Snapshot case/stage path differs');expected_files.add(record['file'])
        require(states['before']==fixture,'Reset projection differs')
        trace=case['trace'];require([e['sequence'] for e in trace]==list(range(1,len(trace)+1)),'Trace sequence differs')
        def one(kind,stage):
            values=[e for e in trace if e['type']==kind and e['stage']==stage];require(len(values)==1,'Missing/duplicate '+kind+' '+stage);return values[0]
        # No arbitrary GETs or extra writes: rebuild the entire trace event inventory.
        expected=[('backend_started','initial'),('request','login'),('response','login'),('database_snapshot','before'),('request','prefix'),('response','prefix'),('database_snapshot','immediate')]
        for _ in range(4):expected.extend([('request','readback'),('response','readback')])
        expected.extend([('backend_stopped','before_restart'),('database_snapshot','after_stop'),('backend_started','restart')])
        for _ in range(4):expected.extend([('request','restart_readback'),('response','restart_readback')])
        expected.extend([('database_snapshot','after_restart'),('backend_stopped','final')])
        require([(e['type'],e['stage']) for e in trace]==expected,'Diagnostic event order/inventory differs')
        for stage,record in case['snapshots'].items():
            event=one('database_snapshot',stage);require(event['file']==record['file'] and event['sha256']==record['sha256'],'Snapshot event binding differs')
        require(one('backend_stopped','before_restart')['cleanup']==case['cleanup_before_restart'] and one('backend_stopped','final')['cleanup']==case['cleanup_final'],'Cleanup event differs')
        login=one('request','login');login_response=one('response','login')
        require(login['method']=='POST' and login['path']=='/api/users/login' and login['payload']=={'user':{'email':'pilot@example.com','password':'[REDACTED]'}},'Login command differs')
        require(login_response['method']=='POST' and login_response['path']==login['path'] and login_response['status']==200 and login_response['data']['user']['username']=='pilotresearch' and login_response['data']['user']['email']=='pilot@example.com','Login actor differs')
        prefix=one('request','prefix');response=one('response','prefix')
        require(prefix['method']=='PUT' and prefix['path']=='/api/user' and prefix['payload']=={'user':spec['prefix_payload']},'Prefix command differs')
        require(response['method']=='PUT' and response['path']==prefix['path'] and type(response['status']) is int and response['status']==case['prefix_status'],'Prefix response differs')
        readbacks={}
        paths=['/api/user']+['/api/articles/'+s for s in report['article_slugs']]
        for stage in ('readback','restart_readback'):
            requests=[e for e in trace if e['type']=='request' and e['stage']==stage];responses=[e for e in trace if e['type']=='response' and e['stage']==stage]
            require([e['path'] for e in requests]==paths and [e['path'] for e in responses]==paths,'Readback paths differ')
            require(all(e['method']=='GET' and e.get('payload') is None for e in requests) and all(e['method']=='GET' and type(e['status']) is int for e in responses),'Readback method/status differs')
            readbacks[stage]={e['path']:e['status'] for e in responses}
        before=states['before'];immediate=states['immediate'];requested=spec['prefix_payload']['username']
        results.append({'candidate_id':spec['candidate_id'],'prefix_status':response['status'],
            'before_username':before['user']['username'],'immediate_username':immediate['user']['username'],
            'after_stop_username':states['after_stop']['user']['username'],'after_restart_username':states['after_restart']['user']['username'],
            'username_changed':immediate['user']['username']!=before['user']['username'],
            'requested_username_observed':immediate['user']['username']==requested,
            'post_response_state_survives_restart':immediate==states['after_stop']==states['after_restart'],
            'user_primary_key_preserved':all(s['user']['id']==before['user']['id'] for s in states.values()),
            'article_identity_body_ownership_preserved':all(s['articles']==before['articles'] for s in states.values()),
            'selected_state_unchanged':all(s==before for s in states.values()),'readback_statuses':readbacks,
            'requirement_policy':spec['expectation']})
    require({str(p.relative_to(d)) for p in d.rglob('*.sqlite3')}==expected_files,'Unexpected/missing database snapshots')
    return {'verified':True,'scope':'three exposed API-prefix database diagnostics; no frontend or primary-study execution','source_commit':report['source_commit'],'backend_commit':report['backend_commit'],'cases':results,'primary_freeze_complete':False}


if __name__=='__main__':
    d=Path(sys.argv[1]);result=validate(d);(d/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result,indent=2))
