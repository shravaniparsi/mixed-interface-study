#!/usr/bin/env python3
"""Independent raw reconstruction of complete or semantically halted mutation sweeps."""
import json,sys
from pathlib import Path
from realworld_generated_execution_v3 import ROOT,SOURCES,jobs,read,branch
from realworld_generated_mutations_v3 import plan,drive
from realworld_generated_loader_v1 import sha
from realworld_generated_terminal_v3 import compare
from mixed_interface.repetition import require

def reconstruct_schedule(observations,recorded):
    visited=[]
    def execute(job):
        require(job['job_id'] in observations,'Missing dispatched observation')
        visited.append(job['job_id']);return observations[job['job_id']]
    replay=drive(execute,lambda _:None)
    require(set(visited)==set(observations),'Extra observation after halt')
    require(replay==recorded,'Campaign ledger differs')
    return replay


def validate(root):
    root=Path(root);cert=read(root/'plan.json');report=read(root/'report.json');campaign=read(root/'campaign.json')
    require(cert['jobs']==jobs() and cert['mutation_plan']==plan() and set(cert['sources'])==set(SOURCES),'Source/selection differs')
    for s,h in cert['sources'].items():require(sha(root/'sources'/s)==h==sha(ROOT/s),'Executed source differs: '+s)
    require(cert['worker_timeout_s']==80 and cert['outer_timeout_s']==1800 and cert['primary_freeze_complete'] is False,'Budget/scope differs')
    bootstrap=read(root/'realworld-bootstrap.json')
    require(bootstrap['status']=='prepared_not_started' and bootstrap['application_source_modified'] is False,'Bootstrap not qualified')
    require(bootstrap['backend_commit']=='87dd078c883a046f5ff20269df2fb004d8b5f83f' and bootstrap['frontend_commit']=='b14ba5011cf9cc97babfcd7ca99dcfbb058862e7','Application revision differs')
    require(report['status']==campaign['status'] and report['status'] in ('completed_bounded_diagnostic','halted_terminal_outcome'),'Executor/setup failure not qualified')
    require(report['completed_jobs']==campaign['completed_jobs']==campaign['started_jobs'] and report['new_primary_samples']==0 and report['primary_freeze_complete'] is False,'Partial or promoted ledger')
    cleanup=report['frontend_cleanup'];require(cleanup['exit_confirmed'] and not cleanup['errors'],'Frontend cleanup incomplete')
    expected=[j['job_id'] for j in jobs()][:len(campaign['completed_jobs'])]
    require(campaign['completed_jobs']==expected and {p.name for p in root.glob('generated-*')}==set(expected),'Attempt inventory differs')
    results=[];observations={};fixture_sha=sha(root/'fixture.sqlite3')
    for job in jobs()[:len(expected)]:
        d=root/job['job_id'];require(read(d/'job.json')==job,'Dispatched job differs')
        require({p.name for p in d.iterdir() if p.is_dir()}=={'api','ui'},'Branch inventory differs')
        branches={c:branch(d/c,job,c,fixture_sha) for c in ('api','ui')}
        value=compare(job,branches,{c:sha(d/c/'observation.json') for c in branches})
        require(value==read(d/'observations.json'),'Pair reconstruction differs');observations[job['job_id']]=value
        results.append({'job_id':job['job_id'],'terminal_kind':value['terminal']['kind'],'branch_total_s':{c:r['branch_total_s'] for c,(_,r) in branches.items()}})
    reconstruct_schedule(observations,campaign)
    return {'verified':True,'source_commit':cert['source_commit'],'status':campaign['status'],'completed_jobs':len(results),
            'branches':2*len(results),'results':results,'unstarted_jobs':[j['job_id'] for j in jobs()[len(results):]],
            'primary_freeze_complete':False,'new_primary_samples':0}

if __name__=='__main__':print(json.dumps(validate(sys.argv[1]),indent=2))
