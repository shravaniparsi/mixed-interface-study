"""Durable, bounded, sanitized command evidence; not a research experiment runner."""
import hashlib,json,os,pathlib,re,selectors,signal,subprocess,time

def atomic(path,value):
 path=pathlib.Path(path);path.parent.mkdir(parents=True,exist_ok=True)
 temporary=path.with_name(path.name+'.pending')
 fd=os.open(temporary,os.O_WRONLY|os.O_CREAT|os.O_TRUNC,0o600)
 with os.fdopen(fd,'w') as f:json.dump(value,f,indent=2);f.write('\n');f.flush();os.fsync(f.fileno())
 os.replace(temporary,path)

def run(label,argv,path,*,timeout=30,output_limit=65536,secrets=(),env=None,cwd=None):
 if not re.fullmatch('[a-z][a-z0-9_-]{0,60}',label):raise ValueError('public stage label required')
 if timeout<=0 or output_limit<1:raise ValueError('positive bounds required')
 if any(not isinstance(s,str) or len(s)<8 or s in label for s in secrets):raise ValueError('invalid redaction value')
 redact=lambda s:replace(s,secrets)
 report={'stage':label,'status':'started','timeout_seconds':timeout,'output_limit_bytes':output_limit,'arguments_retained':False,'environment_retained':False}
 atomic(path,report) # Must succeed before any child can be launched.
 started=time.monotonic();proc=None;data=bytearray();selector=selectors.DefaultSelector()
 try:
  proc=subprocess.Popen(argv,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,start_new_session=True,cwd=cwd,env=env)
  report['pid']=proc.pid;atomic(path,report)
  selector.register(proc.stdout,selectors.EVENT_READ)
  while selector.get_map():
   remaining=timeout-(time.monotonic()-started)
   if remaining<=0:report['status']='timeout';break
   for key,_ in selector.select(min(remaining,0.05)):
    chunk=os.read(key.fileobj.fileno(),4096)
    if not chunk:selector.unregister(key.fileobj);continue
    room=output_limit-len(data);data.extend(chunk[:room])
    if len(chunk)>room:report['status']='output_limit';break
   if report['status']=='output_limit':break
  if report['status'] in ['timeout','output_limit']:
   try:os.killpg(proc.pid,signal.SIGKILL)
   except ProcessLookupError:pass
  try:code=proc.wait(timeout=max(0.01,timeout-(time.monotonic()-started)))
  except subprocess.TimeoutExpired:
   report['status']='timeout'
   try:os.killpg(proc.pid,signal.SIGKILL)
   except ProcessLookupError:pass
   code=proc.wait(timeout=5)
  report['exit_code']=code
  if report['status']=='started':report['status']='succeeded' if code==0 else 'failed'
 except OSError as e:report.update(status='launch_or_observation_error',error=redact(str(e)))
 finally:
  selector.close()
  if proc is not None:
   if proc.poll() is None:
    try:os.killpg(proc.pid,signal.SIGKILL)
    except ProcessLookupError:pass
    proc.wait(timeout=5)
   proc.stdout.close()
  raw=bytes(data);report['captured_bytes']=len(raw);report['captured_sha256']=hashlib.sha256(raw).hexdigest()
  text=raw.decode('utf-8',errors='replace')
  if report['status']=='output_limit' and secrets:
   # Withhold a possibly cut credential at the truncation boundary.
   tail=max(len(s) for s in secrets);text=text[:-tail] if len(text)>tail else '';report['truncation_tail_withheld']=True
  report['output']=redact(text);report['elapsed_seconds']=time.monotonic()-started
  atomic(path,report)
 return report

def replace(text,secrets):
 for value in sorted(secrets,key=len,reverse=True):text=text.replace(value,'[REDACTED]')
 return text
