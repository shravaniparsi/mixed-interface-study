#!/usr/bin/env python3
"""Build unchanged pinned PetClinic sources on the disposable hosted runner."""
import hashlib,json,os,subprocess
from pathlib import Path
root=Path(os.environ['STUDY_RUNTIME'])/'petclinic'
art=Path(os.environ['CI_ARTIFACT_DIR'])
root.mkdir(exist_ok=False)
pins={'backend':('spring-petclinic-rest','5180cc9bd0163393c4e628bedc1bc4c27cfaab1b'),
      'frontend':('spring-petclinic-angular','fba8956cbdd04e09973f81eb39379955a825bfc3')}
def run(args,cwd=None,timeout=300):subprocess.run(args,cwd=cwd,check=True,timeout=timeout)
for name,(repo,commit) in pins.items():
 p=root/name
 run(['git','init',str(p)])
 run(['git','-C',str(p),'remote','add','origin','https://github.com/spring-petclinic/'+repo+'.git'])
 run(['git','-C',str(p),'fetch','--depth','1','origin',commit])
 run(['git','-C',str(p),'checkout','--detach','FETCH_HEAD'])
 assert subprocess.check_output(['git','-C',str(p),'rev-parse','HEAD'],text=True).strip()==commit
run(['./mvnw','-B','-Dstyle.color=never','verify'],root/'backend')
run(['npm','ci','--no-audit','--no-fund'],root/'frontend')
run(['npm','run','test:ci'],root/'frontend')
jars=[p for p in (root/'backend/target').glob('*.jar') if not p.name.endswith(('-sources.jar','-javadoc.jar'))]
assert len(jars)==1,jars
sha=lambda p:hashlib.sha256(p.read_bytes()).hexdigest()
report={'kind':'petclinic_hosted_bootstrap','source_modified':False,'commits':{k:v[1] for k,v in pins.items()},'jar':str(jars[0]),'jar_sha256':sha(jars[0]),'frontend_lock_sha256':sha(root/'frontend/package-lock.json'),'native_backend_verify':'passed','native_frontend_test_ci':'passed'}
for name in pins:
 assert not subprocess.check_output(['git','-C',str(root/name),'status','--porcelain','--untracked-files=no'],text=True).strip(),name
(art/'petclinic-bootstrap.json').write_text(json.dumps(report,indent=2)+'\n')
