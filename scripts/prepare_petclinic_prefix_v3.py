#!/usr/bin/env python3
"""Verify the qualified v2 archive, then replay its controls under prefix policy v3."""
import argparse,json
from petclinic_prefix_outcomes_v3 import ROOT,load,sha,pair_terminal,POLICY
from validate_petclinic_terminal_campaign import validate
from mixed_interface.evaluation import file_hashes
OUTPUT='results/petclinic-prefix-replay-v3.json'
MANIFEST='manifests/petclinic-prefix-preparation-v3.json'
SOURCES=['scripts/prepare_petclinic_prefix_v3.py','scripts/petclinic_prefix_outcomes_v3.py',POLICY,
 'tests/test_petclinic_prefix_outcomes_v3.py','tests/test_petclinic_terminal_outcomes.py',
 'protocol/petclinic-prefix-outcomes-v3.md','manifests/petclinic-terminal-integration-qualification.json']

def generate():
    q=load(ROOT/'manifests/petclinic-terminal-integration-qualification.json');directory=ROOT/q['evidence_directory']
    files={str(p.relative_to(directory)):p for p in directory.rglob('*') if p.is_file()}
    if set(files)!=set(q['input_sha256']):raise ValueError('Qualified archive inventory differs')
    for n,p in files.items():
        if sha(p)!=q['input_sha256'][n]:raise ValueError('Qualified archive hash differs: '+n)
    if validate(directory)!=q['verification']:raise ValueError('Qualified archive replay differs')
    registry=load(ROOT/'manifests/petclinic-candidates-v1.json');pairs=[]
    plan=load(directory/'plan.json')
    for job in plan['plan']['schedule']['initial_jobs']:
        run=directory/job['job_id']/'run';summary=load(run/'summary.json')
        branches={('api' if b['oracle']=='api_semantic' else 'ui'):load(run/b['result']) for b in summary['branches']}
        spec=next(c for c in registry['candidates'] if c['id']==job['pair_id'])
        evidence={'qualified_campaign':sha(directory/'campaign.json'),'job':sha(directory/job['job_id']/'job.json'),**{b['result']:sha(run/b['result']) for b in summary['branches']}}
        result=pair_terminal(job['job_id'],branches,spec,registry,cleanup_confirmed=True,evidence=evidence)
        pairs.append({'candidate_id':job['pair_id'],'terminal':result['terminal'],'comparability':result['comparability'],'branch_kinds':{c:v['kind'] for c,v in result['branches'].items()}})
    if [p['terminal']['kind'] for p in pairs]!=['clean_observation']*3+['matched_rejection']*3:raise ValueError('Actual control interpretation changed')
    result={'kind':'petclinic_prefix_policy_replay_v3','pairs':pairs,'historical_application_run':q['application_run'],'application_executions_added':0,'v3_dispatch_qualified':False,'primary_freeze_complete':False}
    paths=set(SOURCES)|set(plan['sources'])|{str(p.relative_to(ROOT)) for p in files.values()}
    manifest={'kind':'petclinic_prefix_extraction_preparation_v3','status':'qualified_archive_replay_and_synthetic_tests','registered_policy_cases':18,'actual_replayed_pairs':6,'actual_replayed_branches':12,'application_executions_added':0,'v3_dispatch_qualified':False,'primary_freeze_complete':False,'output':OUTPUT,'input_sha256':file_hashes(ROOT,sorted(paths))}
    return result,manifest

if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    result,manifest=generate()
    for n,v in ((OUTPUT,result),(MANIFEST,manifest)):
        if args.verify:
            if load(ROOT/n)!=v:raise ValueError('Prefix preparation differs: '+n)
        else:(ROOT/n).write_text(json.dumps(v,indent=2)+'\n')
    print('PetClinic prefix v3 replay verified: six archived pairs; no new application executions.')
