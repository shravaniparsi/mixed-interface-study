#!/usr/bin/env python3
"""Freeze the final ordinary membership correction before dispatch."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SOURCES=['protocol/benchmark-gitlab-members-controls-v3.md','manifests/benchmark-gitlab-members-controls-v2.json','manifests/benchmark-gitlab-input-inventory-v1.json','scripts/extension/qualify_benchmark_gitlab_members_controls_v3.mjs','scripts/extension/qualify_benchmark_gitlab_members_runtime_v3.sh','scripts/extension/register_benchmark_gitlab_members_v3.py','.github/workflows/benchmark_gitlab_members_controls_v3.yml','scripts/extension/qualify_benchmark_gitlab_auth_v1.py','scripts/extension/qualify_benchmark_gitlab_auth_v2.py','scripts/ci/install_browser.sh','scripts/ci/package.json','evidence/benchmark-gitlab-runtime-source-v1.json']
def main():
 p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args()
 prior=json.loads((ROOT/'manifests/benchmark-gitlab-members-controls-v2.json').read_text());assert not prior['ordinary_triple_qualified'] and next(b for b in prior['branches'] if b['branch']=='api_api')['qualified']
 v={'kind':'benchmark_gitlab_members_correction_v3','prior_run_id':44018502088,'final_qualification_correction':True,'branches':['native_native','api_native','api_api'],'ordinary_branch_attempts':3,'scientific_cases_authorized':0,'app_job_cap_minutes':90,'automatic_retries':0,'source_sha256':{s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SOURCES}}
 target=ROOT/'manifests/benchmark-gitlab-members-correction-v3.json'
 if a.verify:assert json.loads(target.read_text())==v
 else:target.write_text(json.dumps(v,indent=2)+'\n')
 print('Final ordinary membership triple; zero scientific cases; stop qualification if it fails.')
if __name__=='__main__':main()
