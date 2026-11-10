#!/usr/bin/env python3
"""Reconstruct source, timing, semantics and qualification ledger from raw files."""
import sys
from pathlib import Path
from petclinic_timed_jobs_v4 import ROOT,REGISTRY,read,sha,read_job
from petclinic_branch_cost_validation_v1 import finite
from petclinic_timing_qualification_v1 import plan,drive,PAIR_TIMEOUT_S,OUTER_TIMEOUT_S
from mixed_interface.repetition import require

def replay_schedule(observations,recorded):
    visited=[]
    def execute(slot):
        require(slot['slot_id'] in observations,'Missing dispatched result');visited.append(slot['slot_id']);return observations[slot['slot_id']]
    value=drive(execute,lambda _:None)
    require(value==recorded and set(visited)==set(observations),'Qualification ledger or attempt inventory differs')
    return value

def validate(directory):
    from run_petclinic_timing_qualification_v1 import SOURCES
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
    ids=campaign['completed_slots'];require(ids==campaign['started_slots']==[s['slot_id'] for s in plan()['slots']][:len(ids)],'Partial or reordered attempt inventory')
    require({p.name for p in directory.iterdir() if p.is_dir() and p.name!='sources'}==set(ids),'Extra attempt directory')
    observations={};results=[];pids=[]
    for slot in plan()['slots'][:len(ids)]:
        d=directory/slot['slot_id'];require(read(d/'slot.json')==read(d/'dispatch.json')['slot']==slot,'Dispatched slot differs')
        value=read_job(d,slot['job'],read(d/'execution.json'),slot['batch'])
        require(value==read(d/'observations.json'),'Timing or semantic reconstruction differs')
        summary=read(d/'run/summary.json')
        require(summary['jar_sha256']==bootstrap['jar_sha256'] and summary['backend_commit']==registry['backend_commit'] and summary['frontend_commit']==registry['frontend_commit'],'Application revision or jar differs')
        for branch in summary['branches']:
            pid=read(d/'run'/branch['result'])['backend_pid'];require(type(pid) is int and pid>0,'Backend PID missing');pids.append(pid)
        observations[slot['slot_id']]=value
        results.append({'slot_id':slot['slot_id'],'batch':slot['batch'],'candidate_id':slot['job']['pair_id'],'terminal_kind':value['terminal']['kind'],
                        'branch_total_s':{c:r['branch_total_s'] for c,r in value['branch_costs'].items()},'common_browser_startup_s':value['common_browser_startup_s']})
    require(len(pids)==len(set(pids)),'Backend process reused');replay_schedule(observations,campaign)
    return {'verified':True,'status':campaign['status'],'source_commit':cert['source_commit'],'pairs':len(results),'branches':len(pids),'results':results,
            'unstarted_slots':[s['slot_id'] for s in plan()['slots'][len(ids):]],'primary_freeze_complete':False,'new_primary_samples':0}

if __name__=='__main__':
    import json
    print(json.dumps(validate(sys.argv[1]),indent=2))
