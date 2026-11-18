#!/usr/bin/env python3
"""Bounded original-source compile; no workflow or application execution."""
import hashlib,json,os,subprocess,time,tarfile
from pathlib import Path
root=Path.cwd();src=root/'subject';out=Path(os.environ['RUNNER_TEMP'])/'evidence';bins=out.parent/'binaries'
out.mkdir(exist_ok=True);bins.mkdir(exist_ok=True)
revision=subprocess.check_output(['git','-C',str(src),'rev-parse','HEAD'],text=True).strip()
assert revision=='ef5e6457d73e02ad74d72c86fac8b787d2beece9'
(out/'source-commit.txt').write_text(revision+'\n')
images={'backend':'maven@sha256:f7ffbcfeae6e5d56019afeb8c4b288afe73d25b4a0b0b2954fe5866143c1dda0','frontend':'node@sha256:300e3d2c19067c1aec9d9b2bd3acbd43d53797a5836d70a23e437a5634bcd33a'}
results={}
for arm,wd,command,seconds in [
 ('backend','quickstart-generated',['mvn','-B','-Dmaven.test.skip=true','package'],600),
 ('frontend','quickstart-generated/web',['sh','-c','npm install && npm run build'],900)]:
 (out/(arm+'-image.json')).write_bytes(subprocess.check_output(['docker','image','inspect',images[arm]]))
 name='study-celerio-build-'+arm
 cmd=['timeout','--signal=TERM','--kill-after=15',str(seconds),'docker','run','--rm','--name',name,'-v',str(src)+':/source','-w','/source/'+wd,images[arm]]+command
 start=time.monotonic()
 with (out/(arm+'-build.log')).open('wb') as log:
  result=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
 subprocess.run(['docker','rm','-f',name],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
 results[arm]={'exit_code':result.returncode,'elapsed_seconds':time.monotonic()-start,'command':cmd}
 (out/'measurement.json').write_text(json.dumps(results,indent=2)+'\n')
 if result.returncode==0:
  if arm=='backend':
   jar=src/'quickstart-generated/target/celerio-angular-quickstart.jar'
   assert jar.is_file();(bins/'application.jar').write_bytes(jar.read_bytes())
  else:
   dist=src/'quickstart-generated/web/dist';assert (dist/'index.html').is_file()
   with tarfile.open(bins/'frontend.tar','w') as t:t.add(dist,arcname='html')
lock=src/'quickstart-generated/web/package-lock.json'
if lock.exists():(out/'frontend-package-lock.json').write_bytes(lock.read_bytes())
(out/'binaries.json').write_text(json.dumps({p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in bins.iterdir()},indent=2)+'\n')
raise SystemExit(0 if all(r['exit_code']==0 for r in results.values()) else 1)
