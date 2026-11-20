#!/usr/bin/env python3
"""One bounded metadata pin for the explicitly documented native-client dependency."""
import datetime,hashlib,json,pathlib,subprocess,sys,time
R=pathlib.Path(__file__).resolve().parents[2]
freeze=sys.argv[1];manifest='manifests/evaluation-source-11-client-metadata.json'
inputs=[manifest,'scripts/evaluation/shlink_client_metadata.py','results/evaluation-source-11-wave1/collection.json','results/evaluation-source-11-wave1/1.txt','protocol/editability-repairability-evaluation-v1.md']
bindings={}
for p in inputs:
 raw=(R/p).read_bytes();assert raw==subprocess.check_output(['git','show',freeze+':'+p],cwd=R);bindings[p]=hashlib.sha256(raw).hexdigest()
s=json.loads((R/manifest).read_text());parent=json.loads((R/s['parent_collection']).read_text());deadline=datetime.datetime.fromisoformat(parent['source_phase_deadline_utc']);repo=s['companion_repository'];assert 'https://github.com/'+repo in (R/s['basis']).read_text()
out=R/'results/evaluation-source-11-client-metadata';out.mkdir(exist_ok=False)
x=dict(status='started',freeze=freeze,input_sha256=bindings,project_sequence=11,repository=repo,source_phase_anchor_utc=parent['source_phase_anchor_utc'],source_phase_deadline_utc=parent['source_phase_deadline_utc'],requests=[],source_contents_acquired=False,application_executed=False,scientific_cases=0)
def save():(out/'collection.json').write_text(json.dumps(x,indent=2)+'\n')
def get(endpoint,cap):
 assert datetime.datetime.now(datetime.timezone.utc)<deadline
 row={'endpoint':endpoint};x['requests'].append(row);save();t=time.monotonic()
 try:
  p=subprocess.run(['gh','api',endpoint],capture_output=True,timeout=30);row['exit_code']=p.returncode
  assert p.returncode==0,p.stderr.decode(errors='replace')[:1000];assert len(p.stdout)<=cap
  name=str(len(x['requests']))+'.json';(out/name).write_bytes(p.stdout);row.update(file=name,bytes=len(p.stdout),sha256=hashlib.sha256(p.stdout).hexdigest(),status='collected');return json.loads(p.stdout)
 finally:row['elapsed_seconds']=time.monotonic()-t;save()
try:
 m=get('repos/'+repo,1048576);assert m['full_name'].lower()==repo and not m['private'] and not m['archived'] and not m['disabled']
 x.update(fork=m['fork'],parent=m.get('parent',{}).get('full_name'),source=m.get('source',{}).get('full_name'),default_branch=m['default_branch'])
 ref=get('repos/'+repo+'/git/ref/heads/'+m['default_branch'],1048576);assert ref['object']['type']=='commit';x['revision']=ref['object']['sha']
 tree=get('repos/'+repo+'/git/trees/'+x['revision']+'?recursive=1',8388608);assert not tree.get('truncated');x.update(status='metadata_pinned_client_unqualified',tree_entries=len(tree['tree']))
except Exception as e:x.update(status='metadata_unavailable',error_type=type(e).__name__,error=str(e))
finally:save();print(json.dumps({k:x[k] for k in ['status','source_contents_acquired','scientific_cases']}))
