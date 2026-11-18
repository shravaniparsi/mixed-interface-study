"""Bounded fixed-revision root metadata only; no source blob reads."""
import argparse, datetime, hashlib, json, re, subprocess, time
import urllib.request, urllib.parse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main():
 p=argparse.ArgumentParser();p.add_argument('--freeze',required=True);a=p.parse_args()
 for name in ['protocol/openapi-public-root-metadata-v1.md','scripts/extension/collect_openapi_root_metadata_v1.py','results/openapi-public-metadata-v1/response.json']:
  if (ROOT/name).read_bytes()!=subprocess.check_output(['git','show',a.freeze+':'+name],cwd=ROOT):raise SystemExit('Frozen artifact mismatch')
 out=ROOT/'results/openapi-public-root-metadata-v1';manifest=ROOT/'manifests/openapi-public-root-metadata-v1.json'
 if out.exists() or manifest.exists():raise SystemExit('Refusing retry/overwrite')
 out.mkdir();started=time.monotonic();token=subprocess.check_output(['gh','auth','token'],text=True,timeout=10).strip();rows=[]
 def get(repo,endpoint,label):
  remaining=600-(time.monotonic()-started)
  if remaining<=0:raise TimeoutError('Overall deadline')
  req=urllib.request.Request('https://api.github.com/repos/'+repo+'/'+endpoint,headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','User-Agent':'mixed-interface-study'})
  with urllib.request.urlopen(req,timeout=min(30,remaining)) as r:data=r.read(2097153)
  path=out/(label+'.json');path.write_bytes(data)
  if len(data)>2097152:raise ValueError('Metadata size ceiling')
  return json.loads(data)
 source=json.loads((ROOT/'results/openapi-public-metadata-v1/response.json').read_text())
 for rank,r in enumerate(source['items'],1):
  repo=r['full_name']
  if repo=='prest/prest':rows.append(dict(rank=rank,repository=repo,status='prior_exposure_quarantine'));continue
  row=dict(rank=rank,repository=repo,observed_at=datetime.datetime.now(datetime.timezone.utc).isoformat())
  try:
   ref=get(repo,'git/ref/heads/'+urllib.parse.quote(r['default_branch'],safe=''),str(rank)+'-ref');sha=ref['object']['sha'];row['commit']=sha
   commit=get(repo,'git/commits/'+sha,str(rank)+'-commit');tree=get(repo,'git/trees/'+commit['tree']['sha'],str(rank)+'-tree')
   if tree.get('truncated'):raise ValueError('Incomplete root tree')
   entries=[e for e in tree['tree'] if e['type']=='blob' and e['mode']=='100644' and (re.fullmatch(r'(README|LICENSE|COPYING)(\.[^/]+)?',e['path'],re.I) or e['path'] in ('Dockerfile','compose.yml','compose.yaml','docker-compose.yml','docker-compose.yaml'))]
   entries.sort(key=lambda e:e['path'].encode('utf-8'))
   row.update(status='root_metadata_collected',tree=commit['tree']['sha'],matching_root_blobs=entries,selected_root_blobs=entries[:8])
  except Exception as exc:row.update(status='unavailable',error_type=type(exc).__name__,error=str(exc))
  rows.append(row)
 result=dict(freeze=a.freeze,rows=rows,source_contents_fetched=0,files={str(f.relative_to(ROOT)):hashlib.sha256(f.read_bytes()).hexdigest() for f in sorted(out.glob('*.json'))})
 manifest.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps([dict(repository=r['repository'],status=r['status'],selected=len(r.get('selected_root_blobs',[]))) for r in rows],indent=2))
if __name__=='__main__':main()
