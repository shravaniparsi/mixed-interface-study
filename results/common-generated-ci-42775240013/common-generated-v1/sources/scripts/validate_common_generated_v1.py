#!/usr/bin/env python3
"""Independent raw replay of common generated execution and differing job identities."""
import sys,json
from pathlib import Path
from common_generated_qualification_v1 import plan,drive
from common_generated_adapter_v1 import Adapter
from mixed_interface.common_execution_v1 import read,sha,replay
from mixed_interface.repetition import require

def validate(root):
    from run_common_generated_v1 import SOURCES,ROOT,BINDINGS
    root=Path(root);cert=read(root/'plan.json');report=read(root/'report.json');campaign=read(root/'campaign.json')
    require(cert['plan']==plan() and set(cert['sources'])==set(SOURCES),'Source or selection differs')
    for s,h in cert['sources'].items():require(sha(root/'sources'/s)==h==sha(ROOT/s),'Executed source differs: '+s)
    require(cert['worker_timeout_s']==80 and cert['outer_timeout_s']==600 and cert['primary_freeze_complete'] is False,'Budget/scope differs')
    bootstrap=read(root/'realworld-bootstrap.json')
    require(bootstrap['status']=='prepared_not_started' and bootstrap['application_source_modified'] is False,'Bootstrap differs')
    require(bootstrap['backend_commit']=='87dd078c883a046f5ff20269df2fb004d8b5f83f' and bootstrap['frontend_commit']=='b14ba5011cf9cc97babfcd7ca99dcfbb058862e7','Application revision differs')
    require(report['status']==campaign['status'] and report['status'] in ('completed_bounded_diagnostic','halted_terminal_outcome') and report['new_primary_samples']==0 and report['primary_freeze_complete'] is False,'Run incomplete or promoted')
    cleanup=report['frontend_cleanup'];require(cleanup['exit_confirmed'] and not cleanup['errors'],'Frontend cleanup incomplete')
    jobs=plan()['preflight']['campaign']['schedule']['initial_jobs'];ids=campaign['completed']
    require(ids==campaign['started']==report['completed_jobs']==[j['job_id'] for j in jobs][:len(ids)],'Attempt inventory differs')
    require({p.name for p in root.iterdir() if p.is_dir() and p.name!='sources'}==set(ids),'Extra attempt directory')
    results=[];values={};attempts=[];fixture_sha=sha(root/'fixture.sqlite3')
    for job in jobs[:len(ids)]:
        b=next(b for b in BINDINGS['bindings'] if b['pair_id']==job['pair_id']);d=root/job['job_id']
        value=replay(d,BINDINGS,plan()['preflight'],job,Adapter(b['profile'],fixture_sha=fixture_sha),cert['run_identity'])
        require(job['job_id']!=b['runtime_job']['job_id'],'Qualification must exercise differing identities')
        attempts.append(read(d/'started.json')['attempt_id']);values[job['job_id']]=value
        results.append({'job_id':job['job_id'],'runtime_job_id':b['runtime_job']['job_id'],'pair_id':job['pair_id'],
            'attempt_id':attempts[-1],'terminal_kind':value['kind'],
            'branch_total_s':{c:read(d/'runtime'/c/'run.json')['branch_total_s'] for c in ('api','ui')}})
    require(len(attempts)==len(set(attempts)),'Attempt identity reused')
    visited=[]
    def execute(job):visited.append(job['job_id']);return values[job['job_id']]
    require(drive(execute,lambda _:None)==campaign and visited==ids,'Ledger differs')
    return {'verified':True,'source_commit':cert['source_commit'],'run_identity':cert['run_identity'],'status':campaign['status'],
            'pairs':len(results),'branches':len(results)*2,'results':results,'new_primary_samples':0,'primary_freeze_complete':False}
if __name__=='__main__':print(json.dumps(validate(sys.argv[1]),indent=2))
