#!/usr/bin/env python3
"""Register a single stopped-image source comparison."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SOURCES=['protocol/benchmark-gitlab-mr-source-inspection-v1.md','scripts/extension/inspect_benchmark_gitlab_mr_source_v1.sh','.github/workflows/benchmark_gitlab_mr_source_inspection_v1.yml','scripts/extension/register_benchmark_gitlab_mr_source_v1.py','evidence/gitlab-mr-form-source-v1.json','manifests/benchmark-gitlab-image-inspection-v1.json','manifests/benchmark-gitlab-mr-form-results-v1.json']
def main():
 p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args();v={'kind':'benchmark_gitlab_mr_source_registration_v1','jobs_authorized':1,'job_cap_minutes':20,'container_start_authorized':False,'scientific_cases_authorized':0,'automatic_retries':0,'source_sha256':{s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SOURCES}}
 target=ROOT/'manifests/benchmark-gitlab-mr-source-registration-v1.json'
 if a.verify:assert json.loads(target.read_text())==v
 else:target.write_text(json.dumps(v,indent=2)+'\n')
 print('One stopped-container source inspection; no application execution or retries.')
if __name__=='__main__':main()
