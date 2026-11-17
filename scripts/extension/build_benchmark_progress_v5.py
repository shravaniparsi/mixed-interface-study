#!/usr/bin/env python3
import argparse,hashlib,json
from pathlib import Path
from build_benchmark_progress_v4 import build as prior
ROOT=Path(__file__).resolve().parents[2]
def build():
 v=prior();src='manifests/benchmark-gitlab-readme-controls-v2.json';r=json.loads((ROOT/src).read_text());assert r['ordinary_triple_qualified'] and r['scientific_cases_executed']==0
 v['kind']='benchmark_continuation_progress_snapshot_v5';v['snapshot_scope']='After full final README ordinary qualification; before scientific schedule registration. Not a live job-status feed.'
 for f in v['families']:
  if f['family']=='gitlab.repository_readme':f.update(status='ordinary_triple_qualified_scientific_schedule_not_dispatched',evidence=src)
 v['unexecuted_with_qualification_unresolved']=0;v['unexecuted_qualified_awaiting_scientific_schedule']=6
 v['readme_ordinary_controls'].update(v2_status_at_snapshot='completed_qualified',v2_qualified=True,v2_job_seconds=r['job_seconds'],total_qualification_job_seconds=v['readme_ordinary_controls']['v1_job_seconds']+r['job_seconds'])
 v['source_sha256'][src]=hashlib.sha256((ROOT/src).read_bytes()).hexdigest();return v
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args();v=build();t=ROOT/'manifests/benchmark-progress-v5.json'
 if a.verify:assert json.loads(t.read_text())==v
 else:t.write_text(json.dumps(v,indent=2)+'\n')
 print('24 frozen specifications: 6 executed, 12 unexecuted after closure, 6 README inputs qualified for separately registered scheduling.')
