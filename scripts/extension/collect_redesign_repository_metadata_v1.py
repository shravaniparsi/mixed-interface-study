#!/usr/bin/env python3
"""Collect the frozen redesign metadata schedule once, without source contents."""
import argparse
import hashlib
import json
from pathlib import Path
import re
import signal
import subprocess
import time
from urllib.parse import quote
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/editability-repairability-repository-metadata-v1'
CAP=64*1024*1024

def deadline(*_):raise TimeoutError('Per-repository 90-second deadline')

def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',required=True);args=ap.parse_args()
    assert re.fullmatch('[0-9a-f]{40}',args.freeze)
    names=['protocol/editability-repairability-repository-feasibility-v1.md','manifests/editability-repairability-repository-schedule-v1.json','scripts/extension/collect_redesign_repository_metadata_v1.py','results/editability-repairability-metadata-screen-v1/screen.json','manifests/editability-repairability-exposure-classes-v1.json']
    bindings={}
    for p in names:
        raw=(ROOT/p).read_bytes();assert raw==subprocess.check_output(['git','show',args.freeze+':'+p],cwd=ROOT)
        bindings[p]=hashlib.sha256(raw).hexdigest()
    schedule=json.loads((ROOT/names[1]).read_text());assert schedule['source_sha256']==bindings[names[3]]
    rows=schedule['rows'];assert len(rows)==40 and len({r['repository'] for r in rows})==40
    assert [r['sequence'] for r in rows]==list(range(1,41))
    assert [r['group'] for r in rows]==['development']*8+['evaluation']*32
    OUT.mkdir(exist_ok=False)
    result={'freeze':args.freeze,'input_sha256':bindings,'status':'in_progress','projects':[],'retained_response_bytes':0,'total_byte_cap_reached':False,'source_contents_acquired':False,'application_runs':0,'scientific_cases':0}
    signal.signal(signal.SIGALRM,deadline)
    for row in rows:
        project={**row,'requests':[],'status':'unavailable','lineage_independence':'unresolved'};result['projects'].append(project)
        if result['total_byte_cap_reached'] or result['retained_response_bytes']>=CAP:
            project['status']='unattempted_total_byte_cap';continue
        index=row['sequence'];repo=row['repository'];directory=OUT/f'{index:02d}';directory.mkdir()
        start=time.monotonic();signal.alarm(90)
        def get(endpoint,limit):
            remaining=90-(time.monotonic()-start)
            if remaining<=0 or len(project['requests'])>=3:raise ValueError('Request/time bound')
            request={'endpoint':endpoint};project['requests'].append(request)
            response=subprocess.run(['gh','api',endpoint],capture_output=True,timeout=min(30,remaining));request['exit_code']=response.returncode
            if response.returncode:
                request['error']=response.stderr.decode(errors='replace')[:1000];raise RuntimeError('Request failed')
            request['response_bytes']=len(response.stdout)
            if len(response.stdout)>limit:raise ValueError('Per-response byte cap')
            if result['retained_response_bytes']+len(response.stdout)>CAP:
                result['total_byte_cap_reached']=True
                raise ValueError('Total byte cap would be exceeded; response not retained')
            name=f'{len(project["requests"])}.json';(directory/name).write_bytes(response.stdout)
            result['retained_response_bytes']+=len(response.stdout)
            request.update(file=f'{index:02d}/'+name,sha256=hashlib.sha256(response.stdout).hexdigest())
            return json.loads(response.stdout)
        try:
            meta=get('repos/'+repo,1024*1024)
            project.update(canonical_repository=meta['full_name'],fork=meta['fork'],archived=meta['archived'],disabled=meta['disabled'],private=meta['private'],visibility=meta.get('visibility'),parent_repository=meta.get('parent',{}).get('full_name'),source_repository=meta.get('source',{}).get('full_name'))
            if meta['full_name'].lower()!=repo.lower():raise ValueError('Canonical identity mismatch: alias hold')
            if meta['fork'] or meta['archived'] or meta['disabled'] or meta['private'] or meta.get('visibility')!='public':raise ValueError('Frozen repository metadata eligibility check failed')
            ref=get('repos/'+repo+'/git/ref/heads/'+quote(meta['default_branch'],safe=''),1024*1024)
            revision=ref['object']['sha'];assert re.fullmatch('[0-9a-f]{40}',revision);project['revision']=revision
            tree=get('repos/'+repo+'/git/trees/'+revision+'?recursive=1',8*1024*1024)
            project['tree_response_locator_sha']=tree.get('sha')
            if tree['truncated']:raise ValueError('Truncated tree')
            project.update(tree_entries=len(tree['tree']),status='metadata_pinned_workflow_unqualified')
        except Exception as e:project.update(error_type=type(e).__name__,error=str(e))
        finally:signal.alarm(0)
        project['elapsed_seconds']=time.monotonic()-start
        (OUT/'collection.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({k:project[k] for k in ['sequence','repository','group','status']}),flush=True)
    result['status']='metadata_stage_closed'
    (OUT/'collection.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
