"""Size-capped public export. Raw credentials, database dumps and runtime binaries stay private."""
import base64,hashlib,json,pathlib,re
from source_check import require
AUTH_KEY=re.compile(r'^(?:password|secret|token|totpSecret|authorization|cookie|cookies|api_key|apiKey|INITIAL_API_KEY|SHLINK_SERVER_API_KEY|CORE_SECRET|dump)$',re.I)
OMIT_NAMES={'deployment.json','redaction-values.json','backend.env','client.env'}

def redacted(value):return '[REDACTED sha256:'+hashlib.sha256(str(value).encode()).hexdigest()+']'
def clean(value,secrets):
 if isinstance(value,dict):
  result={}
  for key,item in value.items():
   if key=='public.UserSession' and isinstance(item,dict):
    result[key]={**clean(item,secrets),'rows':[redacted(row) for row in item.get('rows',[])]}
   elif AUTH_KEY.fullmatch(key) and isinstance(item,str):result[key]=redacted(item)
   else:result[key]=clean(item,secrets)
  return result
 if isinstance(value,list):return [clean(v,secrets) for v in value]
 if isinstance(value,str):
  if value.lstrip().startswith(('{','[')):
   try:return json.dumps(clean(json.loads(value),secrets),separators=(',',':'))
   except (ValueError,TypeError):pass
  # Binary observations may encode cache contents. Never publish an encoded credential.
  try:
   decoded=base64.b64decode(value,validate=True)
   if any(secret.encode() in decoded for secret in secrets):return redacted(value)
  except (ValueError,TypeError):pass
  for secret in sorted(secrets,key=len,reverse=True):value=value.replace(secret,'[REDACTED]')
  return value
 return value

def export(base):
 base=pathlib.Path(base);secrets=[]
 if (base/'redaction-values.json').is_file():secrets+=json.loads((base/'redaction-values.json').read_text())
 if (base/'deployment.json').is_file():secrets.append(json.loads((base/'deployment.json').read_text())['api_key'])
 require(all(isinstance(s,str) and len(s)>=12 for s in secrets),'valid_private_redaction_values')
 secrets=list(set(secrets));dest=base/'public-evidence';require(not dest.exists(),'new_export_directory');dest.mkdir(mode=0o700)
 report=dict(status='in_progress',scoring_input='private raw evidence before redaction; public row digests attest to original rows and are not recomputed',files=[],omitted=[],public_bytes=0)
 try:
  for category in ['evidence','build-evidence']:
   source=base/category
   if not source.exists():continue
   require(not source.is_symlink(),'regular_evidence_directory')
   # Only top-level textual evidence; installed vendor sources and runtime archives are not exported.
   for p in sorted(source.iterdir()):
    require(not p.is_symlink(),'no_export_symlink',path=p.name)
    if not p.is_file() or p.name in OMIT_NAMES or p.suffix not in {'.json','.log','.txt','.lock','.Dockerfile','.diff'}:
     report['omitted'].append(category+'/'+p.name);continue
    raw=p.read_bytes();require(len(raw)<=16*1024**2,'raw_file_cap',file=p.name);text=raw.decode('utf-8')
    value=json.loads(text) if p.suffix in {'.json','.lock'} else text
    sanitized=clean(value,secrets);rendered=(json.dumps(sanitized,separators=(',',':'))+'\n') if p.suffix in {'.json','.lock'} else sanitized
    require(all(secret not in rendered for secret in secrets),'no_plaintext_credential',file=p.name)
    encoded=rendered.encode();report['public_bytes']+=len(encoded);require(report['public_bytes']<=32*1024**2,'total_public_size_cap')
    name=category+'--'+p.name;(dest/name).write_bytes(encoded)
    report['files'].append(dict(file=name,raw_sha256=hashlib.sha256(raw).hexdigest(),public_sha256=hashlib.sha256(encoded).hexdigest(),public_bytes=len(encoded),redacted=encoded!=raw))
  report['status']='sanitized';(dest/'export.json').write_text(json.dumps(report,indent=2)+'\n');return report
 except Exception:
  # Partial exports have no success marker and must never be uploaded.
  (dest/'EXPORT_FAILED').write_text('Sanitization did not complete. Do not upload this directory.\n');raise
if __name__=='__main__':
 import sys
 report=export(sys.argv[1]);print(json.dumps({'status':report['status'],'files':len(report['files']),'public_bytes':report['public_bytes']}))
