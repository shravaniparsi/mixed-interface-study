#!/usr/bin/env python3
"""One bounded metadata pin for the explicitly documented native-client dependency."""
import datetime,hashlib,json,pathlib,subprocess,sys,time
R=pathlib.Path(__file__).resolve().parents[2]
manifest,freeze=sys.argv[1:]
config=json.loads((R/manifest).read_text())
inputs=[manifest,'scripts/evaluation/git_dependency_metadata_v2.py',config['parent_collection'],config['basis'],'protocol/editability-repairability-evaluation-v1.md']
bindings={}
for p in inputs:
 raw=(R/p).read_bytes();assert raw==subprocess.check_output(['git','show',freeze+':'+p],cwd=R);bindings[p]=hashlib.sha256(raw).hexdigest()
s=json.loads((R/manifest).read_text());parent=json.loads((R/s['parent_collection']).read_text());deadline=datetime.datetime.fromisoformat(parent['source_phase_deadline_utc']);repo=s['companion_repository'];assert 'https://github.com/'+repo in (R/s['basis']).read_text()
assert 9 <= s['project_sequence'] <= 40
out=R/s['output'];out.mkdir(exist_ok=False)
x=dict(status='started',freeze=freeze,input_sha256=bindings,project_sequence=s['project_sequence'],repository=repo,source_phase_anchor_utc=parent['source_phase_anchor_utc'],source_phase_deadline_utc=parent['source_phase_deadline_utc'],requests=[],source_contents_acquired=False,application_executed=False,scientific_cases=0)
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
 commit=get('repos/'+repo+'/git/commits/'+s['revision'],1048576);assert commit['sha']==s['revision'];x['revision']=commit['sha']
 tree=get('repos/'+repo+'/git/trees/'+x['revision']+'?recursive=1',8388608);assert not tree.get('truncated');x.update(status='metadata_pinned_client_unqualified',tree_entries=len(tree['tree']))
except Exception as e:x.update(status='metadata_unavailable',error_type=type(e).__name__,error=str(e))
finally:save();print(json.dumps({k:x[k] for k in ['status','source_contents_acquired','scientific_cases']}))
