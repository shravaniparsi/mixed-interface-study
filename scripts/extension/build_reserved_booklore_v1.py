#!/usr/bin/env python3
import hashlib,json,os,subprocess,time
from pathlib import Path
src=Path.cwd()/'subject';out=Path(os.environ['RUNNER_TEMP'])/'evidence';bins=out.parent/'binaries'
out.mkdir(exist_ok=True);bins.mkdir(exist_ok=True)
revision=subprocess.check_output(['git','-C',str(src),'rev-parse','HEAD'],text=True).strip()
assert revision=='01b3407528a6ce00d064dbb9aa3f69b72d82641b'
(out/'source-commit.txt').write_text(revision+'\n')
s=(src/'Dockerfile').read_text()
for tag in ['node:24-alpine','gradle:9.3.1-jdk25-alpine']:
 raw=subprocess.check_output(['docker','image','inspect',tag]);data=json.loads(raw)[0]
 (out/(tag.split(':')[0]+'-image.json')).write_bytes(raw)
 digests=[d for d in data['RepoDigests'] if d.split('@')[0].split('/')[-1]==tag.split(':')[0]]
 assert len(digests)==1 and s.count('FROM '+tag+' AS ')==1
 s=s.replace('FROM '+tag+' AS ','FROM '+digests[0]+' AS ')
(out/'build.Dockerfile').write_text(s)
cmd=['timeout','--signal=TERM','--kill-after=15','1200','docker','build','--progress=plain','--target','springboot-build','--build-arg','APP_VERSION=study','-f',str(out/'build.Dockerfile'),'-t','study-booklore-build:v1',str(src)]
start=time.monotonic()
with (out/'build.log').open('wb') as log:r=subprocess.run(cmd,stdout=log,stderr=subprocess.STDOUT)
(out/'measurement.json').write_text(json.dumps({'exit_code':r.returncode,'elapsed_seconds':time.monotonic()-start,'command':cmd},indent=2)+'\n')
if r.returncode==0:
 (out/'built-image.json').write_bytes(subprocess.check_output(['docker','image','inspect','study-booklore-build:v1']))
 subprocess.run(['docker','create','--name','study-booklore-export','study-booklore-build:v1'],check=True,stdout=subprocess.DEVNULL)
 try:subprocess.run(['docker','cp','study-booklore-export:/springboot-app/build/libs/booklore-api-0.0.1-SNAPSHOT.jar',str(bins/'application.jar')],check=True)
 finally:subprocess.run(['docker','rm','study-booklore-export'],check=True,stdout=subprocess.DEVNULL)
(out/'binaries.json').write_text(json.dumps({p.name:{'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()} for p in bins.iterdir()},indent=2)+'\n')
raise SystemExit(r.returncode)
