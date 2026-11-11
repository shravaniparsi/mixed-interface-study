#!/usr/bin/env python3
"""Run frozen real-route historical calibration; retain rejected calls as observations."""
import argparse, hashlib, json, os, pathlib, shutil, subprocess, time
ROOT=pathlib.Path(__file__).resolve().parents[2]
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=pathlib.Path,required=True);p.add_argument('--version',required=True);p.add_argument('--output',type=pathlib.Path,required=True);a=p.parse_args()
 source=a.source.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
 manifest=ROOT/'manifests/vikunja-bulk-calibration-v1.json';reg=json.loads(manifest.read_text())
 report={'kind':'vikunja_bulk_calibration_v1','version':a.version,'run_id':os.environ['GITHUB_RUN_ID'],'study_commit':os.environ['GITHUB_SHA'],'status':'incomplete','registry_sha256':sha(manifest),'commands':[]}
 def run(args,timeout=60,env=None):
  log=out/('command-%02d.log'%len(report['commands']));start=time.monotonic()
  with log.open('w') as f:r=subprocess.run(args,cwd=source,stdout=f,stderr=subprocess.STDOUT,timeout=timeout,env=env)
  report['commands'].append({'args':args,'returncode':r.returncode,'elapsed_seconds':time.monotonic()-start,'log':log.name})
  if r.returncode: raise RuntimeError('command failed: '+str(args))
  return log.read_text()
 try:
  for name,expected in reg['source_sha256'].items():assert sha(ROOT/name)==expected,name
  assert run(['git','rev-parse','HEAD']).strip()==reg['versions'][a.version]
  assert not run(['git','status','--porcelain']).strip()
  for name in reg['archive_sources']:
   target=out/'upstream-source'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/name,target)
   data=target.read_bytes();blob=hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()
   assert blob==reg['upstream_git_blobs'][a.version][name],name
  shutil.copyfile(ROOT/'scripts/extension/observe_vikunja_bulk_v1.go',source/'pkg/webtests/study_bulk_v1_test.go')
  report['go_version']=run(['go','version']).strip()
  env=dict(os.environ,STUDY_OBSERVATIONS=str(out/'observations'),GOFLAGS='-mod=readonly',CGO_ENABLED='1')
  run(['go','test','-count=1','-timeout=8m','-run','^TestStudyBulkPreservationV1$','-v','./pkg/webtests'],timeout=780,env=env)
  assert not run(['git','diff','--name-only']).strip()
  records=[json.loads(p.read_text()) for p in (out/'observations').glob('*.json')]
  assert len(records)==12 and all(r['status']=='observed' for r in records)
  report['status']='observed';report['executions']=len(records)
 except BaseException as error:report.update(error_type=type(error).__name__,error=str(error))
 finally:
  report['files_sha256']={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()}
  (out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 return 0 if report['status']=='observed' else 1
if __name__=='__main__':raise SystemExit(main())
