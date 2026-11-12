#!/usr/bin/env python3
"""Reconstruct mutant qualification from installation, runtime and raw test proof."""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
import tarfile
import xml.etree.ElementTree as ET
ROOT=Path(__file__).resolve().parents[2]
RUN=43144135284
HEAD='7ff74f4c955f075e7bd0dbd5d196af620bf0b00c'

def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()

def classify(code,timeout,counts):
    if timeout:return 'timeout'
    if counts is None:return 'missing_test_report'
    if counts['errors']:return 'test_error'
    if counts['tests']==0:return 'no_tests'
    if counts['skipped']:return 'skipped_unqualified'
    if counts['failures']:return 'execution_qualified_test_failure' if code==1 else 'execution_error'
    return 'passed' if code==0 else 'execution_error'

def load_inputs():
    registration=json.loads((ROOT/'manifests/restestbench-mutant-runtime-registration-v1.json').read_text())
    for name,digest in registration['sha256'].items():assert sha(ROOT/name)==digest
    expected=json.loads((ROOT/'manifests/restestbench-valid-input-hashes-v1.json').read_text())['services']
    with tarfile.open(ROOT/'results/restestbench-applicability-v1/inputs.tar.gz') as archive:
        for member in archive:
            if member.name.startswith('data/requirements/'):
                service=member.name.split('/')[2]
                expected[service][member.name]=hashlib.sha256(archive.extractfile(member).read()).hexdigest()
    static=json.loads((ROOT/'manifests/restestbench-applicability-v1.json').read_text())
    mutations={(r['service'],r['requirement_id'],r['mutant_index']):r for r in static['observations']}
    return registration,expected,mutations

def validate_service(folder,registration,expected,mutations):
    observation=json.loads((folder/'observations.json').read_text());service=observation['service']
    assert observation['kind']=='restestbench_mutant_runtime_v1'
    keys=registration['services'][service]['expected_keys']
    assert observation['upstream_commit']==registration['upstream_commit']
    assert observation['paid_model_calls']==0
    assert (folder/'study-head.txt').read_text().strip()==HEAD
    assert (folder/'instrument-sha256.txt').read_text().split()[0]==registration['sha256']['scripts/extension/run_restestbench_mutant_runtime_v1.py']
    assert observation['expected_keys']==keys
    trials=observation['trials'];seen=[r['key'] for r in trials]
    assert seen==keys[:len(seen)]
    assert observation['unattempted_keys']==keys[len(seen):]
    if observation['terminal']=='completed':assert seen==keys
    if trials:assert json.loads((folder/'input-sha256.json').read_text())==expected[service]
    commands={r['label']:r for r in observation['commands']};assert len(commands)==len(observation['commands'])
    for row in commands.values():
        assert row['elapsed_seconds']>=0 and (folder/row['log']).is_file()
    def success(label):
        command=commands[label];assert command['return_code']==0 and not command['timeout']
    def health(label):
        states=json.loads((folder/(label+'.json')).read_text());assert states and states[-1].get('status')==200
    last_container=None;controls={};failures=[]
    for trial in trials:
        key=trial['key'];mutant=trial['mutant_index'] is not None;req=trial['requirement_id']
        assert key==(f'req-{req}-mut-{trial["mutant_index"]}' if mutant else f'req-{req}-valid')
        if mutant:
            assert controls.get(req) is True and trial['control_passed']
            static=mutations[(service,req,trial['mutant_index'])]
            if 'target' in trial:assert static['target']==f'services/{service}/original/'+trial['target']
            if trial['mutation_applied']:
                assert trial['before_sha256']==static['before_sha256']
                assert trial['after_sha256']==static['after_sha256'] and trial['bytes_changed']
        else:assert not trial['control_passed']
        if trial.get('container'):
            container=trial['container'];state=json.loads((folder/(key+'-container-state.log')).read_text())
            assert state['Running'] and state['StartedAt']==container['started_at'] and state['Pid']==container['pid']
            assert (folder/(key+'-container-id.log')).read_text().strip()==container['id']
            if last_container:assert (container['id'],container['started_at'])!=(last_container['id'],last_container['started_at'])
            last_container=container
        if trial.get('execution_setup_qualified'):
            for label in ['build','start','images',key+'-restart',key+'-container-state']:success(label)
            health('initial-health');health(key+'-restart-health');health(key+'-health')
            suffixes={'fastapi':['schema','migrate','seed'],'nestjs-realworld':['truncate','empty-check'],'todoapp':['clean']}[service]
            for suffix in suffixes:success(key+'-'+suffix)
            if service=='nestjs-realworld':
                lines=(folder/(key+'-empty-check.log')).read_text().splitlines()
                assert [int(line.strip()) for line in lines if line.strip().isdigit()]==[0]*6
            if mutant:
                success(key+'-installed-source')
                assert (folder/(key+'-installed-source.log')).read_text().split()[0]==trial['container_source_sha256']==trial['after_sha256']
        if trial['test_executed']:
            assert trial['execution_setup_qualified']
            command=commands[key+'-test'];assert command['return_code']==trial['return_code'] and command['timeout']==trial['timeout']
            assert trial['test_sha256']==expected[service][f'data/tests/{service}/test_{req}.py']
            xml=folder/(key+'.xml');counts=None;parse_error=False
            if xml.exists():
                try:
                    document=ET.parse(xml).getroot();suites=list(document.iter('testsuite'))
                    counts={k:sum(int(s.get(k,0)) for s in suites) for k in ['tests','errors','failures','skipped']}
                    assert trial['junit']==counts
                    for failure in document.iter('failure'):failures.append({'key':key,'message':failure.get('message',''),'text':failure.text or ''})
                except ET.ParseError:parse_error=True
            if parse_error:assert trial['outcome']=='test_execution_failure' and trial['error'].startswith('ParseError:')
            else:
                outcome=classify(trial['return_code'],trial['timeout'],counts)
                if mutant and outcome=='passed':outcome='survived'
                assert trial['outcome']==outcome
        else:assert key+'-test' not in commands
        candidate=bool(mutant and trial['control_passed'] and trial['mutation_applied'] and trial['bytes_changed'] and trial.get('execution_setup_qualified') and trial['test_executed'] and trial['outcome']=='execution_qualified_test_failure')
        assert trial['candidate_detection']==candidate
        if not mutant:controls[req]=trial['outcome']=='passed'
    mutants=[r for r in trials if r['mutant_index'] is not None]
    return {'service':service,'terminal':observation['terminal'],'expected_controls':registration['services'][service]['requirements'],'expected_mutants':registration['services'][service]['mutants'],'recorded_controls':len(controls),'passing_controls':sum(controls.values()),'recorded_mutants':len(mutants),'mutant_outcomes':dict(Counter(r['outcome'] for r in mutants)),'candidate_detections':sum(r['candidate_detection'] for r in mutants),'uncompleted_keys':observation['unattempted_keys'],'failure_records':failures,'observations_sha256':sha(folder/'observations.json')}

