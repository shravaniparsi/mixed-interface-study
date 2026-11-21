import os,pathlib,json,subprocess,time,secrets,base64,traceback,shutil,sqlite3,sys
R=pathlib.Path(__file__).resolve().parents[2];base=pathlib.Path(os.environ['RUNNER_TEMP'])/'relaticle-ordinary-v1';private=base/'private';out=base/'evidence';private.mkdir(parents=True,exist_ok=True);out.mkdir(exist_ok=True)
image='sha256:2befacb0970cf5bf94a559ee9ae21f5944aa1ebc11ee6ac866b2b7a3202c6e44';report=dict(status='started',role=1,application_executed=False,scientific_cases=0,commands=[]);start=time.monotonic();password=secrets.token_urlsafe(24);appkey='base64:'+base64.b64encode(secrets.token_bytes(32)).decode();sensitive=[password,appkey,appkey[7:]]
def save():(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
def run(args,label,cap=90,env=None):
 remaining=590-(time.monotonic()-start);assert remaining>0,'application budget exhausted';row=dict(label=label);report['commands'].append(row);save();t=time.monotonic()
 try:
  cp=subprocess.run(args,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=min(cap,remaining),env=env);(private/(label+'.log')).write_bytes(cp.stdout);row['exit_code']=cp.returncode;assert cp.returncode==0,label+' exit '+str(cp.returncode);return cp.stdout
 finally:row['elapsed_seconds']=time.monotonic()-t;save()
def artisan(args,label,cap=90):return run(['docker','exec','study-relaticle','php','artisan']+args,label,cap)
try:
 report['stage']='initialize';save();run(['docker','network','create','--internal','study-relaticle-net'],'network')
 uidgid=run(['docker','run','--rm','--network','none','--entrypoint','sh',image,'-c','id -u; id -g'],'image-owner').decode().split();uid,gid=map(int,uidgid);run(['docker','create','--name','study-relaticle-seed','--entrypoint','/bin/true',image],'seed-container');run(['docker','cp','study-relaticle-seed:/var/www/html/storage',str(private/'storage')],'seed-storage');run(['docker','cp','study-relaticle-seed:/var/www/html/bootstrap/cache',str(private/'cache')],'seed-cache');run(['docker','rm','study-relaticle-seed'],'seed-remove')
 storage=private/'storage';(storage/'study').mkdir();db=storage/'study/database.sqlite';sqlite3.connect(db).close();run(['sudo','chown','-R',str(uid)+':'+str(gid),str(storage),str(private/'cache')],'volume-owner');run(['sudo','chmod','-R','a+rX',str(storage),str(private/'cache')],'observer-read')
 config={'APP_NAME':'Relaticle','APP_ENV':'production','APP_DEBUG':'false','APP_URL':'http://127.0.0.1:58082','APP_KEY':appkey,'DB_CONNECTION':'sqlite','DB_DATABASE':'/var/www/html/storage/study/database.sqlite','CACHE_STORE':'database','SESSION_DRIVER':'database','SESSION_LIFETIME':'120','QUEUE_CONNECTION':'sync','BROADCAST_CONNECTION':'"null"','FILESYSTEM_DISK':'local','MAIL_MAILER':'log','LOG_CHANNEL':'stderr','REQUIRE_EMAIL_VERIFICATION':'false','RELATICLE_CLOUD':'false','RELATICLE_FEATURE_SETUP_CONVERSATION':'false','RELATICLE_FEATURE_ONBOARD_SEED':'false','RELATICLE_FEATURE_EMAIL_INTEGRATION':'false','RELATICLE_FEATURE_BILLING':'false'}
 envfile=private/'app.env';envfile.write_text('\n'.join(k+'='+v for k,v in config.items())+'\n');report.update(stage='startup',application_executed=True);save()
 run(['docker','run','--rm','--network','study-relaticle-net','--env-file',str(envfile),'-v',str(storage)+':/var/www/html/storage','-v',str(private/'cache')+':/var/www/html/bootstrap/cache','--entrypoint','php',image,'artisan','migrate','--force','--no-interaction'],'initialize-original-schema',120)
 run(['docker','run','-d','--name','study-relaticle','--network','study-relaticle-net','--env-file',str(envfile),'-p','127.0.0.1:58082:8080','-v',str(storage)+':/var/www/html/storage','-v',str(private/'cache')+':/var/www/html/bootstrap/cache',image],'start')
 import urllib.request
 ready=False
 for attempt in range(60):
  try:
   with urllib.request.urlopen('http://127.0.0.1:58082/up',timeout=1) as response:ready=response.status==200
   if ready:break
  except Exception:pass
  time.sleep(1)
 assert ready,'original app startup did not become healthy'
 report['stage']='schema';save();env={**os.environ,'STUDY_DB':str(db),'STUDY_PRIVATE':str(private),'STUDY_EVIDENCE':str(out),'STUDY_PASSWORD':password,'STUDY_ROUTES':str(private/'routes.json')}
 before=run(['python3',str(R/'evaluation/relaticle-ordinary-v1/state.py'),'before-schema'],'before-schema',env=env)
 generated=artisan(['scribe:generate','--no-interaction'],'schema-generate',90)
 after=run(['python3',str(R/'evaluation/relaticle-ordinary-v1/state.py'),'after-schema'],'after-schema',env=env);assert json.loads(before)==json.loads(after),'schema generation changed database'
 run(['docker','cp','study-relaticle:/var/www/html/storage/scribe/openapi.yaml',str(out/'openapi.yaml')],'schema-copy')
 report['stage']='user';save();helptext=artisan(['make:filament-user','--help'],'user-help').decode()
 for option in ['--name','--email','--password','--panel']:assert option in helptext,'original user command missing '+option
 artisan(['make:filament-user','--name=Study User','--email=study@example.test','--password='+password,'--panel=app','--no-interaction'],'user-create')
 (private/'routes.json').write_bytes(artisan(['route:list','--json'],'routes'))
 code="require 'vendor/autoload.php'; $app=require 'bootstrap/app.php'; $app->make(Illuminate\\Contracts\\Console\\Kernel::class)->bootstrap(); echo json_encode(['database'=>config('database.default'),'cache'=>config('cache.default'),'session'=>config('session.driver'),'queue'=>config('queue.default'),'broadcast'=>config('broadcasting.default'),'sqlite'=>DB::select('select sqlite_version() as version'),'source'=>config('relaticle.cloud'),'subscriber_sync'=>config('mailcoach-sdk.enabled_subscribers_sync')]);"
 resolved=json.loads(run(['docker','exec','study-relaticle','php','-r',code],'resolved-config'));assert [resolved[k] for k in ['database','cache','session','queue','broadcast']]==['sqlite','database','database','sync','null'];(out/'resolved-config.json').write_text(json.dumps(resolved,indent=2))
 report['stage']='native_api_controls';save();run(['node',str(R/'evaluation/relaticle-ordinary-v1/run.mjs')],'browser',cap=300,env=env);report['status']='ordinary_role1_passed'
except Exception as e:report.update(status='ordinary_role1_unavailable',error_type=type(e).__name__,error=str(e));(private/'failure.log').write_text(traceback.format_exc())
finally:
 cp=subprocess.run(['docker','logs','study-relaticle'],capture_output=True,timeout=15);(private/'container.log').write_bytes(cp.stdout+cp.stderr)
 token=private/'token.secret'
 if token.exists():sensitive.append(token.read_text())
 for f in private.glob('*.log'):
  if f.stem in ['before-schema','after-schema']:continue
  text=f.read_text(errors='replace')
  for secret in sensitive:text=text.replace(secret,'[REDACTED]')
  (out/f.name).write_text(text)
 report['elapsed_seconds']=time.monotonic()-start;save();subprocess.run(['docker','rm','-f','study-relaticle'],capture_output=True,timeout=20);subprocess.run(['docker','network','rm','study-relaticle-net'],capture_output=True,timeout=10)
print(json.dumps(report));raise SystemExit(0 if report['status']=='ordinary_role1_passed' else 1)
