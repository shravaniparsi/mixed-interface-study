#!/usr/bin/env python3
import hashlib,json,os,subprocess,time,urllib.request
from pathlib import Path
out=Path(os.environ['RUNNER_TEMP'])/'evidence';binary=Path(os.environ['RUNNER_TEMP'])/'binaries/application.jar'
assert hashlib.sha256(binary.read_bytes()).hexdigest()=='7fe6375fcd89880c12df4de3bd84c238b130d80aa4574df46c495fb1ce3476f0'
J='gradle@sha256:c60c0cfda2348ff28c0d561428a5aab20c23211e165ab3350a95b33cb15ab495'
def cmd(args):return subprocess.check_output(args,text=True,stderr=subprocess.STDOUT,timeout=40)
info=json.loads(cmd(['docker','image','inspect','mariadb:11.4']));(out/'mariadb-image.json').write_text(json.dumps(info,indent=2)+'\n')
P=next(d for d in info[0]['RepoDigests'] if d.split('@')[0].split('/')[-1]=='mariadb')
(out/'java-image.json').write_text(cmd(['docker','image','inspect',J]));states=[]
for arm in ['ui-ui','api-ui','api-api']:
 dest=out/arm;dest.mkdir();start=time.monotonic();d={'arm':arm,'status':'setup_failed','readiness':[],'independent_evaluation_cases':0};names=['study-booklore-app','study-booklore-db']
 try:
  cmd(['docker','network','create','--internal','study-booklore'])
  net=json.loads(cmd(['docker','network','inspect','study-booklore']));assert net[0]['Internal'] is True;(dest/'network.json').write_text(json.dumps(net,indent=2)+'\n')
  cmd(['docker','run','-d','--name',names[1],'--network','study-booklore','-e','MARIADB_ROOT_PASSWORD=studyroot','-e','MARIADB_DATABASE=booklore','-e','MARIADB_USER=booklore','-e','MARIADB_PASSWORD=booklore',P])
  ready=False
  for _ in range(30):
   r=subprocess.run(['docker','exec',names[1],'healthcheck.sh','--connect','--innodb_initialized'],capture_output=True,timeout=10)
   if r.returncode==0:ready=True;break
   time.sleep(2)
  assert ready,'Database readiness deadline'
  args=['docker','run','-d','--user','0','--name',names[0],'--network','study-booklore','-v',str(binary)+':/study/application.jar:ro']
  for e in ['DATABASE_URL=jdbc:mariadb://study-booklore-db:3306/booklore','DATABASE_USERNAME=booklore','DATABASE_PASSWORD=booklore','REMOTE_AUTH_ENABLED=false','REMOTE_AUTH_ADMIN_GROUP=study-disabled','BOOKLORE_PORT=6060']:args+=['-e',e]
  cmd(args+[J,'sh','-c','mkdir -p /app/data /bookdrop && exec java -Xmx2g -jar /study/application.jar'])
  app=json.loads(cmd(['docker','inspect',names[0]]))[0];ip=app['NetworkSettings']['Networks']['study-booklore']['IPAddress'];assert ip.startswith('172.')
  base='http://'+ip+':6060';d['base']=base
  ready=False;deadline=time.monotonic()+120
  while time.monotonic()<deadline:
   try:
    with urllib.request.urlopen(base+'/api/v1/setup/status',timeout=3) as r:body=r.read(100000);d['readiness'].append({'status':r.status});ready=r.status==200
   except Exception as e:d['readiness'].append({'error':str(e)})
   if ready:break
   time.sleep(3)
  assert ready,'Application readiness deadline'
  r=subprocess.run(['node','scripts/extension/qualify_reserved_booklore_control_v1.mjs','--arm',arm,'--base',base,'--out',str(dest)],timeout=180)
  d['browser_exit']=r.returncode;d['status']='qualified' if r.returncode==0 and json.loads((dest/'control.json').read_text())['status']=='qualified' else 'control_failed'
 except Exception as e:d.update(error_type=type(e).__name__,error=str(e))
 finally:
  for name in names:
   for action,suffix in [('logs','log'),('inspect','json')]:
    r=subprocess.run(['docker',action,name],capture_output=True,text=True,timeout=30);(dest/(name+'.'+suffix)).write_text(r.stdout+r.stderr)
   subprocess.run(['docker','rm','-fv',name],capture_output=True,timeout=30)
  subprocess.run(['docker','network','rm','study-booklore'],capture_output=True,timeout=30)
  d['elapsed_seconds']=time.monotonic()-start;(dest/'runtime.json').write_text(json.dumps(d,indent=2)+'\n');states.append(d)
(out/'controls-summary.json').write_text(json.dumps(states,indent=2)+'\n')
raise SystemExit(0 if all(s['status']=='qualified' for s in states) else 1)
