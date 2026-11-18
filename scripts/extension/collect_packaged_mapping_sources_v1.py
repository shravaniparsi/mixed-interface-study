"""Retrieve only blobs in the published mapping schedule; preserve one-shot failures."""
import base64
import concurrent.futures
import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
SCHEDULE=ROOT/'manifests/maintained-packaged-mapping-schedule-v1.json'
OUT=Path('/private/tmp/maintained-packaged-mapping-source-v1')
MANIFEST=ROOT/'manifests/maintained-packaged-mapping-collection-v1.json'

def main():
    if OUT.exists() or MANIFEST.exists():
        raise SystemExit('Refusing to repeat or overwrite collection')
    OUT.mkdir()
    schedule=json.loads(SCHEDULE.read_text())
    jobs=[]
    for r in schedule['rows']:
        for kind,field in [('view','selected_views'),('deployment','selected_deployment')]:
            for entry in r.get(field,[]):
                jobs.append(dict(repository=r['repository'],rank=r['rank'],commit=r['commit'],kind=kind,path=entry['path'],blob=entry['sha'],size=entry['size'],index=len(jobs)+1))
    token=subprocess.check_output(['gh','auth','token'],text=True).strip()
    def collect(row):
        if row['size']>256*1024:
            return dict(row,status='oversized_source')
        try:
            request=urllib.request.Request('https://api.github.com/repos/'+row['repository']+'/git/blobs/'+row['blob'],headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','User-Agent':'mixed-interface-study'})
            with urllib.request.urlopen(request,timeout=30) as response:
                raw=response.read(512*1024+1)
            if len(raw)>512*1024:
                raise ValueError('Blob envelope exceeds bound')
            value=json.loads(raw)
            assert value['encoding']=='base64'
            data=base64.b64decode(value['content'])
            assert len(data)==row['size'] and len(data)<=256*1024
            assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==row['blob']
            path=OUT/(str(row['index'])+'.txt');path.write_bytes(data)
            return dict(row,status='collected_verified',sha256=hashlib.sha256(data).hexdigest(),local_path=str(path))
        except Exception as exc:
            return dict(row,status='collection_error',error_type=type(exc).__name__,error=str(exc))
    with concurrent.futures.ThreadPoolExecutor(max_workers=3) as pool:
        rows=list(pool.map(collect,jobs))
    MANIFEST.write_text(json.dumps(dict(kind='maintained_packaged_mapping_collection',schedule_freeze='ae08bd5be403bb9e10ffe6f75d86bd7fce7d88dc',schedule_sha256=hashlib.sha256(SCHEDULE.read_bytes()).hexdigest(),rows=rows),indent=2)+'\n')
    from collections import Counter
    print(json.dumps(dict(Counter(r['status'] for r in rows))))

if __name__=='__main__':
    main()
