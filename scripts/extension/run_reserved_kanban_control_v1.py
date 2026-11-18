#!/usr/bin/env python3
import argparse,hashlib,json,os,subprocess,time,urllib.request,urllib.error
from pathlib import Path
P='postgres@sha256:8342bcb43446694428ec6594e72e4299692854f0fc3aca090b0ab46f4c7f32a1'
J='maven@sha256:f7ffbcfeae6e5d56019afeb8c4b288afe73d25b4a0b0b2954fe5866143c1dda0'
N='nginx@sha256:17bd1698318e9c0f9ba2c5ed49f53d690684dab7fe3e8019b855c352528d57be'
p=argparse.ArgumentParser();p.add_argument('--out',type=Path,required=True);p.add_argument('--binaries',type=Path,required=True);p.add_argument('--arm',choices=['ui-ui','api-ui','api-api'],required=True);a=p.parse_args()
out=a.out.resolve();out.mkdir(exist_ok=True,parents=True);binary=a.binaries.resolve();start=time.monotonic();d={'arm':a.arm,'status':'setup_failed','readiness':[],'independent_evaluation_cases':0}
def cmd(args):return subprocess.check_output(args,text=True,stderr=subprocess.STDOUT)
names=['study-kanban-ui','kanban-app','study-kanban-db']
try:
 assert hashlib.sha256((binary/'application.jar').read_bytes()).hexdigest()=='6e5348777f57305daebbc9c4c83cab42b98722a26f3c1c57ce2c10c4f921d831'
 assert hashlib.sha256((binary/'frontend.tar').read_bytes()).hexdigest()=='7f012b071931de2884f8426eda9ddd4b6a5410ca288ae53b1a959c7e772b4a02'
 # Extract only regular files below html, without trusting tar paths or links.
 import tarfile
 html=binary/'html';html.mkdir()
 with tarfile.open(binary/'frontend.tar') as tar:
  for m in tar.getmembers():
   if m.isdir():continue
   assert m.isfile() and m.name.startswith('html/') and '..' not in Path(m.name).parts
   dest=binary/m.name;dest.parent.mkdir(parents=True,exist_ok=True);dest.write_bytes(tar.extractfile(m).read())
 for label,im in [('postgres',P),('java',J),('nginx',N)]:
  (out/(label+'-image.json')).write_text(cmd(['docker','image','inspect',im]))
 (out/'java-version.txt').write_text(cmd(['docker','run','--rm','--network','none',J,'java','-version']))
 cmd(['docker','network','create','--internal','study-kanban'])
 info=json.loads(cmd(['docker','network','inspect','study-kanban']));assert info[0]['Internal'] is True
 (out/'network.json').write_text(json.dumps(info,indent=2)+'\n')
 cmd(['docker','run','-d','--name','study-kanban-db','--network','study-kanban','-e','POSTGRES_DB=kanban','-e','POSTGRES_USER=kanban','-e','POSTGRES_PASSWORD=kanban',P])
 ready=False
 for attempt in range(60):
  proc=subprocess.run(['docker','exec','study-kanban-db','pg_isready','-U','kanban','-d','kanban'],capture_output=True,text=True)
  if proc.returncode==0:ready=True;break
  time.sleep(2)
 assert ready,'Postgres readiness deadline'
 cmd(['docker','run','-d','--name','kanban-app','--network','study-kanban','-e','DB_SERVER=study-kanban-db','-e','POSTGRES_DB=kanban','-e','POSTGRES_USER=kanban','-e','POSTGRES_PASSWORD=kanban','-v',str(binary/'application.jar')+':/study/application.jar:ro',J,'java','-Xmx1g','-jar','/study/application.jar'])
 conf=Path('scripts/extension/kanban_original_nginx.conf').resolve()
 cmd(['docker','run','-d','--name','study-kanban-ui','--network','study-kanban','-p','127.0.0.1:4200:80','-v',str(html)+':/usr/share/nginx/html:ro','-v',str(conf)+':/etc/nginx/conf.d/default.conf:ro',N])
 deadline=time.monotonic()+180;ready=False
 while time.monotonic()<deadline:
  row={}
  try:
   with urllib.request.urlopen('http://127.0.0.1:4200/api/kanbans/',timeout=3) as r:
    body=r.read(1048576);row['status']=r.status
   if row['status']==200 and isinstance(json.loads(body),list):ready=True
  except Exception as e:row['error']=str(e)
  d['readiness'].append(row)
  if ready:break
  time.sleep(3)
 assert ready,'Application readiness deadline'
 run=subprocess.run(['node','scripts/extension/qualify_reserved_kanban_control_v1.mjs','--arm',a.arm,'--out',str(out)],timeout=180)
 d['browser_exit']=run.returncode;d['status']='qualified' if run.returncode==0 and json.loads((out/'control.json').read_text())['status']=='qualified' else 'control_failed'
except Exception as e:d.update(error_type=type(e).__name__,error=str(e))
finally:
 for name in names:
  for action,suffix in [('logs','log'),('inspect','json')]:
   p=subprocess.run(['docker',action,name],capture_output=True,text=True);(out/(name+'.'+suffix)).write_text(p.stdout+p.stderr)
  subprocess.run(['docker','rm','-fv',name],capture_output=True)
 subprocess.run(['docker','network','rm','study-kanban'],capture_output=True)
 d['elapsed_seconds']=time.monotonic()-start;(out/'runtime.json').write_text(json.dumps(d,indent=2)+'\n')
raise SystemExit(0 if d['status']=='qualified' else 1)
