#!/usr/bin/env python3
"""Summarize the frozen connectivity diagnostic without treating it as science."""
import argparse
from collections import Counter
from datetime import datetime
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--archive',type=Path,required=True);parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    archive=args.archive.resolve();run=json.loads((archive/'run.json').read_text())
    assert run['status']=='completed' and run['headSha']=='490c0f03e00addc839d4d673093a50190cf496f8'
    assert len(run['jobs'])==1
    job=run['jobs'][0];folder=archive/'gitlab-connectivity-43170995499'
    seconds=(datetime.fromisoformat(job['completedAt'].replace('Z','+00:00'))-datetime.fromisoformat(job['startedAt'].replace('Z','+00:00'))).total_seconds()
    result={'kind':'benchmark_gitlab_connectivity_v1','run_id':43170995499,'job_id':job['databaseId'],'job_conclusion':job['conclusion'],'job_seconds':seconds,'scientific_cases_executed':0,'paid_model_calls':0,'diagnostic_only':True,'connectivity_groups':[]}
    path=folder/'connectivity.json'
    if path.exists():
        data=json.loads(path.read_text());assert data['diagnostic_only'] and data['scientific_cases_executed']==0
        groups={}
        for round_ in data['rounds']:
            keys=[]
            for row in round_['observations']:
                key=(row['vantage'],row['port'],row['path'],row.get('proxy_mode','not_applicable'))
                keys.append(key)
                outcome=json.dumps({k:row.get(k) for k in ('status','error_type','reason_type','errno','exit_code','final_path')},sort_keys=True)
                groups.setdefault(key,Counter())[outcome]+=1
            assert len(keys)==len(set(keys))==8
        if job['conclusion']=='success':
            assert [r['index'] for r in data['rounds']]==list(range(6))
        result['rounds_retained']=len(data['rounds'])
        for key,counts in sorted(groups.items()):
            result['connectivity_groups'].append({'vantage':key[0],'port':key[1],'path':key[2],'proxy_mode':key[3],'outcomes':[dict(json.loads(outcome),count=count) for outcome,count in sorted(counts.items())]})
    else:
        result['diagnostic_evidence_missing']=True
    result['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(archive.rglob('*')) if p.is_file()}
    target=ROOT/'manifests/benchmark-gitlab-connectivity-v1.json'
    if args.verify:assert json.loads(target.read_text())==result
    else:target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'},indent=2))
if __name__=='__main__':main()
