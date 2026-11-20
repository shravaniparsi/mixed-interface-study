"""Fail-closed public evidence export. Never upload the raw evidence directory."""
import hashlib,json,os,pathlib,re
SECRET_KEY=re.compile(r'(password|secret|token|authorization|cookie|cookies|sessions)$',re.I)
def clean(value,secrets):
 if isinstance(value,dict) and 'public.UserSession' in value:
  value={k:({**v,'rows':['[REDACTED]' for _ in v['rows']]} if k=='public.UserSession' else v) for k,v in value.items()}
 if isinstance(value,dict):return {k:('[REDACTED]' if SECRET_KEY.search(k) and not isinstance(v,(bool,type(None))) else clean(v,secrets)) for k,v in value.items()}
 if isinstance(value,list):return [clean(x,secrets) for x in value]
 if isinstance(value,str):
  if value.lstrip().startswith(('{','[')):
   try:return json.dumps(clean(json.loads(value),secrets),separators=(',',':'))
   except (ValueError,TypeError):pass
  for secret in secrets:value=value.replace(secret,'[REDACTED]')
 return value
ALLOWED={'freeze.txt','node-version.txt','python-version.txt','network-interfaces.json','network-routes.json','bundle-verification.json','environment.json','public-startup.json','browser-actor.json','api-token-response.json','api-actor.json','native-create-request.json','api-created.json','before.json','editor-before.json','edit-request.json','after.json','trace.json','response-capture.json','result.json','application.log','application-1.log','application-2.log','settings.json','checkpoint-state.json','checkpoint-repeat.json','checkpoint-after-backup.json','backup-logical-state.json','checkpoint-actor.json','checkpoint-form.json','checkpoint-browser-identity.json','warm-before.json','warm-request.json','warm-response.json','warm-api-after.json','warm-after.json','restored-before-start.json','restored-actor.json','restored-browser-identity.json','restored-form.json','restored-start-state.json','restored-repeat.json','restored-before.json','restored-request.json','restored-response.json','restored-api-after.json','restored-after.json','pg-versions.txt','pg-binaries.sha256','runtime-before.json','runtime-after.json'}
def export(base):
 source=base/'evidence';dest=base/'public-evidence';dest.mkdir(exist_ok=False)
 secrets=json.loads((base/'redaction-values.json').read_text()) if (base/'redaction-values.json').exists() else []
 assert all(isinstance(s,str) and len(s)>=8 for s in secrets)
 report={'status':'sanitized','policy':'exact captured credential replacement plus structured authentication-key redaction; raw HTML and images omitted','files':[],'omitted':[]}
 total=0
 for p in sorted(source.iterdir()):
  assert p.is_file() and not p.is_symlink()
  if p.name not in ALLOWED:report['omitted'].append(p.name);continue
  raw=p.read_bytes();total+=len(raw);assert len(raw)<=8*1024**2 and total<=32*1024**2
  text=raw.decode();value=json.loads(text) if p.suffix=='.json' else text
  v=clean(value,secrets);public=(json.dumps(v,indent=2)+'\n') if p.suffix=='.json' else v
  assert all(secret not in public for secret in secrets)
  (dest/p.name).write_text(public)
  report['files'].append({'file':p.name,'raw_sha256':hashlib.sha256(raw).hexdigest(),'public_sha256':hashlib.sha256(public.encode()).hexdigest(),'redacted':public!=text})
 (dest/'export.json').write_text(json.dumps(report,indent=2)+'\n')
 return report
if __name__=='__main__':export(pathlib.Path(os.environ['ORDINARY_BASE']))
