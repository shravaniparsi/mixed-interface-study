import hashlib,json,os,pathlib,pwd,shutil,sys,tempfile
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'infrastructure-journal-v1'))
from journal import run,atomic
base=pathlib.Path(os.environ['ORDINARY_BASE']);out=base/'evidence';pg=pathlib.Path('/usr/lib/postgresql/16/bin');cluster=pathlib.Path(tempfile.mkdtemp(prefix='research-zipline-pg-'));cluster.chmod(0o755);data=cluster/'data'
number=0;may_run=False;stopped=False;passed=False;summary={'status':'started','scientific_cases':0}
def command(label,args,timeout=30):
 global number
 number+=1;summary['stage']=label;atomic(out/'infra-00-result.json',summary)
 result=run(label,args,out/f'infra-{number:02d}-{label}.json',timeout=timeout,output_limit=65536,cwd='/tmp')
 assert result['status']=='succeeded',(label,result['status'],result.get('exit_code'))
 return result
try:
 version=command('version',[str(pg/'postgres'),'--version'])['output'];assert version.startswith('postgres (PostgreSQL) 16.')
 versions=[version.strip()];hashes=[]
 for tool in ['initdb','pg_ctl','pg_dump','pg_restore','psql','createdb','dropdb']:
  versions.append(command('version_'+tool,[str(pg/tool),'--version'])['output'].strip());hashes.append(hashlib.sha256((pg/tool).read_bytes()).hexdigest()+'  '+str(pg/tool))
 (out/'pg-versions.txt').write_text('\n'.join(versions)+'\n');(out/'pg-binaries.sha256').write_text('\n'.join(hashes)+'\n')
 user=pwd.getpwnam('postgres');data.mkdir(mode=0o700);os.chown(data,user.pw_uid,user.pw_gid)
 command('permissions',['runuser','-u','postgres','--','/bin/sh','-c','test -x "$1" && test -w "$2"','check',str(cluster),str(data)])
 command('initialize',['runuser','-u','postgres','--',str(pg/'initdb'),'-D',str(data),'-U','research','-A','trust','--no-locale','--encoding=UTF8'])
 may_run=True
 command('start',['runuser','-u','postgres','--',str(pg/'pg_ctl'),'-D',str(data),'-l',str(data/'server.log'),'-o',f'-h 127.0.0.1 -p 55432 -k {data}','-w','start'])
 command('createdb',[str(pg/'createdb'),'-h','127.0.0.1','-p','55432','-U','research','zipline'])
 # Application evidence already has its own sanitized export. Do not retain its stdout in the infrastructure journal.
 import subprocess
 summary['stage']='application';atomic(out/'infra-00-result.json',summary)
 completed=subprocess.run([os.environ['NODE_BIN'],os.environ['RUN_SCRIPT']],env={**os.environ,'PG_BIN':str(pg)},timeout=480)
 assert completed.returncode==0,'application returned '+str(completed.returncode)
 passed=True
except Exception as e:summary.update(status='unavailable',error_type=type(e).__name__,error=str(e))
finally:
 atomic(out/'infra-00-result.json',summary)
 if may_run:
  try:
   command('stop',['runuser','-u','postgres','--',str(pg/'pg_ctl'),'-D',str(data),'-m','fast','-w','stop']);stopped=True
  except Exception as e:summary['cleanup_error']=str(e);passed=False
 if not may_run or stopped:shutil.rmtree(cluster)
 summary.update(status='completed' if passed else 'unavailable',shutdown_verified=stopped,commands=number);atomic(out/'infra-00-result.json',summary)
sys.exit(0 if passed else 1)
