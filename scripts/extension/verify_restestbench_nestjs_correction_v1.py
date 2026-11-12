#!/usr/bin/env python3
"""Verify the one registered reset correction and combine qualification coverage."""
import argparse
from datetime import datetime
import hashlib
import importlib.util
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BASE=ROOT/'scripts/extension/verify_restestbench_valid_golden_v1.py'
spec=importlib.util.spec_from_file_location('original_verifier',BASE)
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
HEAD='dca9f1c6bd158e43f06a92a84f108dc28b6f29df'
RUN=43134240767

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def build(archive):
    reg_path=ROOT/'manifests/restestbench-nestjs-reset-correction-v1.json'
    registration=json.loads(reg_path.read_text())
    for path,digest in registration['sha256'].items():assert sha(ROOT/path)==digest
    run=json.loads((archive/'run.json').read_text());jobs=json.loads((archive/'jobs.json').read_text())['jobs']
    assert run['id']==RUN and run['head_sha']==HEAD and run['status']=='completed' and run['run_attempt']==1
    assert len(jobs)==1 and jobs[0]['status']=='completed'
    paths=list(archive.rglob('observations.json'));assert len(paths)==1
    folder=paths[0].parent;observation=json.loads(paths[0].read_text())
    assert observation['kind']=='restestbench_valid_golden_nestjs_correction_v1'
    module.HEAD=HEAD
    projection={'upstream_commit':registration['upstream_commit'],'services':registration['services'],'sha256':{'scripts/extension/run_restestbench_valid_golden_v1.py':registration['sha256']['scripts/extension/run_restestbench_valid_golden_nestjs_correction_v1.py']}}
    hashes=json.loads((ROOT/'manifests/restestbench-valid-input-hashes-v1.json').read_text())
    result=module.validate_observation(folder,projection,hashes['services']['nestjs-realworld'])
    commands={r['label']:r for r in observation['commands']}
    for case in observation['cases']:
        if not case['test_executed']:continue
        label=f'req-{case["id"]}-empty-check';row=commands[label]
        assert row['return_code']==0 and not row['timeout']
        lines=(folder/row['log']).read_text().splitlines()
        assert [int(line.strip()) for line in lines if line.strip().isdigit()]==[0]*6
    job=jobs[0]
    elapsed=(datetime.fromisoformat(job['completed_at'].replace('Z','+00:00'))-datetime.fromisoformat(job['started_at'].replace('Z','+00:00'))).total_seconds()/60
    first_path=ROOT/'manifests/restestbench-valid-golden-fresh-v1.json';first=json.loads(first_path.read_text())
    total=first['elapsed_job_minutes']+elapsed
    assert first['job_count']+len(jobs)==4 and total<=100
    services={k:v for k,v in first['services'].items() if k!='nestjs-realworld'};services['nestjs-realworld']=result
    return {'kind':'restestbench_valid_golden_after_correction_v1','run_id':RUN,'head_sha':HEAD,'run_conclusion':run['conclusion'],'correction':result,'services':services,'all_services_qualified':all(r['all_valid_tests_qualified'] for r in services.values()),'qualified_requirement_count':sum(r['outcomes'].get('passed',0) for r in services.values()),'correction_job_minutes':elapsed,'total_application_jobs':4,'total_application_job_minutes':total,'application_job_minutes_ceiling':100,'application_correction_allowance_exhausted':True,'paid_model_calls':0,'new_application_defects_claimed':0,'mutant_behavior_validated':False,'original_verifier_sha256':sha(BASE),'initial_manifest_sha256':sha(first_path),'registration_sha256':sha(reg_path),'evidence_sha256':{str(p.relative_to(archive)):sha(p) for p in sorted(archive.rglob('*')) if p.is_file()}}

def main():
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--verify',action='store_true');args=p.parse_args();value=build(args.archive)
    if args.verify:assert json.loads(args.output.read_text())==value
    else:
        assert not args.output.exists();args.output.write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps({k:v for k,v in value.items() if k!='evidence_sha256'},indent=2))

if __name__=='__main__':main()
