#!/usr/bin/env python3
"""Check retained build provenance; never infer runtime qualification."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RUN=44216495263

def build():
 archive=ROOT/f'results/reserved-booklore-build-v1-ci-{RUN}'
 def read(n):return json.loads((archive/n).read_text())
 run=read('github-run.json')
 assert run['id']==RUN and run['status']=='completed' and run['head_sha']=='a8769a2f79e61e6004edb572cea78a1cc4b09397'
 m=read('measurement.json') if (archive/'measurement.json').exists() else None
 binaries=read('binaries.json') if (archive/'binaries.json').exists() else {}
 status='setup_not_reached' if m is None else 'compiled' if m['exit_code']==0 else 'build_failed'
 if status=='compiled':
  assert (archive/'source-commit.txt').read_text().strip()=='01b3407528a6ce00d064dbb9aa3f69b72d82641b'
  assert set(binaries)=={'application.jar'} and binaries['application.jar']['bytes']>0
  assert len(binaries['application.jar']['sha256'])==64
  cmd=m['command'];assert '--target' in cmd and cmd[cmd.index('--target')+1]=='springboot-build'
  assert (archive/'built-image.json').exists()
 return {'kind':'closed_booklore_build','run_id':RUN,'status':status,'measurement':m,'binaries_reported_by_ci':binaries,'runtime_qualified':False,'independent_evaluation_cases':0,'evidence_hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(archive.iterdir()) if p.is_file()}}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args();d=build();out=ROOT/'manifests/reserved-booklore-build-v1.json'
 if a.verify:assert json.loads(out.read_text())==d
 else:out.write_text(json.dumps(d,indent=2)+'\n')
 print(json.dumps({k:v for k,v in d.items() if k!='evidence_hashes'},indent=2))
