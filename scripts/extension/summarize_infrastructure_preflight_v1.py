#!/usr/bin/env python3
"""Check the fixed infrastructure preflight without assigning scientific coverage."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RUN=44218771396

def build():
 archive=ROOT/f'results/infrastructure-preflight-v1-ci-{RUN}'
 def read(name):return json.loads((archive/name).read_text())
 run=read('github-run.json')
 assert run['id']==RUN and run['head_sha']=='1132cf20a81615e0bc1c62a5a86002bb46695c79' and run['status']=='completed'
 jobs=read('github-jobs.json')['jobs'];assert len(jobs)==1
 steps={s['name']:s['conclusion'] for s in jobs[0]['steps']}
 smoke=read('smoke.json') if (archive/'smoke.json').exists() else None
 qualified=False
 if smoke and smoke['status']=='qualified':
  assert run['conclusion']=='success'
  assert steps['Install unchanged pinned browser with bounded extended deadline']=='success'
  assert steps['Native local form smoke check']=='success'
  assert smoke['scientific_cases']==0
  assert smoke['browser_version']=='151.0.7922.34'
  assert smoke['requests']==[{'method':'POST','url':'/save','body':'value=study-runtime'}]
  browser=read('browser.json')
  assert browser['playwright']=='1.62.1' and browser['declared']['revision']=='1234'
  assert browser['declared']['browserVersion']=='151.0.7922.34'
  assert len(browser['executable_sha256'])==64
  lock=read('node-tools-package-lock.json')
  assert lock['packages']['node_modules/playwright']['version']=='1.62.1'
  qualified=True
 return {'kind':'infrastructure_preflight_closure','run_id':RUN,'conclusion':run['conclusion'],'qualified':qualified,'smoke':smoke,'steps':steps,'scientific_cases':0,'interpretation':'Local browser execution only; no application or API/UI compatibility observation.','evidence_hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(archive.rglob('*')) if p.is_file()}}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args();d=build();out=ROOT/'manifests/infrastructure-preflight-v1.json'
 if a.verify:assert json.loads(out.read_text())==d
 else:out.write_text(json.dumps(d,indent=2)+'\n')
 print(json.dumps({k:v for k,v in d.items() if k!='evidence_hashes'},indent=2))
