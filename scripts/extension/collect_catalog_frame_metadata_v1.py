#!/usr/bin/env python3
"""Read fixed catalog metadata and root docs only; never software entries."""
import base64
import hashlib
import json
import subprocess
import time
from pathlib import Path
from urllib.parse import quote

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/catalog-frame-metadata-v1'
REPO='awesome-selfhosted/awesome-selfhosted-data'


def main():
    index=ROOT/'manifests/prior-repository-reference-index-v2.json'
    index_raw=index.read_bytes();assert json.loads(index_raw)['absence_proves_no_exposure'] is False
    OUT.mkdir(exist_ok=False);start=time.monotonic()
    result={'kind':'catalog_frame_metadata_feasibility','repository':REPO,'reference_index_sha256':hashlib.sha256(index_raw).hexdigest(),'rows':[],'status':'failed'}
    def get(endpoint,limit):
        remaining=120-(time.monotonic()-start)
        if remaining<=0 or len(result['rows'])>=5:raise ValueError('Request/time bound')
        row={'endpoint':endpoint};result['rows'].append(row)
        r=subprocess.run(['gh','api',endpoint],capture_output=True,timeout=min(30,remaining))
        row['exit_code']=r.returncode
        if r.returncode:row['error']=r.stderr.decode(errors='replace')[:1000];raise RuntimeError('Catalog request failed')
        if len(r.stdout)>limit:raise ValueError('Response byte bound')
        filename=str(len(result['rows']))+'.json';(OUT/filename).write_bytes(r.stdout)
        row.update(file=filename,bytes=len(r.stdout),sha256=hashlib.sha256(r.stdout).hexdigest())
        return json.loads(r.stdout)
    try:
        repo=get('repos/'+REPO,1024*1024)
        branch=repo['default_branch'];ref=get('repos/'+REPO+'/git/ref/heads/'+quote(branch,safe=''),1024*1024)
        revision=ref['object']['sha'];result['revision']=revision
        tree=get('repos/'+REPO+'/git/trees/'+revision+'?recursive=1',8*1024*1024)
        if tree['truncated']:raise ValueError('Truncated catalog tree')
        result['tree_entries']=len(tree['tree']);result['root_documents']=[]
        for label,names in [('readme',{'readme','readme.md','readme.rst','readme.txt'}),('license',{'license','license.md','license.txt','copying'})]:
            found=sorted([r for r in tree['tree'] if '/' not in r['path'] and r['path'].lower() in names and r['type']=='blob'],key=lambda r:r['path'].encode())
            if not found:result['root_documents'].append({'kind':label,'status':'absent'});continue
            item=found[0];body=get('repos/'+REPO+'/git/blobs/'+item['sha'],256*1024)
            if body['encoding']!='base64':raise ValueError('Unexpected blob encoding')
            raw=base64.b64decode(body['content'])
            if len(raw)>128*1024:raise ValueError('Decoded root document bound')
            if hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()!=item['sha']:raise ValueError('Root blob mismatch')
            raw.decode('utf8');(OUT/(label+'.txt')).write_bytes(raw)
            result['root_documents'].append({'kind':label,'path':item['path'],'blob_sha':item['sha'],'sha256':hashlib.sha256(raw).hexdigest(),'bytes':len(raw),'status':'verified'})
        result['status']='catalog_metadata_collected_no_application_selection'
    except Exception as error:result.update(error_type=type(error).__name__,error=str(error))
    result['elapsed_seconds']=time.monotonic()-start
    (OUT/'collection.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
