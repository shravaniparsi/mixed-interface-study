#!/usr/bin/env python3
"""Fetch only registered catalog schema documents; execute none."""
import base64
import hashlib
import json
import subprocess
import time
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/catalog-schema-v1'

def main():
    raw=(ROOT/'manifests/catalog-schema-schedule-v1.json').read_bytes()
    schedule=json.loads(raw)
    assert len(schedule['files'])==4
    OUT.mkdir(exist_ok=False)
    start=time.monotonic();used=0
    result={'schedule_sha256':hashlib.sha256(raw).hexdigest(),'rows':[], 'status':'failed'}
    try:
        for entry in schedule['files']:
            row=dict(entry);result['rows'].append(row)
            remaining=120-(time.monotonic()-start)
            if remaining<=0:raise ValueError('Total deadline')
            response=subprocess.run(['gh','api','repos/'+schedule['repository']+'/git/blobs/'+entry['blob_sha']],capture_output=True,timeout=min(30,remaining))
            row['exit_code']=response.returncode
            if response.returncode:
                row['error']=response.stderr.decode(errors='replace')[:1000]
                raise RuntimeError('Request failed')
            if len(response.stdout)>512*1024:raise ValueError('Envelope bound')
            name=str(entry['sequence'])+'.json';(OUT/name).write_bytes(response.stdout)
            row.update(envelope=name,envelope_sha256=hashlib.sha256(response.stdout).hexdigest())
            data=json.loads(response.stdout)
            assert data['encoding']=='base64'
            content=base64.b64decode(data['content'])
            if len(content)>256*1024 or used+len(content)>512*1024:raise ValueError('Decoded bound')
            used+=len(content)
            assert hashlib.sha1(b'blob '+str(len(content)).encode()+b'\0'+content).hexdigest()==entry['blob_sha']
            assert len(content)==entry['declared_bytes']
            content.decode('utf8')
            name=str(entry['sequence'])+'.txt';(OUT/name).write_bytes(content)
            row.update(file=name,sha256=hashlib.sha256(content).hexdigest(),bytes=len(content),status='verified')
        result['status']='schema_documents_collected_no_application_selection'
    except Exception as error:
        result.update(error_type=type(error).__name__,error=str(error))
    result.update(elapsed_seconds=time.monotonic()-start,decoded_bytes=used)
    (OUT/'collection.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
