#!/usr/bin/env python3
"""Verify coverage of read-only browser inspection, not workflow eligibility."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--archive',type=Path,required=True);parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    archive=args.archive.resolve();run=json.loads((archive/'run.json').read_text())
    assert run['status']=='completed' and run['headSha']=='e08d60a840e94619f663dcb0ab026d82e181184d'
    assert len(run['jobs'])==1
    job=run['jobs'][0];folder=archive/'gitlab-browser-v1-43173565701'
    seconds=(datetime.fromisoformat(job['completedAt'].replace('Z','+00:00'))-datetime.fromisoformat(job['startedAt'].replace('Z','+00:00'))).total_seconds()
    result={'kind':'benchmark_gitlab_browser_inspection_v1','run_id':43173565701,'job_id':job['databaseId'],'job_conclusion':job['conclusion'],'job_seconds':seconds,'scientific_cases_executed':0,'paid_model_calls':0,'native_workflows_qualified':False,'inspection_completed':False}
    if (folder/'browser-inspection.json').exists():
        data=json.loads((folder/'browser-inspection.json').read_text());assert data['scientific_cases_executed']==data['business_object_writes']==0
        result['inspection_completed']=data.get('inspection_completed',False)
        result['actor']=data.get('actor')
        result['forms']=[{k:v for k,v in row.items() if k not in ('fields','links')} | {'field_count':len(row.get('fields',[]))} for row in data['forms']]
        result['blocked_request_count']=len(data['blocked_requests'])
        expected=json.loads((ROOT/'manifests/benchmark-gitlab-auth-v2.json').read_text())
        branches=sorted(b['name'] for b in expected['mr_branch_candidates'] if not b['default'])
        observed=sorted(row['branch'] for row in data['branch_comparisons'])
        result['branch_compare_count']=len(observed)
        result['all_selected_branches_attempted']=observed==branches
        result['branch_compare_failures']=[row['branch'] for row in data['branch_comparisons'] if 'error_type' in row]
        result['branches_with_lexical_patch_clues']=[row['branch'] for row in data['branch_comparisons'] if any(d.get('matches') for d in row.get('diffs',[]))]
        result['semantic_branch_identity_qualified']=False
        if result['inspection_completed']:
            assert observed==branches and result['actor']=={'id':2330,'username':'byteblaze'}
        if job['conclusion']=='success':assert result['inspection_completed']
    else:result['browser_evidence_missing']=True
    result['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(archive.rglob('*')) if p.is_file()}
    target=ROOT/'manifests/benchmark-gitlab-browser-inspection-v1.json'
    if args.verify:assert json.loads(target.read_text())==result
    else:target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'},indent=2))
if __name__=='__main__':main()
