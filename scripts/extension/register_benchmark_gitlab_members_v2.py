#!/usr/bin/env python3
"""Freeze one membership instrumentation correction, before dispatch."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SOURCES=['protocol/benchmark-gitlab-members-controls-v2.md','protocol/benchmark-gitlab-members-controls-v1.md','manifests/benchmark-gitlab-members-controls-v1.json','manifests/benchmark-gitlab-input-inventory-v1.json','scripts/extension/qualify_benchmark_gitlab_members_controls_v2.mjs','scripts/extension/qualify_benchmark_gitlab_members_runtime_v2.sh','scripts/extension/register_benchmark_gitlab_members_v2.py','.github/workflows/benchmark_gitlab_members_controls_v2.yml','scripts/extension/qualify_benchmark_gitlab_auth_v1.py','scripts/extension/qualify_benchmark_gitlab_auth_v2.py','scripts/ci/install_browser.sh','scripts/ci/package.json','evidence/benchmark-gitlab-runtime-source-v1.json']
def main():
 p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args()
 value={'kind':'benchmark_gitlab_members_correction_v2','prior_run_id':43290251888,'branches':['native_native','api_native','api_api'],'ordinary_branch_attempts':3,'scientific_cases_authorized':0,'app_job_cap_minutes':90,'automatic_retries':0,'source_sha256':{s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SOURCES}}
 target=ROOT/'manifests/benchmark-gitlab-members-correction-v2.json'
 if a.verify:assert json.loads(target.read_text())==value
 else:target.write_text(json.dumps(value,indent=2)+'\n')
 print('One fixed ordinary membership triple; zero scientific cases; no automatic retries.')
if __name__=='__main__':main()
