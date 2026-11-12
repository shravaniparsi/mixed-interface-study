#!/usr/bin/env python3
"""Verify frozen stopped-container extraction, version identity and infrastructure cost."""
import argparse
from datetime import datetime
import hashlib
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--archive',type=Path,required=True);parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    archive=args.archive.resolve();run=json.loads((archive/'run.json').read_text());assert run['status']=='completed'
    assert run['headSha']=='d8d84fcb24269f1d16ec0e522e7c1b4838a5bc03'
    job=run['jobs'][0];assert len(run['jobs'])==1
    seconds=(datetime.fromisoformat(job['completedAt'].replace('Z','+00:00'))-datetime.fromisoformat(job['startedAt'].replace('Z','+00:00'))).total_seconds()
    folder=archive/'gitlab-image-inspection-43166622248'
    result={'kind':'gitlab_image_inspection_v1','run_id':43166622248,'job_id':job['databaseId'],'job_seconds':seconds,'job_conclusion':job['conclusion'],'scientific_cases_executed':0,'paid_model_calls':0,'application_version':None,'source_revision':None,'api_documents':[]}
    if (folder/'extraction-summary.json').exists():
        summary=json.loads((folder/'extraction-summary.json').read_text());state=json.loads((folder/'container-state.json').read_text())
        assert not summary['container_started'] and summary['scientific_cases_executed']==0
        assert state['Status']=='created' and not state['Running'] and state['Pid']==0
        assert state['StartedAt'].startswith('0001-01-01')
        for name,digest in summary['extracted_files'].items():assert hashlib.sha256((folder/name).read_bytes()).hexdigest()==digest
        assert 'sha256:673ba94d757c5b3f4bb55751ad8b745a33bad2b987349322403cbc41035a92e0' in (folder/'image-identity.txt').read_text()
        for name,field in [('VERSION','application_version'),('REVISION','source_revision')]:
            path=folder/'extracted'/name
            if path.exists():result[field]=path.read_text().strip()
        result['api_documents']=sorted(name for name in summary['extracted_files'] if name.startswith('extracted/doc/api/'))
        result['container_never_started_verified']=True
    else:
        result['container_never_started_verified']=False
        result['scope']='Incomplete extraction: inspect raw failure logs; absence of evidence is not successful qualification.'
    files=sorted(p for p in archive.rglob('*') if p.is_file())
    result['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    target=ROOT/'manifests/benchmark-gitlab-image-inspection-v1.json'
    if args.verify:assert json.loads(target.read_text())==result
    else:target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'},indent=2))

if __name__=='__main__':main()
