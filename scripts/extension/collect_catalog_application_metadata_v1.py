#!/usr/bin/env python3
"""Pin the fixed cohort's repository identities and trees, without source blobs."""
import hashlib
import json
import signal
import subprocess
import time
from pathlib import Path
from urllib.parse import quote

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/catalog-application-metadata-v1'

def deadline(*args):raise TimeoutError('Per-project 90-second deadline')

def main():
    raw=(ROOT/'manifests/catalog-cohort-v1.json').read_bytes();cohort=json.loads(raw)
    assert len(cohort['selected'])==12 and cohort['replacement_allowed'] is False
    OUT.mkdir(exist_ok=False)
    result={'cohort_sha256':hashlib.sha256(raw).hexdigest(),'projects':[],'status':'in_progress'}
    signal.signal(signal.SIGALRM,deadline)
    for index,repo in enumerate(cohort['selected'],1):
        directory=OUT/f'{index:02d}';directory.mkdir()
        project={'sequence':index,'repository':repo,'requests':[],'status':'unavailable'};result['projects'].append(project)
        start=time.monotonic();signal.alarm(90)
        def get(endpoint,limit):
            remaining=90-(time.monotonic()-start)
            if remaining<=0 or len(project['requests'])>=3:raise ValueError('Request/time bound')
            row={'endpoint':endpoint};project['requests'].append(row)
            response=subprocess.run(['gh','api',endpoint],capture_output=True,timeout=min(30,remaining))
            row['exit_code']=response.returncode
            if response.returncode:
                row['error']=response.stderr.decode(errors='replace')[:1000]
                raise RuntimeError('Request failed')
            if len(response.stdout)>limit:
                row['bytes']=len(response.stdout);raise ValueError('Response byte bound')
            name=f'{len(project["requests"])}.json';(directory/name).write_bytes(response.stdout)
            row.update(file=f'{index:02d}/'+name,bytes=len(response.stdout),sha256=hashlib.sha256(response.stdout).hexdigest())
            return json.loads(response.stdout)
        try:
            meta=get('repos/'+repo,1024*1024)
            project.update(canonical_repository=meta['full_name'],fork=meta['fork'],archived=meta['archived'],disabled=meta['disabled'],parent_repository=meta.get('parent',{}).get('full_name'),source_repository=meta.get('source',{}).get('full_name'))
            if meta['full_name'].lower()!=repo.lower():raise ValueError('Canonical identity mismatch: alias audit required')
            ref=get('repos/'+repo+'/git/ref/heads/'+quote(meta['default_branch'],safe=''),1024*1024)
            revision=ref['object']['sha'];project['revision']=revision
            tree=get('repos/'+repo+'/git/trees/'+revision+'?recursive=1',8*1024*1024)
            if tree['truncated']:raise ValueError('Truncated tree')
            project.update(tree_entries=len(tree['tree']),status='metadata_pinned_pending_source_qualification')
        except Exception as error:project.update(error_type=type(error).__name__,error=str(error))
        finally:signal.alarm(0)
        project['elapsed_seconds']=time.monotonic()-start
        (OUT/'collection.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({k:v for k,v in project.items() if k!='requests'}),flush=True)
    result['status']='fixed_cohort_metadata_stage_closed'
    (OUT/'collection.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':main()
