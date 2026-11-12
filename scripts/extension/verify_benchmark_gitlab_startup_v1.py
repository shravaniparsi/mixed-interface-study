#!/usr/bin/env python3
"""Reconstruct startup qualification from retained health and job evidence."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RUN=43168226517
HEAD='15ab5131acd21630381ea3dacc0f3694a06d56f7'
DIGEST='sha256:673ba94d757c5b3f4bb55751ad8b745a33bad2b987349322403cbc41035a92e0'
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--archive',type=Path,required=True);parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    archive=args.archive.resolve();run=json.loads((archive/'run.json').read_text())
    assert run['status']=='completed' and run['headSha']==HEAD
    assert len(run['jobs'])==1
    job=run['jobs'][0]
    seconds=(datetime.fromisoformat(job['completedAt'].replace('Z','+00:00'))-datetime.fromisoformat(job['startedAt'].replace('Z','+00:00'))).total_seconds()
    folder=archive/('gitlab-startup-'+str(RUN))
    assert (folder/'head.txt').read_text().strip()==HEAD
    result={'kind':'benchmark_gitlab_startup_v1','run_id':RUN,'job_id':job['databaseId'],'job_conclusion':job['conclusion'],'job_seconds':seconds,'scientific_cases_executed':0,'paid_model_calls':0,'startup_qualified':False,'authentication_qualified':False,'business_workflows_qualified':False}
    if (folder/'readiness.json').exists():
        probe=json.loads((folder/'readiness.json').read_text())
        assert probe['scientific_cases_executed']==0
        attempts=probe['attempts']
        hits=[a for a in attempts if a.get('status')==200 and a.get('body','').strip()=='GitLab OK']
        assert bool(hits)==probe['ready']
        result.update(health_attempts=len(attempts),health_response_observed=bool(hits),last_probe_elapsed_seconds=attempts[-1]['elapsed_seconds'] if attempts else None)
        assert DIGEST in (folder/'image-identity.txt').read_text()
        result['startup_qualified']=bool(hits) and job['conclusion']=='success'
    else:
        result['health_probe_evidence_missing']=True
    if (folder/'version.txt').exists():
        result['application_version']=(folder/'version.txt').read_text().strip()
    if result['startup_qualified']:
        assert result['application_version']=='15.7.5'
    result['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(archive.rglob('*')) if p.is_file()}
    target=ROOT/'manifests/benchmark-gitlab-startup-v1.json'
    if args.verify:
        assert json.loads(target.read_text())==result
    else:
        target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'},indent=2))
if __name__=='__main__':main()
