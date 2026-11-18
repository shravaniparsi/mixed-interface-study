#!/usr/bin/env python3
"""Collect exactly the published root/setup source wave, without execution."""
import argparse
import base64
import hashlib
import json
import subprocess
from collections import Counter
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/catalog-source-wave28-v1'

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--freeze',required=True);args=parser.parse_args()
    assert len(args.freeze)==40 and all(c in '0123456789abcdef' for c in args.freeze), 'Full immutable commit required'
    names=['protocol/catalog-application-qualification-v1.md','protocol/catalog-source-wave28-v1.md','manifests/catalog-source-wave28-schedule-v1.json','scripts/extension/collect_catalog_source_wave28_v1.py','results/catalog-source-wave1-v1/collection.json','results/catalog-source-wave2-v1/collection.json','results/catalog-source-wave3-v1/collection.json','results/catalog-source-wave4-v1/collection.json','results/catalog-source-wave5-v1/collection.json','results/catalog-source-wave6-v1/collection.json','results/catalog-source-wave7-v1/collection.json','results/catalog-source-wave8-v1/collection.json','results/catalog-source-wave9-v1/collection.json','results/catalog-source-wave10-v1/collection.json','results/catalog-source-wave11-v1/collection.json','results/catalog-source-wave12-v1/collection.json','results/catalog-source-wave13-v1/collection.json','results/catalog-source-wave14-v1/collection.json','results/catalog-source-wave15-v1/collection.json','results/catalog-source-wave16-v1/collection.json','results/catalog-source-wave17-v1/collection.json','results/catalog-source-wave18-v1/collection.json','results/catalog-source-wave19-v1/collection.json','results/catalog-source-wave20-v1/collection.json','results/catalog-source-wave21-v1/collection.json','results/catalog-source-wave22-v1/collection.json','results/catalog-source-wave23-v1/collection.json','results/catalog-source-wave24-v1/collection.json','results/catalog-source-wave25-v1/collection.json','results/catalog-source-wave26-v1/collection.json','results/catalog-source-wave27-v1/collection.json']
    hashes={}
    for name in names:
        raw=(ROOT/name).read_bytes()
        assert raw==subprocess.check_output(['git','show',args.freeze+':'+name],cwd=ROOT)
        hashes[name]=hashlib.sha256(raw).hexdigest()
    entries=json.loads((ROOT/names[2]).read_text())['rows'];assert len(entries)==5
    OUT.mkdir(exist_ok=False)
    result={'freeze':args.freeze,'artifact_hashes':hashes,'rows':[],'application_executed':False,'status':'in_progress'}
    prior=[json.loads((ROOT/f'results/catalog-source-wave{wave}-v1/collection.json').read_text()) for wave in [1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27]]
    assert all(p['status']=='source_wave_closed' for p in prior)
    previous=[r for p in prior for r in p['rows']]
    counts=Counter(r['repository'] for r in previous);used=Counter()
    for r in previous:
        if r['status']=='collected_verified':used[r['repository']]+=r['bytes']
    assert dict(counts)==prior[-1]['scheduled_counts'] and dict(used)==prior[-1]['decoded_bytes']
    seen={(r['repository'],r['path']) for r in previous}
    for e in entries:
        assert (e['repository'],e['path']) not in seen
        seen.add((e['repository'],e['path']))
    for entry in entries:
        row=dict(entry);result['rows'].append(row);repo=entry['repository'];counts[repo]+=1
        try:
            if counts[repo]>256 or entry['declared_bytes']>256*1024 or used[repo]+entry['declared_bytes']>8*1024*1024:raise ValueError('Source acquisition bound')
            response=subprocess.run(['gh','api','repos/'+repo+'/git/blobs/'+entry['blob_sha']],capture_output=True,timeout=30)
            row['exit_code']=response.returncode
            if response.returncode:
                row['error']=response.stderr.decode(errors='replace')[:1000];raise RuntimeError('Request failed')
            if len(response.stdout)>512*1024:raise ValueError('Envelope bound')
            name=str(entry['sequence'])+'.json';(OUT/name).write_bytes(response.stdout)
            row.update(envelope=name,envelope_sha256=hashlib.sha256(response.stdout).hexdigest())
            body=json.loads(response.stdout);assert body['encoding']=='base64'
            raw=base64.b64decode(body['content']);assert len(raw)==entry['declared_bytes']
            assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==entry['blob_sha']
            raw.decode('utf8');used[repo]+=len(raw)
            name=str(entry['sequence'])+'.txt';(OUT/name).write_bytes(raw)
            row.update(status='collected_verified',file=name,sha256=hashlib.sha256(raw).hexdigest(),bytes=len(raw))
        except Exception as error:row.update(status='unavailable',error_type=type(error).__name__,error=str(error))
        (OUT/'collection.json').write_text(json.dumps(result,indent=2)+'\n')
        print(json.dumps({k:row[k] for k in ['sequence','repository','path','status']}),flush=True)
    result.update(status='source_wave_closed',scheduled_counts=dict(counts),decoded_bytes=dict(used))
    (OUT/'collection.json').write_text(json.dumps(result,indent=2)+'\n')

if __name__=='__main__':main()
