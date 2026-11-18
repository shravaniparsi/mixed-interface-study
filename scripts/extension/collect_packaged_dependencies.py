"""Collect a published bounded dependency wave once; never execute source."""
import argparse
import base64
import hashlib
import json
import subprocess
import urllib.request
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--wave',type=int,required=True)
    parser.add_argument('--freeze',required=True)
    args=parser.parse_args()
    relative=f'manifests/maintained-packaged-dependencies-v{args.wave}.json'
    raw=(ROOT/relative).read_bytes()
    frozen=subprocess.check_output(['git','show',args.freeze+':'+relative],cwd=ROOT)
    if raw!=frozen:
        raise SystemExit('Schedule differs from declared freeze')
    schedule=json.loads(raw)
    if max(schedule['cumulative_files'].values())>24:
        raise SystemExit('Dependency allowance exceeded')
    out=Path(f'/private/tmp/maintained-packaged-dependencies-v{args.wave}')
    manifest=ROOT/f'manifests/maintained-packaged-dependency-collection-v{args.wave}.json'
    if out.exists() or manifest.exists():
        raise SystemExit('Refusing repeat or overwrite')
    out.mkdir()
    token=subprocess.check_output(['gh','auth','token'],text=True).strip()
    rows=[]
    for entry in schedule['rows']:
        row=dict(entry)
        if row['size']>262144:
            row['status']='oversized_source';rows.append(row);continue
        try:
            request=urllib.request.Request('https://api.github.com/repos/'+row['repository']+'/git/blobs/'+row['blob'],headers={'Authorization':'Bearer '+token,'Accept':'application/vnd.github+json','User-Agent':'mixed-interface-study'})
            with urllib.request.urlopen(request,timeout=30) as response:
                envelope=response.read(524289)
            if len(envelope)>524288:
                raise ValueError('Blob envelope exceeds bound')
            blob=json.loads(envelope)
            assert blob['encoding']=='base64'
            data=base64.b64decode(blob['content'])
            assert len(data)==row['size']
            assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==row['blob']
            path=out/(str(row['index'])+'.txt');path.write_bytes(data)
            row.update(status='collected_verified',sha256=hashlib.sha256(data).hexdigest(),local_path=str(path))
        except Exception as exc:
            row.update(status='collection_error',error_type=type(exc).__name__,error=str(exc))
        rows.append(row)
    manifest.write_text(json.dumps(dict(schedule_freeze=args.freeze,schedule_sha256=hashlib.sha256(raw).hexdigest(),rows=rows),indent=2)+'\n')
    print(json.dumps([dict(path=r['path'],status=r['status']) for r in rows],indent=2))

if __name__=='__main__':
    main()