def build(archive):
    registration,expected,mutations=load_inputs()
    run=json.loads((archive/'run.json').read_text());jobs=json.loads((archive/'jobs.json').read_text())['jobs']
    assert run['id']==RUN and run['head_sha']==HEAD and run['run_attempt']==1 and run['status']=='completed'
    assert len(jobs)==3 and all(j['status']=='completed' for j in jobs)
    services={}
    for path in archive.rglob('observations.json'):
        result=validate_service(path.parent,registration,expected,mutations);assert result['service'] not in services;services[result['service']]=result
    for service in registration['services']:
        if service not in services:services[service]={'service':service,'terminal':'missing_observations','execution_count_known':False}
    elapsed=sum((datetime.fromisoformat(j['completed_at'].replace('Z','+00:00'))-datetime.fromisoformat(j['started_at'].replace('Z','+00:00'))).total_seconds()/60 for j in jobs)
    return {'kind':'restestbench_mutant_runtime_results_v1','run_id':RUN,'head_sha':HEAD,'run_conclusion':run['conclusion'],'services':services,'all_trials_accounted_with_records':all(s.get('terminal')=='completed' and not s.get('uncompleted_keys') for s in services.values()),'job_count':len(jobs),'application_job_minutes':elapsed,'job_minutes_ceiling':120,'paid_model_calls':0,'candidate_detections_are_not_adjudicated_semantic_defects':True,'new_application_defects_claimed':0,'evidence_sha256':{str(p.relative_to(archive)):sha(p) for p in sorted(archive.rglob('*')) if p.is_file()}}

def main():
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--output',type=Path,required=True);p.add_argument('--verify',action='store_true');args=p.parse_args();value=build(args.archive)
    if args.verify:assert json.loads(args.output.read_text())==value
    else:
        assert not args.output.exists();args.output.write_text(json.dumps(value,indent=2)+'\n')
    print(json.dumps({k:v for k,v in value.items() if k not in ['evidence_sha256','services']},indent=2))
    for service in value['services'].values():print(json.dumps({k:v for k,v in service.items() if k!='failure_records'},indent=2))

if __name__=='__main__':main()
