#!/usr/bin/env python3
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SOURCES=['protocol/benchmark-reddit-api-source-inspection-v1.md','scripts/extension/inspect_benchmark_reddit_api_source_v1.sh','scripts/extension/register_benchmark_reddit_api_source_v1.py','.github/workflows/benchmark_reddit_api_source_inspection_v1.yml','results/benchmark-reddit-build-source-v1/source.json']
p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args()
v={'kind':'benchmark_reddit_api_source_registration_v1','jobs_authorized':1,'job_cap_minutes':20,'business_writes_authorized':0,'scientific_cases_authorized':0,'source_sha256':{s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SOURCES}}
t=ROOT/'manifests/benchmark-reddit-api-source-registration-v1.json'
if a.verify:assert json.loads(t.read_text())==v
else:t.write_text(json.dumps(v,indent=2)+'\n')
print('One stopped Reddit source inspection; no application execution.')
