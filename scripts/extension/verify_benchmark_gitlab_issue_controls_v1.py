#!/usr/bin/env python3
"""Recompute ordinary triple equivalence; failures do not count as defects."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
BRANCHES=('native_native','api_native','api_api')
HEAD='d6ebc23f66d5ba8172e78eafe649069301f7cd62'
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--archive',type=Path,required=True);parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    archive=args.archive.resolve();run=json.loads((archive/'run.json').read_text());assert run['status']=='completed' and run['headSha']==HEAD
    jobs={j['name']:j for j in run['jobs']};assert set(jobs)=={'qualify ('+b+')' for b in BRANCHES}
    result={'kind':'benchmark_gitlab_issue_controls_v1','run_id':43175216640,'scientific_cases_executed':0,'paid_model_calls':0,'ordinary_triple_qualified':False,'branches':[]}
    controls=[];container_ids=[];total=0
    for branch in BRANCHES:
        job=jobs['qualify ('+branch+')'];seconds=(datetime.fromisoformat(job['completedAt'].replace('Z','+00:00'))-datetime.fromisoformat(job['startedAt'].replace('Z','+00:00'))).total_seconds();total+=seconds
        folder=archive/('gitlab-issue-control-v1-'+branch+'-43175216640');entry={'branch':branch,'job_id':job['databaseId'],'job_conclusion':job['conclusion'],'job_seconds':seconds,'control_evidence_present':False,'verified_branch_pass':False}
        if (folder/'container-id.txt').exists():container_ids.append((folder/'container-id.txt').read_text().strip())
        if (folder/'issue-control.json').exists():
            row=json.loads((folder/'issue-control.json').read_text());assert row['branch']==branch and row['scientific_cases_executed']==0
            entry.update(control_evidence_present=True,stage=row['stage'],reported_pass=row['ordinary_control_passed'],error_type=row.get('error_type'),failure_path=row.get('failure_path'))
            if row['ordinary_control_passed']:
                assert job['conclusion']=='success' and row['stage']=='complete'
                assert (folder/'head.txt').read_text().strip()==HEAD
                assert 'sha256:673ba94d757c5b3f4bb55751ad8b745a33bad2b987349322403cbc41035a92e0' in (folder/'image-identity.txt').read_text()
                assert row['actor']=={'id':2330,'username':'byteblaze'}
                before=row['producer_state'];after=row['final_state']
                assert before['title']=='Integrating LLMs for better prompts' and before['description']=='Continuation control'
                assert before['project_id']==183 and before['confidential'] is False
                assert before['assignee_ids']==[] and before['due_date'] is None
                assert after==dict(before,assignee_ids=[2264],due_date='2033-04-01')
                entry['verified_branch_pass']=True
                controls.append(row)
        result['branches'].append(entry)
    result['job_seconds']=total
    result['distinct_fresh_containers']=len(container_ids)==len(set(container_ids))==3
    result['setup_equal']=len(controls)==3 and all(c['assignee_membership_setup']==controls[0]['assignee_membership_setup'] for c in controls)
    result['producer_states_equal']=len(controls)==3 and all(c['producer_state']==controls[0]['producer_state'] for c in controls)
    result['final_states_equal']=len(controls)==3 and all(c['final_state']==controls[0]['final_state'] for c in controls)
    result['ordinary_triple_qualified']=all(result[k] for k in ('distinct_fresh_containers','setup_equal','producer_states_equal','final_states_equal')) and all(b['verified_branch_pass'] for b in result['branches'])
    result['reset_evidence_scope']='Distinct disposable containers plus the frozen instrument preflight assertion; raw preflight issue-list contents were not archived.'
    result['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(archive.rglob('*')) if p.is_file()}
    target=ROOT/'manifests/benchmark-gitlab-issue-controls-v1.json'
    if args.verify:assert json.loads(target.read_text())==result
    else:target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'},indent=2))
if __name__=='__main__':main()
