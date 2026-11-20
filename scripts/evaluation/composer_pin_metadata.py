#!/usr/bin/env python3
"""Resolve a source-declared Composer commit via package provenance, without install."""
import datetime, hashlib, json, pathlib, re, subprocess, sys, time
R=pathlib.Path(__file__).resolve().parents[2]
manifest,freeze=sys.argv[1:]
s=json.loads((R/manifest).read_text()); bindings={}
for name in [manifest,'scripts/evaluation/composer_pin_metadata.py',s['composer'],s['parent_collection'],'protocol/editability-repairability-evaluation-v1.md']:
 raw=(R/name).read_bytes();assert raw==subprocess.check_output(['git','show',freeze+':'+name],cwd=R);bindings[name]=hashlib.sha256(raw).hexdigest()
constraint=json.loads((R/s['composer']).read_text())['require'][s['package']]
assert constraint==s['constraint'];pin=re.search(r'#([0-9a-f]{7,40})(?: |$)',constraint).group(1)
parent=json.loads((R/s['parent_collection']).read_text());deadline=datetime.datetime.fromisoformat(parent['source_phase_deadline_utc'])
out=R/s['output'];out.mkdir(exist_ok=False)
x=dict(status='started',freeze=freeze,input_sha256=bindings,project_sequence=s['project_sequence'],source_phase_anchor_utc=parent['source_phase_anchor_utc'],source_phase_deadline_utc=parent['source_phase_deadline_utc'],requests=[],registry_requests=[],application_executed=False,scientific_cases=0)
def save(): (out/'collection.json').write_text(json.dumps(x,indent=2)+'\n')
def request(args,name,rows):
 assert datetime.datetime.now(datetime.timezone.utc)<deadline
 row=dict(arguments=args,file=name,status='started');rows.append(row);save();start=time.monotonic()
 try:
  p=subprocess.run(args,capture_output=True,timeout=30);row['exit_code']=p.returncode
  assert p.returncode==0,p.stderr.decode(errors='replace')[:500]
  assert len(p.stdout)<=2*1024**2
  (out/name).write_bytes(p.stdout);row.update(status='collected',bytes=len(p.stdout),sha256=hashlib.sha256(p.stdout).hexdigest())
  return json.loads(p.stdout)
 finally:row['elapsed_seconds']=time.monotonic()-start;save()
try:
 url='https://repo.packagist.org/p2/'+s['package']+'~dev.json'
 m=request(['curl','--fail','--retry','0','--max-time','25','--max-filesize','2097152',url],'registry.json',x['registry_requests'])
 versions=m['packages'][s['package']];v=next(v for v in versions if v.get('version')==s['constraint'].split('#')[0])
 source=v['source'];assert source['type']=='git';match=re.fullmatch(r'https://github.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+?)(?:\.git)?',source['url']);assert match
 repo=match.group(1);x.update(repository=repo,declared_commit=pin,registry_branch_identity_only=True)
 def gh(endpoint,name): return request(['gh','api',endpoint],name,x['requests'])
 m=gh('repos/'+repo,'1.json');assert m['full_name'].lower()==repo.lower() and not m['private']
 x.update(fork=m['fork'],parent=m.get('parent',{}).get('full_name'),source=m.get('source',{}).get('full_name'))
 c=gh('repos/'+repo+'/git/commits/'+pin,'2.json');assert c['sha'].startswith(pin) and re.fullmatch('[0-9a-f]{40}',c['sha']);x['revision']=c['sha']
 t=gh('repos/'+repo+'/git/trees/'+c['sha']+'?recursive=1','3.json');assert not t.get('truncated')
 x.update(status='metadata_pinned_client_unqualified',dependency_role='backend_common',tree_entries=len(t['tree']))
except Exception as e:x.update(status='metadata_unavailable',error_type=type(e).__name__,error=str(e))
finally:save();print(json.dumps({k:x.get(k) for k in ['status','repository','revision','error']}))
