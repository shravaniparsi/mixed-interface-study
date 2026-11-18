"""Collect only frozen root-document blobs once, without execution."""
import argparse,base64,hashlib,json,subprocess,time
import urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--freeze',required=True);a=p.parse_args()
 names=['protocol/openapi-public-root-content-v1.md','manifests/openapi-public-root-content-schedule-v1.json','scripts/extension/collect_openapi_root_content_v1.py']
 hashes={}
 for name in names:
  raw=(ROOT/name).read_bytes()
  if raw!=subprocess.check_output(['git','show',a.freeze+':'+name],cwd=ROOT):raise SystemExit('Frozen artifact mismatch')
  hashes[name]=hashlib.sha256(raw).hexdigest()
 out=Path('/private/tmp/openapi-public-root-content-v1');dest=ROOT/'manifests/openapi-public-root-content-collection-v1.json'
 if out.exists() or dest.exists():raise SystemExit('Refusing retry/overwrite')
 out.mkdir();started=time.monotonic();token=subprocess.check_output(['gh','auth','token'],text=True,timeout=10).strip();rows=[]
 for entry in json.loads((ROOT/names[1]).read_text())['rows']:
  row=dict(entry)
  if row['size']>262144:row['status']='oversized_source';rows.append(row);continue
  try:
   remaining=900-(time.monotonic()-started)
   if remaining<=0:raise TimeoutError('Collection deadline')
   req=urllib.request.Request('https://api.github.com/repos/'+row['repository']+'/git/blobs/'+row['blob'],headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','User-Agent':'mixed-interface-study'})
   with urllib.request.urlopen(req,timeout=min(30,remaining)) as response:raw=response.read(524289)
   if len(raw)>524288:raise ValueError('Encoded size ceiling')
   envelope=json.loads(raw)
   if envelope['encoding']!='base64':raise ValueError('Unexpected encoding')
   data=base64.b64decode(envelope['content'])
   if len(data)!=row['size'] or len(data)>262144:raise ValueError('Size mismatch')
   if hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()!=row['blob']:raise ValueError('Git blob mismatch')
   path=out/(str(row['index'])+'.txt');path.write_bytes(data)
   row.update(status='collected_verified',sha256=hashlib.sha256(data).hexdigest(),local_path=str(path))
  except Exception as exc:row.update(status='unavailable',error_type=type(exc).__name__,error=str(exc))
  rows.append(row)
 dest.write_text(json.dumps(dict(freeze=a.freeze,artifact_hashes=hashes,rows=rows,application_executed=False),indent=2)+'\n')
 print(json.dumps([dict(index=r['index'],status=r['status']) for r in rows],indent=2))
if __name__=='__main__':main()
