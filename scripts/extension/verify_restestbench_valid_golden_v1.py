#!/usr/bin/env python3
"""Reconstruct valid-test qualification only from terminal-run raw evidence."""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[2]
HEAD='b137f849a95b28adf0013c3d0a36458dbb819920'
RUN=43096414710


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def classify(code, timeout, totals):
    if timeout:return 'timeout'
    if totals is None:return 'missing_test_report'
    if totals['errors']:return 'test_error'
    if totals['tests']==0:return 'no_tests'
    if totals['failures']:return 'test_failed'
    if totals['skipped']:return 'skipped_unqualified'
    return 'passed' if code==0 else 'execution_error'


def validate_observation(folder, registration, expected_hashes):
    observation=json.loads((folder/'observations.json').read_text())
    service=observation['service']; expected=registration['services'][service]
    assert observation['upstream_commit']==registration['upstream_commit']
    assert observation['paid_model_calls']==observation['mutations_installed']==0
    assert (folder/'study-head.txt').read_text().strip()==HEAD
    recorded_instrument=(folder/'instrument-sha256.txt').read_text().split()[0]
    assert recorded_instrument==registration['sha256']['scripts/extension/run_restestbench_valid_golden_v1.py']
    assert observation['expected_ids']==expected
    cases=observation['cases']; ids=[c['id'] for c in cases]
    assert ids==expected[:len(ids)]
    assert observation['unattempted_ids']==sorted(set(expected)-set(ids))
    if observation['terminal']=='completed':assert ids==expected
    commands={r['label']:r for r in observation['commands']}
    assert len(commands)==len(observation['commands'])
    for command in commands.values():
        assert command['elapsed_seconds']>=0
        assert (folder/command['log']).is_file()
    if cases:
        assert json.loads((folder/'input-sha256.json').read_text())==expected_hashes
    def successful(label):
        command=commands[label];assert command['return_code']==0 and not command['timeout']
    def healthy(label):
        entries=json.loads((folder/(label+'.json')).read_text());assert entries and entries[-1].get('status')==200
    for case in cases:
        prefix='req-'+str(case['id'])
        if not case['test_executed']:
            assert case['outcome']=='reset_or_health_failure'
            assert prefix+'-test' not in commands
            continue
        for label in ['build','start','images']:successful(label)
        healthy('initial-health');healthy(prefix+'-health')
        reset_labels={'fastapi':['schema','migrate','seed'],'nestjs-realworld':['restart','truncate'],'todoapp':['clean','restart']}[service]
        for label in reset_labels:successful(prefix+'-'+label)
        if service=='nestjs-realworld':healthy(prefix+'-restart-health')
        command=commands[prefix+'-test']
        assert command['return_code']==case['return_code'] and command['timeout']==case['timeout']
        assert case['test_sha256']==expected_hashes[f'data/tests/{service}/test_{case["id"]}.py']
        totals=None; xml=folder/(prefix+'.xml')
        if xml.exists():
            suites=list(ET.parse(xml).getroot().iter('testsuite'))
            totals={k:sum(int(s.get(k,0)) for s in suites) for k in ['tests','failures','errors','skipped']}
            assert case['junit']==totals
        assert classify(case['return_code'],case['timeout'],totals)==case['outcome']
    test_commands=[name for name in commands if name.startswith('req-') and name.endswith('-test')]
    return {'service':service,'terminal':observation['terminal'],'expected':len(expected),'completed_case_records':len(cases),'recorded_test_processes':len(test_commands),'outcomes':dict(Counter(c['outcome'] for c in cases)),'unattempted_case_ids':observation['unattempted_ids'],'all_valid_tests_qualified':observation['terminal']=='completed' and len(cases)==len(expected) and all(c['outcome']=='passed' for c in cases),'observation_sha256':sha(folder/'observations.json')}


def build(archive):
    registration=json.loads((ROOT/'manifests/restestbench-valid-golden-registration-v1.json').read_text())
    hashes=json.loads((ROOT/'manifests/restestbench-valid-input-hashes-v1.json').read_text())
    for path,digest in registration['sha256'].items():assert sha(ROOT/path)==digest
    run=json.loads((archive/'run.json').read_text());jobs=json.loads((archive/'jobs.json').read_text())['jobs']
    assert run['id']==RUN and run['head_sha']==HEAD and run['status']=='completed'
    assert run['run_attempt']==1
    assert all(j['status']=='completed' for j in jobs)
    observations=list(archive.rglob('observations.json'));results={}
    for path in observations:
        result=validate_observation(path.parent,registration,hashes['services'][json.loads(path.read_text())['service']])
        assert result['service'] not in results;results[result['service']]=result
    for service,ids in registration['services'].items():
        if service not in results:results[service]={'service':service,'expected':len(ids),'terminal':'missing_observation','all_valid_tests_qualified':False,'test_execution_count_known':False}
    elapsed=[]
    for job in jobs:
        if job.get('started_at') and job.get('completed_at'):
            start=datetime.fromisoformat(job['started_at'].replace('Z','+00:00'));end=datetime.fromisoformat(job['completed_at'].replace('Z','+00:00'))
            elapsed.append((end-start).total_seconds()/60)
    return {'kind':'restestbench_valid_golden_results_v1','run_id':RUN,'head_sha':HEAD,'run_conclusion':run['conclusion'],'services':results,'all_services_qualified':all(r['all_valid_tests_qualified'] for r in results.values()),'job_count':len(jobs),'elapsed_job_minutes':sum(elapsed),'timed_job_count':len(elapsed),'elapsed_minutes_are_not_invoice_cost':True,'new_defects_claimed':0,'paid_model_calls':0,'evidence_sha256':{str(p.relative_to(archive)):sha(p) for p in sorted(archive.rglob('*')) if p.is_file()}}


def main():
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--verify',action='store_true');args=p.parse_args()
    value=build(args.archive)
    if args.verify:assert json.loads(args.output.read_text())==value
    else:
        assert not args.output.exists();args.output.write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps({k:v for k,v in value.items() if k!='evidence_sha256'},indent=2))

if __name__=='__main__':main()
