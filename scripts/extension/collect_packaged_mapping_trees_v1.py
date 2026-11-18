"""One bounded metadata request per pinned repository; never fetch source contents."""
import concurrent.futures
import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
FREEZE = 'c9129f670e60726fe055bc52f5a44ca37d1eb9d2'
OUT = ROOT / 'results/maintained-packaged-mapping-trees-v1'
MANIFEST = ROOT / 'manifests/maintained-packaged-mapping-schedule-v1.json'
EXCLUDED = {'test','tests','__tests__','node_modules','vendor','dist','build','target','coverage','fixtures','examples'}

def key(row):
    return row['path'].encode('utf-8')

def allowed(row):
    path = row['path'].lower()
    return (row.get('type') == 'blob' and row.get('mode') in ('100644','100755')
            and not EXCLUDED.intersection(path.split('/'))
            and '.test.' not in path and '.spec.' not in path)

def main():
    import fnmatch
    if OUT.exists() or MANIFEST.exists():
        raise SystemExit('Refusing to overwrite or repeat collection')
    OUT.mkdir(parents=True)
    sources = json.loads((ROOT/'manifests/maintained-packaged-source-collection-v1.json').read_text())['rows']
    repos = {r['repository']:r for r in sources}
    token = subprocess.check_output(['gh','auth','token'], text=True).strip()
    def collect(item):
        repo, record = item
        row = {k:record[k] for k in ('repository','rank','commit')}
        request = urllib.request.Request('https://api.github.com/repos/'+repo+'/git/trees/'+record['commit']+'?recursive=1', headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','User-Agent':'mixed-interface-study'})
        try:
            with urllib.request.urlopen(request, timeout=45) as response:
                raw = response.read(8*1024*1024+1)
            path = OUT/(str(record['rank'])+'.json')
            path.write_bytes(raw)
            row.update(archive=str(path.relative_to(ROOT)),sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
            if len(raw)>8*1024*1024:
                row['status']='response_oversized';return row
            tree=json.loads(raw)
            pinned_root=json.loads((ROOT/'results/maintained-packaged-root-metadata-v1'/(str(record['rank'])+'-tree.json')).read_text())
            assert tree['sha']==pinned_root['sha'], 'Root tree identity mismatch'
            row.update(status='collected',tree_sha=tree['sha'],truncated=tree.get('truncated',False))
            blobs=[r for r in tree['tree'] if allowed(r)]
            views=sorted([r for r in blobs if r['path'].lower().endswith(('.tsx','.jsx','.vue','.svelte','.html','.component.ts')) and any(term in r['path'].lower() for term in ('form','create','edit','dialog','modal'))],key=key)
            existing={r['path'] for r in sources if r['repository']==repo}
            deployments=sorted([r for r in blobs if r['path'] not in existing and (r['path'].split('/')[-1].lower() in ('dockerfile','.env.example') or any(fnmatch.fnmatch(r['path'].split('/')[-1].lower(),pattern) for pattern in ('docker-compose*.yml','docker-compose*.yaml','compose*.yml','compose*.yaml')))],key=key)
            row.update(view_candidates=views,selected_views=views[:32],omitted_view_count=max(0,len(views)-32),deployment_candidates=deployments,selected_deployment=deployments[:4],omitted_deployment_count=max(0,len(deployments)-4))
        except Exception as exc:
            row.update(status='collection_error',error_type=type(exc).__name__,error=str(exc))
        return row
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        rows=sorted(pool.map(collect,repos.items()),key=lambda r:r['rank'])
    MANIFEST.write_text(json.dumps(dict(kind='maintained_packaged_mapping_source_schedule',protocol_freeze=FREEZE,rows=rows,quarantined=['go-vikunja/vikunja'],source_contents_collected=False),indent=2)+'\n')
    print(json.dumps([dict(repository=r['repository'],status=r['status'],truncated=r.get('truncated'),views=len(r.get('selected_views',[])),deployment=len(r.get('selected_deployment',[]))) for r in rows],indent=2))

if __name__=='__main__':
    main()
