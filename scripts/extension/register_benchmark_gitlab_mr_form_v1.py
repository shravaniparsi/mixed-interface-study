#!/usr/bin/env python3
"""Hash one read-only selected-form inspection before dispatch."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SOURCES=['protocol/benchmark-gitlab-mr-form-inspection-v1.md','manifests/benchmark-gitlab-mr-branch-binding-v1.json','manifests/benchmark-gitlab-input-inventory-v1.json','scripts/extension/inspect_benchmark_gitlab_mr_form_v1.mjs','scripts/extension/inspect_benchmark_gitlab_mr_form_runtime_v1.sh','scripts/extension/register_benchmark_gitlab_mr_form_v1.py','.github/workflows/benchmark_gitlab_mr_form_inspection_v1.yml','scripts/extension/qualify_benchmark_gitlab_auth_v1.py','scripts/extension/qualify_benchmark_gitlab_auth_v2.py','scripts/ci/install_browser.sh','scripts/ci/package.json']
def main():
 p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args()
 v={'kind':'benchmark_gitlab_mr_form_inspection_registration_v1','jobs_authorized':1,'job_cap_minutes':30,'business_writes_authorized':0,'scientific_cases_authorized':0,'source_sha256':{s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SOURCES}}
 target=ROOT/'manifests/benchmark-gitlab-mr-form-registration-v1.json'
 if a.verify:assert json.loads(target.read_text())==v
 else:target.write_text(json.dumps(v,indent=2)+'\n')
 print('One read-only MR form inspection; no business writes or scientific cases.')
if __name__=='__main__':main()
