#!/usr/bin/env python3
import argparse,hashlib,json,os,shutil,subprocess,time
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser();p.add_argument('--source',type=Path,required=True);p.add_argument('--version',required=True);p.add_argument('--lock',type=Path,required=True);p.add_argument('--output',type=Path,required=True);a=p.parse_args();source=a.source.resolve();out=a.output.resolve();out.mkdir(parents=True,exist_ok=False)
 regpath=ROOT/'manifests/fastdash-cascade-calibration-v1.json';reg=json.loads(regpath.read_text());report={'kind':'fastdash_cascade_v1','version':a.version,'run_id':os.environ['GITHUB_RUN_ID'],'study_commit':os.environ['GITHUB_SHA'],'registry_sha256':sha(regpath),'status':'incomplete','commands':[]}
 def run(args,timeout=120,env=None):
  log=out/('command-%02d.log'%len(report['commands']));start=time.monotonic()
  with log.open('w') as f:r=subprocess.run(args,cwd=source,stdout=f,stderr=subprocess.STDOUT,env=env,timeout=timeout)
  report['commands'].append({'args':args,'returncode':r.returncode,'elapsed_seconds':time.monotonic()-start,'log':log.name})
  if r.returncode:raise RuntimeError('command failed: '+str(args))
  return log.read_text()
 try:
  for name,expected in reg['source_sha256'].items():assert sha(ROOT/name)==expected,name
  assert run(['git','rev-parse','HEAD']).strip()==reg['versions'][a.version]
  assert not run(['git','status','--porcelain']).strip()
  for name,expected in reg['upstream_git_blobs'][a.version].items():
   target=out/'upstream-source'/name;target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source/name,target)
   data=target.read_bytes();assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==expected,name
  shutil.copyfile(a.lock,out/'requirements.txt');report['python']=run(['python','--version']).strip();run(['python','-m','pip','freeze','--all'])
  env=dict(os.environ,PYTHONPATH=str(source),PYTHONDONTWRITEBYTECODE='1')
  for case in reg['cases']:
   run(['python',str(ROOT/'scripts/extension/observe_fastdash_cascade_v1.py'),'--case',case,'--output',str(out/'observations'/(case+'.json'))],env=env)
  assert not run(['git','diff','--name-only']).strip()
  report['status']='observed';report['executions']=4
 except BaseException as e:report.update(error_type=type(e).__name__,error=str(e))
 finally:
  report['files_sha256']={str(p.relative_to(out)):sha(p) for p in sorted(out.rglob('*')) if p.is_file()};(out/'report.json').write_text(json.dumps(report,indent=2)+'\n')
 return 0 if report['status']=='observed' else 1
if __name__=='__main__':raise SystemExit(main())
