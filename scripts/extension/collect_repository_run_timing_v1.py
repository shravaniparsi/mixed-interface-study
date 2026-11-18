#!/usr/bin/env python3
"""One bounded metadata request per inventoried run; preserve unavailable timings."""
import concurrent.futures,datetime,hashlib,json,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
source=ROOT/'results/repository-run-inventory-20261117'
out=ROOT/'results/repository-run-timing-20261117';out.mkdir(exist_ok=True)
rows=[r for p in sorted(source.glob('page-*.json')) for r in json.loads(p.read_text())['workflow_runs']]
assert len(rows)==695 and len({r['id'] for r in rows})==695

def collect(row):
 run=row['id'];dest=out/f'{run}.json'
 if dest.exists():raise RuntimeError('Refusing to overwrite an earlier timing observation')
 result={'run_id':run,'run_attempt_in_inventory':row['run_attempt'],'event':row['event'],'observed_at':datetime.datetime.now(datetime.timezone.utc).isoformat()}
 try:
  r=subprocess.run(['gh','api',f'repos/shravaniparsi/mixed-interface-study/actions/runs/{run}/timing'],capture_output=True,text=True,timeout=25)
  result['exit_code']=r.returncode
  if r.returncode==0:result['timing']=json.loads(r.stdout)
  else:result['error']=r.stderr.strip();result['response']=r.stdout.strip()
 except (subprocess.TimeoutExpired,json.JSONDecodeError) as e:result['error']=str(e)
 dest.write_text(json.dumps(result,indent=2)+'\n');return result
with concurrent.futures.ThreadPoolExecutor(max_workers=4) as pool:results=list(pool.map(collect,rows))
available=[r for r in results if 'timing' in r]
summary={'kind':'repository_run_timing_inventory','run_count':len(results),'available_count':len(available),'unavailable_run_ids':[r['run_id'] for r in results if 'timing' not in r],'reported_billable_ms_by_os':{},'scope':'Run-level timing endpoint for the fixed 695-run inventory, one observation per run. Multi-attempt attribution unresolved. Includes push checks; excludes local work, assistant/tool usage, other services and invoice verification.','dollar_spend_verified':False,'evidence_hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(out.glob('*.json'))}}
for r in available:
 for label,d in r['timing'].get('billable',{}).items():summary['reported_billable_ms_by_os'][label]=summary['reported_billable_ms_by_os'].get(label,0)+d.get('total_ms',0)
(ROOT/'manifests/repository-run-timing-20261117.json').write_text(json.dumps(summary,indent=2)+'\n')
print(json.dumps({k:v for k,v in summary.items() if k!='evidence_hashes'},indent=2))
