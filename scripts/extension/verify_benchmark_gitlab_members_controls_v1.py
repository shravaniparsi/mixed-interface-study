#!/usr/bin/env python3
"""Preserve failed membership qualification without classifying it as a defect."""
import argparse,json,hashlib
from datetime import datetime
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
    p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--verify',action='store_true');a=p.parse_args();root=a.archive.resolve()
    run=json.loads((root/'run.json').read_text());assert run['status']=='completed' and run['headSha']=='39100350d74e12cbc9eb9e34d52a7b6e7d2fe965'
    result={'kind':'benchmark_gitlab_members_controls_v1','run_id':43290251888,'scientific_cases_executed':0,'ordinary_triple_qualified':False,'branches':[],'job_seconds':0,'paid_model_calls':0}
    for branch in ('native_native','api_native','api_api'):
        job=next(j for j in run['jobs'] if j['name']==f'qualify ({branch})')
        seconds=(datetime.fromisoformat(job['completedAt'].replace('Z','+00:00'))-datetime.fromisoformat(job['startedAt'].replace('Z','+00:00'))).total_seconds();result['job_seconds']+=seconds
        folder=root/f'gitlab-members-control-v1-{branch}-43290251888';path=folder/'members-control.json';row=json.loads(path.read_text()) if path.exists() else None
        entry={'branch':branch,'job_seconds':seconds,'job_conclusion':job['conclusion'],'evidence_present':bool(row)}
        if row:
            assert row['branch']==branch and row['scientific_cases_executed']==0
            entry.update(reported_pass=row['ordinary_control_passed'],stage=row['stage'],error_type=row.get('error_type'),failure_path=row.get('failure_path'))
            if row['ordinary_control_passed']:
                assert row['preflight_project_absent'] and row['browser_cleanup_confirmed']
                assert row['producer_state']==row['final_state']
                expected=sorted(row['initial_members']+[{'id':i,'access_level':30} for i in (2367,43,5)],key=lambda x:x['id'])
                assert row['final_members']==expected
        result['branches'].append(entry)
    result['source_sha256']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(root.rglob('*')) if p.is_file()}
    target=ROOT/'manifests/benchmark-gitlab-members-controls-v1.json'
    if a.verify:assert json.loads(target.read_text())==result
    else:target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'},indent=2))
if __name__=='__main__':main()
