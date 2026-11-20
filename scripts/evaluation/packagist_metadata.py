#!/usr/bin/env python3
"""One registered package metadata read; does not install or resolve an application."""
import datetime,hashlib,json,pathlib,re,subprocess,sys
R=pathlib.Path(__file__).resolve().parents[2]
manifest,freeze=sys.argv[1:];s=json.loads((R/manifest).read_text());bindings={}
for name in [manifest,'scripts/evaluation/packagist_metadata.py',s['composer'],s['parent_collection']]:
 raw=(R/name).read_bytes();assert raw==subprocess.check_output(['git','show',freeze+':'+name],cwd=R);bindings[name]=hashlib.sha256(raw).hexdigest()
assert json.loads((R/s['composer']).read_text())['require'][s['package']]==s['constraint']
p=json.loads((R/s['parent_collection']).read_text());assert datetime.datetime.now(datetime.timezone.utc)<datetime.datetime.fromisoformat(p['source_phase_deadline_utc'])
assert re.fullmatch(r'[a-z0-9_-]+/[a-z0-9_-]+',s['package'])
out=R/s['output'];out.mkdir(exist_ok=False)
x=dict(status='started',freeze=freeze,input_sha256=bindings,source_phase_anchor_utc=p['source_phase_anchor_utc'],source_phase_deadline_utc=p['source_phase_deadline_utc'],application_executed=False,scientific_cases=0)
try:
 url='https://repo.packagist.org/p2/'+s['package']+'.json';x['url']=url
 cp=subprocess.run(['curl','--fail','--retry','0','--max-time','25','--max-filesize','2097152',url],capture_output=True,timeout=30);x['exit_code']=cp.returncode
 assert cp.returncode==0,cp.stderr.decode(errors='replace')[:500];assert len(cp.stdout)<=2097152
 m=json.loads(cp.stdout);assert s['package'] in m['packages'];(out/'metadata.json').write_bytes(cp.stdout)
 x.update(status='metadata_collected_unresolved_dependencies',bytes=len(cp.stdout),sha256=hashlib.sha256(cp.stdout).hexdigest())
except Exception as e:x.update(status='metadata_unavailable',error=str(e))
finally:(out/'collection.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps(x))
