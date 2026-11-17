#!/usr/bin/env python3
import argparse,hashlib,json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def load(p):return json.loads((ROOT/p).read_text())
def sha(p):return hashlib.sha256((ROOT/p).read_bytes()).hexdigest()
def build():
    cp='results/development-fixture-field-transfer-v1/measurement.json';dp='results/development-fixture-field-replay-v1/measurement.json';fp='results/development-test-serialization-v1/measurement.json'
    c,d,f=load(cp),load(dp),load(fp)
    assert c['input_sha256']==d['input_sha256']==sha(fp)
    assert c['evaluator_sha256']==sha('src/mixed_interface/constraint_transfer.py')
    assert c['lineage_sha256']==sha('manifests/development-lineage-v1.json')
    assert not d['errors'] and d['angular']=='14.2.0'
    assert len(c['rows'])==len(d['rows'])==15
    rows=[]
    for i,(x,y) in enumerate(zip(c['rows'],d['rows'])):
        fixture=f['rows'][i//3];field=['login','email','password'][i%3]
        assert x['id']==y['id']==fixture['id']+':'+field
        assert x['body_sha256']==y['body_sha256']==fixture['body_sha256']
        assert y['status']=='measured'
        rows.append({'id':x['id'],'transfer':x['verdict'],'native_replay':y['verdict']})
    return {'kind':'closed_controlled_field_projection_comparison','freeze':'5140925','rows':rows,'transfer_counts':dict(Counter(r['transfer'] for r in rows)),'replay_counts':dict(Counter(r['native_replay'] for r in rows)),'joint_determinate':sum(r['transfer'] in ['satisfied','violated'] and r['native_replay'] in ['satisfied','violated'] for r in rows),'joint_determinate_disagreements':sum(r['transfer']!=r['native_replay'] for r in rows if r['transfer'] in ['satisfied','violated'] and r['native_replay'] in ['satisfied','violated']),'additional_transfer_unknowns':sum(r['transfer']=='unknown' and r['native_replay']!='unknown' for r in rows),'full_state_reconstruction':False,'independent_evaluation_cases':0,'method_advantage_demonstrated':False,'hashes':{p:sha(p) for p in [cp,dp,fp]}}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args();d=build();path='manifests/development-fixture-field-comparison-v1.json'
    if a.verify:assert load(path)==d;print('All 15 field identities and matched-information outcomes verified.')
    else:(ROOT/path).write_text(json.dumps(d,indent=2)+'\n');print(json.dumps({k:v for k,v in d.items() if k.endswith('counts') or k=='additional_transfer_unknowns'}))
