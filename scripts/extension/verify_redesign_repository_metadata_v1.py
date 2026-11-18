#!/usr/bin/env python3
"""Check frozen split, metadata bytes, request identity and commit/tree bindings."""
import hashlib
import json
from collections import Counter
from pathlib import Path
from urllib.parse import quote
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/editability-repairability-repository-metadata-v1'

def main():
    x=json.loads((OUT/'collection.json').read_text());assert x['status']=='metadata_stage_closed'
    schedule=json.loads((ROOT/'manifests/editability-repairability-repository-schedule-v1.json').read_text())
    expected=schedule['rows'];actual=x['projects'];assert len(expected)==len(actual)==40
    ranked=sorted(expected,key=lambda r:(hashlib.sha256((schedule['seed']+r['repository']).encode()).hexdigest(),r['repository']))
    assert [r['repository'] for r in ranked]==[r['repository'] for r in expected]
    total=0;requests=0
    for i,(e,r) in enumerate(zip(expected,actual),1):
        assert all(r[k]==e[k] for k in ['sequence','repository','group','rank_sha256'])
        assert r['group']==('development' if i<=8 else 'evaluation')
        assert r['rank_sha256']==hashlib.sha256((schedule['seed']+r['repository']).encode()).hexdigest()
        assert len(r['requests'])<=3;requests+=len(r['requests']);bodies=[]
        for j,q in enumerate(r['requests'],1):
            if 'file' not in q:continue
            assert q['file']==f'{i:02d}/{j}.json'
            raw=(OUT/q['file']).read_bytes();assert len(raw)==q['response_bytes'];assert hashlib.sha256(raw).hexdigest()==q['sha256']
            assert len(raw)<=(8*1024*1024 if j==3 else 1024*1024)
            total+=len(raw);bodies.append(json.loads(raw))
        if r['status']=='metadata_pinned_workflow_unqualified':
            assert len(bodies)==3
            meta,ref,tree=bodies
            assert meta['full_name'].lower()==r['repository'].lower()
            assert not any(meta[k] for k in ['fork','private','archived','disabled']) and meta['visibility']=='public'
            assert ref['object']['sha']==r['revision']
            assert tree['truncated'] is False and len(tree['tree'])==r['tree_entries']
            assert tree['sha']==r['tree_response_locator_sha']
            assert [q['endpoint'] for q in r['requests']]==[
                'repos/'+r['repository'],
                'repos/'+r['repository']+'/git/ref/heads/'+quote(meta['default_branch'],safe=''),
                'repos/'+r['repository']+'/git/trees/'+r['revision']+'?recursive=1']
    assert total==x['retained_response_bytes']<=64*1024*1024 and requests<=120
    for p,h in x['input_sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h
    assert x['application_runs']==x['scientific_cases']==0 and x['source_contents_acquired'] is False
    report={'projects':40,'development_candidates':8,'evaluation_candidates':32,'requests':requests,'retained_bytes':total,'status_counts':dict(Counter(r['status'] for r in actual)), 'all_recorded_response_hashes_verified':True,'split_and_request_bindings_verified':True,'workflow_qualification_established':False,'lineage_independence_established':False,'collection_sha256':hashlib.sha256((OUT/'collection.json').read_bytes()).hexdigest()}
    out=OUT/'verification.json';encoded=json.dumps(report,indent=2)+'\n'
    if out.exists():assert out.read_text()==encoded
    else:out.write_text(encoded)
    print(json.dumps(report))
if __name__=='__main__':main()
