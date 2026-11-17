#!/usr/bin/env python3
"""Snapshot selected-family accounting after README v1 and source eligibility audits."""
import argparse,hashlib,json
from pathlib import Path
from build_benchmark_progress_v3 import build as prior
ROOT=Path(__file__).resolve().parents[2]
SOURCES=['manifests/benchmark-gitlab-readme-content-v1.json','manifests/benchmark-gitlab-readme-controls-v1.json','manifests/benchmark-gitlab-readme-registration-v2.json','manifests/benchmark-gitlab-directory-capability-v1.json','manifests/benchmark-reddit-api-source-results-v1.json','protocol/benchmark-gitlab-readme-controls-v2.md']
def build():
 v=prior();data={s:json.loads((ROOT/s).read_text()) for s in SOURCES if s.endswith('.json')}
 assert not data[SOURCES[1]]['ordinary_triple_qualified']
 assert data[SOURCES[2]]['scientific_cases_authorized']==0 and data[SOURCES[2]]['jobs_authorized']==3
 assert data[SOURCES[3]]['qualification_status']=='closed_documented_contract_ineligible'
 assert data[SOURCES[4]]['scientific_cases_executed']==0
 v['kind']='benchmark_continuation_progress_snapshot_v4'
 v['snapshot_scope']='After archived README v1 ordinary failures, original content recovery, final v2 dispatch and Reddit/directory contract assessments. Not a live job-status feed.'
 for f in v['families']:
  if f['family']=='gitlab.repository_readme':f.update(status='content_bound_v1_unqualified_final_v2_dispatched',evidence=SOURCES[2])
 v['retained_family_eligibility']={'gitlab.directory_file':{'status':'closed_documented_contract_ineligible','evidence':SOURCES[3]},'reddit.post_comment':{'status':'closed_api_continuation_contract_unestablished','evidence':SOURCES[4]}}
 v['readme_ordinary_controls']={'v1_run':44027377236,'v1_job_seconds':data[SOURCES[1]]['job_seconds'],'v1_qualified':False,'v2_run':44030229250,'v2_frozen_head':'3c646b26eb9e0ad25832ea6d5f057707d278504a','v2_status_at_snapshot':'dispatched_results_pending','v2_max_job_minutes':90,'scientific_cases_authorized':0,'further_correction_permitted':False}
 v['source_sha256'].update({s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SOURCES})
 return v
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args();v=build();dest=ROOT/'manifests/benchmark-progress-v4.json'
 if a.verify:assert json.loads(dest.read_text())==v
 else:dest.write_text(json.dumps(v,indent=2)+'\n')
 print('24 frozen specifications: 6 executed, 18 unexecuted; README final ordinary qualification pending; Reddit/directory retained as contract-ineligible.')
