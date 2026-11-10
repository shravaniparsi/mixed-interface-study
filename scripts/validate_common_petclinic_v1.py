#!/usr/bin/env python3
"""Reconstruct common identities and runtime semantics from fresh-attempt evidence."""
import sys
from pathlib import Path
from petclinic_timed_jobs_v4 import ROOT,REGISTRY,read,sha
from petclinic_branch_cost_validation_v1 import finite
from common_petclinic_qualification_v1 import plan,drive,PAIR_TIMEOUT_S,OUTER_TIMEOUT_S
from common_petclinic_adapter_v1 import Adapter
from mixed_interface.common_execution_v1 import replay
from mixed_interface.repetition import require

def validate(directory):
    from run_common_petclinic_v1 import SOURCES,BINDINGS
    directory=Path(directory);cert=read(directory/'plan.json');report=read(directory/'report.json');campaign=read(directory/'campaign.json')
    require(cert['plan']==plan() and set(cert['sources'])==set(SOURCES),'Source inventory or plan differs')
    for name,h in cert['sources'].items():require(sha(directory/'sources'/name)==h==sha(ROOT/name),'Source differs: '+name)
    require(set(cert['environment'])=={'petclinic-bootstrap.json','runtime-versions.json','browser.json'},'Environment inventory differs')
    for name,h in cert['environment'].items():require(sha(directory/name)==h,'Environment differs')
    require(cert['pair_timeout_s']==PAIR_TIMEOUT_S and cert['outer_timeout_s']==OUTER_TIMEOUT_S and cert['new_primary_samples']==0 and cert['primary_freeze_complete'] is False,'Budget or scope differs')
    bootstrap=read(directory/'petclinic-bootstrap.json');registry=read(ROOT/REGISTRY)
    require(bootstrap['source_modified'] is False and bootstrap['commits']=={'backend':registry['backend_commit'],'frontend':registry['frontend_commit']} and bootstrap['native_backend_verify']==bootstrap['native_frontend_test_ci']=='passed','Bootstrap differs')
    require(report['status']==campaign['status'] and report['status'] in ('completed_bounded_diagnostic','halted_terminal_outcome'),'Executor failure not qualified')
    require(report['new_primary_samples']==0 and report['primary_freeze_complete'] is False,'Report promoted')
    cleanup=report['frontend_cleanup'];require(cleanup['exit_confirmed'] is True and not cleanup['errors'],'Frontend cleanup unconfirmed')
    require(finite(report['common_frontend_setup_s']) and finite(report['common_frontend_teardown_s']),'Common timing missing')
    jobs=plan()['preflight']['campaign']['schedule']['initial_jobs'];ids=campaign['completed']
    require(ids==campaign['started']==[j['job_id'] for j in jobs][:len(ids)],'Partial or reordered attempts')
    require({p.name for p in directory.iterdir() if p.is_dir() and p.name!='sources'}==set(ids),'Extra attempt directory')
    observations={};results=[];pids=[];attempts=[]
    for job in jobs[:len(ids)]:
        d=directory/job['job_id'];value=replay(d,BINDINGS,cert['plan']['preflight'],job,Adapter(),cert['run_identity'])
        receipt=read(d/'receipt.json');attempts.append(receipt['start']['attempt_id'])
        summary=read(d/'runtime/run/summary.json')
        require(summary['jar_sha256']==bootstrap['jar_sha256'] and summary['backend_commit']==registry['backend_commit'] and summary['frontend_commit']==registry['frontend_commit'],'Application revision or jar differs')
        for branch in summary['branches']:
            pid=read(d/'runtime/run'/branch['result'])['backend_pid'];require(type(pid) is int and pid>0,'Backend PID missing');pids.append(pid)
        observations[job['job_id']]=value;loaded=read(d/'runtime-observations.json')
        results.append({'job_id':job['job_id'],'pair_id':job['pair_id'],'attempt_id':attempts[-1],
                        'terminal_kind':value['kind'],'runtime_job_id':summary['job']['job_id'],
                        'branch_total_s':{c:r['branch_total_s'] for c,r in loaded['branch_costs'].items()}})
    require(len(pids)==len(set(pids)) and len(attempts)==len(set(attempts)),'Attempt or backend process reused')
    visited=[]
    def execute(job):visited.append(job['job_id']);return observations[job['job_id']]
    reconstructed=drive(execute,lambda _:None)
    require(reconstructed==campaign and visited==ids,'Common ledger differs')
    return {'verified':True,'status':campaign['status'],'source_commit':cert['source_commit'],'run_identity':cert['run_identity'],
            'pairs':len(results),'branches':len(pids),'results':results,'primary_freeze_complete':False,'new_primary_samples':0}

if __name__=='__main__':
    import json
    print(json.dumps(validate(sys.argv[1]),indent=2))
