import hashlib,json,os,pathlib,pwd,shutil,sys,tempfile
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'infrastructure-journal-v1'))
from journal import run,atomic
out=pathlib.Path(os.environ['INFRA_OUT']);out.mkdir(parents=True,exist_ok=True)
base=pathlib.Path(tempfile.mkdtemp(prefix='research-pg-infra-'));base.chmod(0o755)
pg=pathlib.Path('/usr/lib/postgresql/16/bin');data=base/'data';counter=0;started=False;stopped=False
result={'status':'in_progress','stage':'tools','application_executed':False,'scientific_cases':0,'checks':{}}
def command(label,args,ok=True):
 global counter
 counter+=1;result['stage']=label;atomic(out/'result.json',result)
 r=run(label,args,out/f'{counter:02d}-{label}.json',timeout=30,output_limit=65536,cwd='/tmp')
 if ok:assert r['status']=='succeeded',(label,r['status'],r.get('exit_code'))
 return r
conn='postgresql://fixture@127.0.0.1:55433/fixture'
def tool(name,*args,ok=True):return command(name,[str(pg/name),*args],ok)
def sql(statement):return tool('psql','-X','-A','-t','-v','ON_ERROR_STOP=1','-d',conn,'-c',statement)
query="SELECT jsonb_build_object('rows',(SELECT jsonb_agg(to_jsonb(t) ORDER BY id) FROM sample t),'sequence',(SELECT jsonb_build_object('last_value',last_value::text,'is_called',is_called) FROM sample_id_seq))::text"
try:
 version=tool('postgres','--version')['output'].strip();assert version.startswith('postgres (PostgreSQL) 16.')
 tools={n:hashlib.sha256((pg/n).read_bytes()).hexdigest() for n in ['postgres','initdb','pg_ctl','pg_dump','pg_restore','psql','createdb','dropdb']};atomic(out/'tools.json',{'version':version,'sha256':tools})
 user=pwd.getpwnam('postgres');data.mkdir(mode=0o700);os.chown(data,user.pw_uid,user.pw_gid)
 command('service_permissions',['runuser','-u','postgres','--','/bin/sh','-c','test -x "$1" && test -w "$2"','check',str(base),str(data)])
 init=['runuser','-u','postgres','--',str(pg/'initdb'),'-D',str(data),'-U','fixture','-A','trust','--no-locale','--encoding=UTF8']
 command('initialize',init)
 negative=command('expected_nonempty_failure',init,ok=False);assert negative['status']=='failed' and negative['exit_code']!=0 and 'not empty' in negative['output'].lower();result['checks']['failure_diagnostic_preserved']=True
 started=True
 command('start',['runuser','-u','postgres','--',str(pg/'pg_ctl'),'-D',str(data),'-l',str(data/'server.log'),'-o',f'-h 127.0.0.1 -p 55433 -k {data}','-w','start'])
 tool('createdb','-h','127.0.0.1','-p','55433','-U','fixture','fixture')
 sql("CREATE TABLE sample(id bigint GENERATED ALWAYS AS IDENTITY PRIMARY KEY, value text NOT NULL, payload jsonb NOT NULL); INSERT INTO sample(value,payload) VALUES ('ordinary','{\"present\":null}'),('other','{}');")
 before=json.loads(sql(query)['output']);atomic(out/'before.json',before)
 dump=base/'backup.dump';tool('pg_dump','--format=custom','--file',str(dump),conn);atomic(out/'backup.json',{'sha256':hashlib.sha256(dump.read_bytes()).hexdigest(),'bytes':dump.stat().st_size})
 sql("UPDATE sample SET value='changed' WHERE id=1; INSERT INTO sample(value,payload) VALUES ('later','{}');")
 changed=json.loads(sql(query)['output']);atomic(out/'changed.json',changed);assert changed!=before
 tool('dropdb','-h','127.0.0.1','-p','55433','-U','fixture','fixture');tool('createdb','-h','127.0.0.1','-p','55433','-U','fixture','fixture')
 tool('pg_restore','--exit-on-error','--no-owner','-d',conn,str(dump));after=json.loads(sql(query)['output']);atomic(out/'restored.json',after);assert after==before;result['checks']['rows_and_sequence_restored']=True
 command('stop',['runuser','-u','postgres','--',str(pg/'pg_ctl'),'-D',str(data),'-m','fast','-w','stop']);stopped=True
 status=command('stopped_status',['runuser','-u','postgres','--',str(pg/'pg_ctl'),'-D',str(data),'status'],ok=False);assert status['status']=='failed' and status['exit_code']==3 and 'no server running' in status['output'].lower();result['checks']['shutdown_verified']=True
 result.update(status='infrastructure_checks_passed',stage='complete')
except Exception as e:result.update(status='infrastructure_unavailable',failed_stage=result['stage'],error_type=type(e).__name__,error=str(e))
finally:
 atomic(out/'result.json',result)
 if started and not stopped:
  try:
   command('cleanup_stop',['runuser','-u','postgres','--',str(pg/'pg_ctl'),'-D',str(data),'-m','fast','-w','stop']);stopped=True
  except Exception as e:result['cleanup_error']=str(e)
 if not started or stopped:shutil.rmtree(base)
 result['command_count']=counter;atomic(out/'result.json',result)
 print(json.dumps(result))
sys.exit(0 if result['status']=='infrastructure_checks_passed' else 1)
