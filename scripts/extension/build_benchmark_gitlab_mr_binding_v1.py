#!/usr/bin/env python3
"""Bind the selected task's semantic branch using inspected repository provenance."""
import argparse
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--verify',action='store_true');args=parser.parse_args()
    paths=[ROOT/'results/benchmark-gitlab-browser-v1-ci-43173565701/gitlab-browser-v1-43173565701/browser-inspection.json',ROOT/'results/benchmark-gitlab-mr-branch-binding-v1/commit-diff.json',ROOT/'results/benchmark-gitlab-mr-branch-binding-v1/source-job.json',ROOT/'manifests/benchmark-representative-context-v1.json',ROOT/'manifests/benchmark-gitlab-auth-v2.json']
    browser,patch,job,context,auth=[json.loads(p.read_text()) for p in paths]
    commit='2b3ec149575466e9994d7b7709fcac6b317d5954'
    candidates=[row['branch'] for row in browser['branch_comparisons'] if any(c['id']==commit and c['title']=='upgrade node version to allow use of template strings' for c in row.get('commits',[]))]
    assert candidates==['feature/replace-gulp']
    assert patch['commit']==commit and not patch['may_be_truncated'] and len(patch['diffs'])==1
    diff=patch['diffs'][0];assert diff['old_path']==diff['new_path']=='.nvmrc'
    assert diff['diff']=='@@ -1 +1 @@\n-10.14.2\n+14.13.0\n'
    assert job['id']==131037699142 and job['run_id']==43175216640 and job['conclusion']=='success'
    assert auth['mr_project']['id']==174 and auth['mr_project']['default_branch']=='main'
    assert auth['actor']['id']==2330 and auth['user_candidates']['Roshan'][0]['id']==2264
    task=next(r for r in context['representatives'] if r['task_id']==805)
    assert task['start_urls']==['__GITLAB__/a11yproject/a11yproject.com']
    result={'kind':'benchmark_gitlab_mr_branch_binding_v1','task_id':805,'project_id':174,'project_path':'a11yproject/a11yproject.com','source_branch':'feature/replace-gulp','target_branch':'main','reviewer_ids':[2330,2264],'evidence_commit':commit,'binding_basis':'Unique inspected branch containing the intent-matching commit message, corroborated by its Node-version configuration patch. This identifies repository intent, not a claim that Node 14 first introduced template-string support.','scientific_execution_authorized':False,'native_write_control_qualified':False,'additional_jobs_executed':0,'source_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in paths}}
    target=ROOT/'manifests/benchmark-gitlab-mr-branch-binding-v1.json'
    if args.verify:assert json.loads(target.read_text())==result
    else:target.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k!='source_sha256'},indent=2))
if __name__=='__main__':main()
