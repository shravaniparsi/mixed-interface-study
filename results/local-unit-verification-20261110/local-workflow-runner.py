from pathlib import Path
import os,re,subprocess,time,json
root=Path.cwd();out=root/'results/local-unit-verification-20261110';out.mkdir(exist_ok=False)
lines=Path('.github/workflows/unit.yml').read_text().splitlines();steps=[];name=None;i=0
while i<len(lines):
 line=lines[i]
 if line.startswith('      - name: '):name=line.split(': ',1)[1]
 if line.startswith('        run: '):
  command=line[len('        run: '):]
  if command=='|':
   block=[];i+=1
   while i<len(lines) and (lines[i].startswith('          ') or not lines[i].strip()):
    block.append(lines[i][10:]);i+=1
   command='\n'.join(block);i-=1
  if name!='Initialize evidence directory':steps.append((name,command))
 i+=1
metadata={'source_commit':subprocess.check_output(['git','rev-parse','HEAD'],text=True).strip(),'scope':'Local execution of run steps from unit.yml; not hosted CI or a new application experiment','node':'/Users/shravaniparsi/.nvm/versions/node/v20.19.6/bin/node','steps':[]}
env=dict(os.environ,PYTHONDONTWRITEBYTECODE='1',PYTHONPATH='src',CI_ARTIFACT_DIR=str(out.resolve()),RUNNER_TEMP='/private/tmp',PATH='/Users/shravaniparsi/.nvm/versions/node/v20.19.6/bin:'+os.environ['PATH'])
for index,(name,command) in enumerate(steps):
 command=re.sub(r'\bpython\b','python3',command);started=time.monotonic();log=out/f'step-{index:02}.log'
 with log.open('x') as handle:
  completed=subprocess.run(['/bin/bash','-o','pipefail','-c',command],env=env,stdout=handle,stderr=subprocess.STDOUT)
 record={'name':name,'command':command,'exit_code':completed.returncode,'elapsed_s':time.monotonic()-started,'log':log.name};metadata['steps'].append(record)
 (out/'report.json').write_text(json.dumps(metadata,indent=2)+'\n')
 print(name,completed.returncode,flush=True)
 if completed.returncode:raise SystemExit(completed.returncode)
print('All local unit-workflow run steps passed',flush=True)
