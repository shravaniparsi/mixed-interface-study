#!/usr/bin/env python3
"""Reconstruct namespace health and same-actor authentication separately."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--archive',type=Path,required=True);parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    archive=args.archive.resolve();run=json.loads((archive/'run.json').read_text())
    assert run['status']=='completed' and run['headSha']=='5235f969b1f2bc208a777f4f882c86fc16df760a'
    assert len(run['jobs'])==1
    job=run['jobs'][0];folder=archive/'gitlab-auth-v2-43172360473'
    seconds=(datetime.fromisoformat(job['completedAt'].replace('Z','+00:00'))-datetime.fromisoformat(job['startedAt'].replace('Z','+00:00'))).total_seconds()
    result={'kind':'benchmark_gitlab_auth_v2','run_id':43172360473,'job_id':job['databaseId'],'job_conclusion':job['conclusion'],'job_seconds':seconds,'scientific_cases_executed':0,'paid_model_calls':0,'namespace_health_qualified':False,'actor_authenticated':False,'fixture_discovery_completed':False,'native_workflows_qualified':False}
    if (folder/'readiness.json').exists():
        ready=json.loads((folder/'readiness.json').read_text());hits=[r for r in ready['attempts'] if r.get('status')==200 and r.get('body','').strip()=='GitLab OK']
        assert ready['ready']==bool(hits) and ready['scientific_cases_executed']==0
        result['namespace_health_qualified']=bool(hits)
    if (folder/'authentication.json').exists():
        auth=json.loads((folder/'authentication.json').read_text())
        assert auth['scientific_cases_executed']==auth['business_object_writes']==0
        result['actor_authenticated']=auth['authenticated'] and auth.get('actor',{}).get('username')=='byteblaze'
        result['fixture_discovery_completed']=result['actor_authenticated'] and 'failure_type' not in auth and 'qualification_scope' in auth
        for key in ('actor','issue_project_candidates','mr_project','mr_branch_candidates','mr_branch_listing_may_be_truncated','user_candidates','failure_type'):
            if key in auth:result[key]=auth[key]
    if job['conclusion']=='success':
        assert result['namespace_health_qualified'] and result['fixture_discovery_completed']
    result['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(archive.rglob('*')) if p.is_file()}
    target=ROOT/'manifests/benchmark-gitlab-auth-v2.json'
    if args.verify:assert json.loads(target.read_text())==result
    else:target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'},indent=2))
if __name__=='__main__':main()
