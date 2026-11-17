#!/usr/bin/env python3
"""Verify stopped-image source provenance; capability interpretation is separately stated."""
import argparse,hashlib,json
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[2]
p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args()
root=ROOT/'results/benchmark-reddit-api-source-v1-ci-44028579797';run=json.loads((root/'run.json').read_text());folder=root/'reddit-api-source-inspection-44028579797'
head='9fff34cb9b6c4d48158c8972cf9bc213647f18e3';digest='0594908059a03e5f610005689440a95c05e776e734006197c7b1eba12734cb46'
assert run['databaseId']==44028579797 and run['status']=='completed' and run['conclusion']=='success' and run['headSha']==head
assert (folder/'head.txt').read_text().strip()==head
assert '@sha256:'+digest in (folder/'image-identity.txt').read_text()
state=json.loads((folder/'container-state.json').read_text());assert state['Status']=='created' and state['Running'] is False and state['StartedAt'].startswith('0001-')
summary=json.loads((folder/'extraction-summary.json').read_text());assert summary['container_started'] is False and summary['scientific_cases_executed']==summary['business_writes_executed']==0
actual={str(f.relative_to(folder)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted((folder/'extracted').rglob('*')) if f.is_file()};assert actual==summary['extracted_files']
composer=json.loads((folder/'extracted/composer.json').read_text());assert composer['name']=='postmill/postmill'
assert len(run['jobs'])==1;job=run['jobs'][0];parse=lambda x:datetime.fromisoformat(x.replace('Z','+00:00'));seconds=(parse(job['completedAt'])-parse(job['startedAt'])).total_seconds();assert 0<=seconds<=1200
api=folder/'extracted/src/Controller/Api';assert {f.name for f in api.glob('*.php')}=={'SubmissionController.php','CommentController.php','ForumController.php','UserController.php'}
m={'kind':'benchmark_reddit_api_source_results_v1','run_id':44028579797,'frozen_head':head,'image_digest':digest,'job_seconds':seconds,'container_started':False,'ordinary_controls_executed':0,'scientific_cases_executed':0,'business_writes_executed':0,'package_name':composer['name'],'extracted_files':len(actual),'capability_assessment':{'post_creation':'Packaged JSON POST /api/submissions delegates to apiCreate and server-side validation.','comment_creation':'Not provided by reviewed API controllers; the native comment action uses Symfony form submission.','qualification_status':'API/API post-to-comment continuation not established; selected family remains ineligible for the registered triple.','limitation':'Source-contract assessment; no runtime requests, exact upstream Postmill release or universal absence of undocumented endpoints established.'},'source_sha256':{str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(root.rglob('*')) if f.is_file()}}
t=ROOT/'manifests/benchmark-reddit-api-source-results-v1.json'
if a.verify:assert json.loads(t.read_text())==m
else:t.write_text(json.dumps(m,indent=2)+'\n')
print(json.dumps({k:v for k,v in m.items() if k!='source_sha256'},indent=2))
