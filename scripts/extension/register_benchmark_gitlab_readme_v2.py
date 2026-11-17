#!/usr/bin/env python3
"""Freeze ordinary README qualification sources before outcomes."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SOURCES=['manifests/benchmark-gitlab-readme-controls-v1.json','protocol/benchmark-gitlab-readme-controls-v2.md','manifests/benchmark-gitlab-readme-content-v1.json','manifests/benchmark-gitlab-input-inventory-v1.json','results/benchmark-wikipedia-article-v1/expected-README.md','results/gitlab-readme-instrument-source-v1/source.json','scripts/extension/qualify_benchmark_gitlab_readme_controls_v2.mjs','scripts/extension/qualify_benchmark_gitlab_readme_runtime_v2.sh','scripts/extension/register_benchmark_gitlab_readme_v2.py','.github/workflows/benchmark_gitlab_readme_controls_v2.yml','scripts/extension/qualify_benchmark_gitlab_auth_v1.py','scripts/extension/qualify_benchmark_gitlab_auth_v2.py','scripts/ci/install_browser.sh','scripts/ci/package.json']
def main():
 p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args()
 source=json.loads((ROOT/'results/gitlab-readme-instrument-source-v1/source.json').read_text())
 for row in source['sources']:
  b=(ROOT/'results/gitlab-readme-instrument-source-v1'/row['path']).read_bytes()
  assert hashlib.sha256(b).hexdigest()==row['sha256']
  assert hashlib.sha1(b'blob '+str(len(b)).encode()+b'\0'+b).hexdigest()==row['git_blob']
 v={'kind':'benchmark_gitlab_readme_controls_registration_v2','branches':['native_native','api_native','api_api'],'jobs_authorized':3,'job_cap_minutes':30,'scientific_cases_authorized':0,'source_sha256':{s:hashlib.sha256((ROOT/s).read_bytes()).hexdigest() for s in SOURCES}}
 target=ROOT/'manifests/benchmark-gitlab-readme-registration-v2.json'
 if a.verify:assert json.loads(target.read_text())==v
 else:target.write_text(json.dumps(v,indent=2)+'\n')
 print('Three ordinary README branches; zero scientific cases; sources verified.')
if __name__=='__main__':main()
