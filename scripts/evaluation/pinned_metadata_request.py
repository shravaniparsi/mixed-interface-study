#!/usr/bin/env python3
"""One prospective bounded public metadata request; no package installation."""
import datetime,hashlib,json,pathlib,subprocess,sys
R=pathlib.Path(__file__).resolve().parents[2]
manifest,freeze=sys.argv[1:];s=json.loads((R/manifest).read_text());bindings={}
for name in [manifest,'scripts/evaluation/pinned_metadata_request.py',*s['inputs']]:
 raw=(R/name).read_bytes();assert raw==subprocess.check_output(['git','show',freeze+':'+name],cwd=R);bindings[name]=hashlib.sha256(raw).hexdigest()
parent=json.loads((R/s['parent_collection']).read_text());assert datetime.datetime.now(datetime.timezone.utc)<datetime.datetime.fromisoformat(parent['source_phase_deadline_utc'])
out=R/s['output'];out.mkdir(exist_ok=False);x=dict(status='started',freeze=freeze,input_sha256=bindings,source_phase_anchor_utc=parent['source_phase_anchor_utc'],source_phase_deadline_utc=parent['source_phase_deadline_utc'],application_executed=False,scientific_cases=0)
try:
 assert s['url'].startswith('https://registry.npmjs.org/')
 p=subprocess.run(['curl','--fail','--location','--retry','0','--max-time','30','--max-filesize','1048576',s['url']],capture_output=True,timeout=35)
 x['exit_code']=p.returncode;assert p.returncode==0,p.stderr.decode(errors='replace')[-1000:];assert len(p.stdout)<=1048576
 m=json.loads(p.stdout);assert m['name']==s['name'] and m['version']==s['version']
 lock=json.loads((R/s['lockfile']).read_text())['packages']['node_modules/'+s['name']]
 assert m['dist']['integrity']==lock['integrity'] and m['dist']['tarball']==lock['resolved']
 (out/'metadata.json').write_bytes(p.stdout);x.update(status='metadata_verified_against_original_lock',bytes=len(p.stdout),sha256=hashlib.sha256(p.stdout).hexdigest(),repository=m.get('repository'),gitHead=m.get('gitHead'),dist=m['dist'])
except Exception as e:x.update(status='metadata_unavailable',error_type=type(e).__name__,error=str(e))
finally:(out/'collection.json').write_text(json.dumps(x,indent=2)+'\n');print(json.dumps(x))
