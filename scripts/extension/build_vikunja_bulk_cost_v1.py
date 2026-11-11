#!/usr/bin/env python3
"""Reconstruct elapsed job cost of both retained Vikunja attempts."""
import argparse
from datetime import datetime
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def build():
 folder=ROOT/'results/vikunja-bulk-accounting-v1';rows=[]
 for run_id,conclusion in [(43086390320,'failure'),(43086867599,'success')]:
  run=json.loads((folder/('%s-run.json'%run_id)).read_text());jobs=json.loads((folder/('%s-jobs.json'%run_id)).read_text())
  assert run['id']==run_id and run['status']=='completed' and run['conclusion']==conclusion
  assert jobs['total_count']==len(jobs['jobs'])==2
  for j in jobs['jobs']:
   parse=lambda s:datetime.fromisoformat(s.replace('Z','+00:00'))
   rows.append({'run_id':run_id,'job_id':j['id'],'name':j['name'],'conclusion':j['conclusion'],'elapsed_seconds':(parse(j['completed_at'])-parse(j['started_at'])).total_seconds()})
 return {'kind':'vikunja_bulk_job_accounting_v1','application_runs':2,'jobs':rows,'job_elapsed_minutes':sum(r['elapsed_seconds'] for r in rows)/60,'paid_model_calls':0,'scope':'Both compile-failure jobs and both corrected observation jobs. Excludes other cohorts, unit checks, assistant/tool usage and local work. Elapsed job time is not an invoice or billed minutes.','raw_sha256':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(folder.glob('*.json'))}}
def main():
 p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args();d=build();out=ROOT/'manifests/vikunja-bulk-cost-v1.json'
 if a.verify:assert json.loads(out.read_text())==d
 else:assert not out.exists();out.write_text(json.dumps(d,indent=2)+'\n')
 print(json.dumps({k:v for k,v in d.items() if k not in ('raw_sha256','jobs','scope')}))
if __name__=='__main__':main()
