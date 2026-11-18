#!/usr/bin/env python3
"""Acquire only the published development source schedule; never execute it."""
import argparse
import base64
from collections import Counter
import hashlib
import json
from pathlib import Path
import re
import subprocess
import time
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/redesign-development-source-wave1-v1'
def main():
    ap=argparse.ArgumentParser();ap.add_argument('--freeze',required=True);args=ap.parse_args();assert re.fullmatch('[0-9a-f]{40}',args.freeze)
    names=['protocol/editability-repairability-development-source-v1.md','manifests/redesign-development-source-wave1-v1.json','scripts/extension/collect_redesign_development_source_wave1_v1.py','results/editability-repairability-repository-metadata-v1/collection.json','manifests/editability-repairability-repository-schedule-v1.json']
    bindings={}
    for name in names:
        raw=(ROOT/name).read_bytes();assert raw==subprocess.check_output(['git','show',args.freeze+':'+name],cwd=ROOT);bindings[name]=hashlib.sha256(raw).hexdigest()
    rows=json.loads((ROOT/names[1]).read_text())['rows'];assert len(rows)==28
    projects=json.loads((ROOT/names[3]).read_text())['projects']
    seen=set()
    for e in rows:
        p=projects[e['project_sequence']-1];assert p['group']=='development' and p['repository']==e['repository'] and p['revision']==e['revision']
        file=f'results/editability-repairability-repository-metadata-v1/{p["sequence"]:02d}/3.json';raw=(ROOT/file).read_bytes();assert hashlib.sha256(raw).hexdigest()==p['requests'][2]['sha256'];bindings[file]=hashlib.sha256(raw).hexdigest()
        entry=next(r for r in json.loads(raw)['tree'] if r['path']==e['path']);assert entry['sha']==e['blob_sha'] and entry['size']==e['declared_bytes'] and entry['type']=='blob'
        key=(e['repository'],e['path']);assert key not in seen;seen.add(key)
    OUT.mkdir(exist_ok=False);counts=Counter();used=Counter()
    result={'freeze':args.freeze,'input_sha256':bindings,'rows':[],'status':'in_progress','application_executed':False}
    for e in rows:
        start=time.monotonic();r=dict(e);result['rows'].append(r);repo=e['repository'];counts[repo]+=1
        try:
            assert counts[repo]<=256 and e['declared_bytes']<=1024*1024 and used[repo]+e['declared_bytes']<=16*1024*1024
            p=subprocess.run(['gh','api','repos/'+repo+'/git/blobs/'+e['blob_sha']],capture_output=True,timeout=30);r['exit_code']=p.returncode
            if p.returncode:raise RuntimeError(p.stderr.decode(errors='replace')[:1000])
            assert len(p.stdout)<=2*1024*1024
            name=str(e['sequence'])+'.json';(OUT/name).write_bytes(p.stdout);r.update(envelope=name,envelope_sha256=hashlib.sha256(p.stdout).hexdigest())
            value=json.loads(p.stdout);assert value['encoding']=='base64';raw=base64.b64decode(value['content']);assert len(raw)==e['declared_bytes']
            assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==e['blob_sha'];raw.decode('utf8')
            name=str(e['sequence'])+'.txt';(OUT/name).write_bytes(raw);used[repo]+=len(raw);r.update(file=name,bytes=len(raw),sha256=hashlib.sha256(raw).hexdigest(),status='collected_verified')
        except Exception as error:r.update(status='unavailable',error_type=type(error).__name__,error=str(error))
        r['elapsed_seconds']=time.monotonic()-start
        (OUT/'collection.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({k:r[k] for k in ['sequence','repository','path','status']}),flush=True)
    result.update(status='source_wave_closed',scheduled_counts=dict(counts),decoded_bytes=dict(used))
    (OUT/'collection.json').write_text(json.dumps(result,indent=2)+'\n')
if __name__=='__main__':main()
