#!/usr/bin/env python3
"""Reproduce six prior issue inputs and their fixed repetition schedules."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def build():
    inventory=json.loads((ROOT/'manifests/benchmark-gitlab-input-inventory-v1.json').read_text())
    family=next(f for f in inventory['families'] if f['family']=='gitlab.issue_assignment')
    cases=[{'id':s['id'],'optional_field_patch':s['optional_field_patch'],'role':'scientific'} for s in family['specifications']]
    assert len(cases)==6
    controls=[{'id':name,'optional_field_patch':{'description':'Continuation control','confidential':False},'role':'control'} for name in ('control_start','control_end')]
    schedules=[]
    for rep in (1,2):
        order=sorted(cases,key=lambda c:hashlib.sha256((str(rep)+':'+c['id']).encode()).hexdigest())
        branches=['native_native','api_native','api_api']
        if rep==2:branches.reverse()
        entries=[{'case_id':'control_start','branch':'native_native','role':'control'}]
        entries += [{'case_id':c['id'],'branch':b,'role':'scientific'} for c in order for b in branches]
        entries += [{'case_id':'control_end','branch':'native_native','role':'control'}]
        schedules.append({'repetition':rep,'executions':entries})
    sources=['protocol/benchmark-gitlab-issue-execution-v1.md','manifests/benchmark-gitlab-input-inventory-v1.json','manifests/benchmark-gitlab-issue-controls-v1.json','scripts/extension/run_benchmark_gitlab_issue_case_v1.mjs','scripts/extension/run_benchmark_gitlab_issue_batch_v1.py','scripts/extension/wait_benchmark_gitlab_ready_v1.py','scripts/extension/build_benchmark_gitlab_issue_execution_v1.py','.github/workflows/benchmark_gitlab_issue_execution_v1.yml','scripts/ci/install_browser.sh','scripts/ci/package.json','scripts/extension/qualify_benchmark_gitlab_auth_v1.py','evidence/benchmark-gitlab-runtime-source-v1.json']
    return {'kind':'benchmark_gitlab_issue_execution_v1','execution_authorized':True,'scope':'Only the qualified issue family; other frozen families remain pending.','scientific_specifications':6,'fixed_repetitions':2,'scheduled_triples':12,'scientific_branches':36,'control_branches':4,'app_job_cap_minutes':90,'cases':cases+controls,'schedules':schedules,'source_sha256':{p:hashlib.sha256((ROOT/p).read_bytes()).hexdigest() for p in sources}}
def main():
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args();result=build();target=ROOT/'manifests/benchmark-gitlab-issue-execution-v1.json'
    if a.verify:assert json.loads(target.read_text())==result
    else:target.write_text(json.dumps(result,indent=2,ensure_ascii=False)+'\n')
    print('Six fixed issue specifications; two repetitions; 36 scientific and four control branches.')
if __name__=='__main__':main()
