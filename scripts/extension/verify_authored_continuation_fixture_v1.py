#!/usr/bin/env python3
"""Verify retained authored observations without restarting the fixture."""
import hashlib
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
DIR=ROOT/'results/continuation-authored-fixture-v1-ci-44371691916'
def load(p):return json.loads(p.read_text())
def main():
    freeze='820ae95366a1e812ea9fdefce04cf7fc5b422358'
    assert (DIR/'freeze.txt').read_text().strip()==freeze
    run=load(DIR/'run.json');assert run['headSha']==freeze and run['status']=='completed' and run['conclusion']=='success'
    registration=load(ROOT/'manifests/continuation-authored-fixture-v1.json')
    for p,h in registration['sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,p
    planned=load(ROOT/'development/continuation-fixture-v1/cases.json')
    s=load(DIR/'summary.json');assert s['status']=='qualified_authored_fixture' and s['scientific_cases']==0
    assert s['node_version']=='v20.20.2' and len(s['cases'])==9
    assert [r['id'] for r in s['cases']]==[r['id'] for r in planned]
    baseline=load(DIR/'baseline-measurements.json')['rows'];assert [r['id'] for r in baseline]==[r['id'] for r in planned]
    rows={r['id']:r for r in s['cases']}
    for plan,r in zip(planned,s['cases']):
        assert r['expected']==r['observed']==plan['expected'] and r['matches_expected'] is True
        o=r['observation'];posts=[t for t in r['trace'] if t['path']=='/native/save' and t['method']=='POST']
        assert len(posts)==o['native_posts']
        assert [t['status'] for t in posts]==([o['submit_status']] if 'submit_status' in o else [])
        state=load(DIR/(r['id']+'-state.json'))
        if 'after' in o:assert state==o['after']
        assert all(t['path'] in ['/new','/edit/1','/api/create','/native/create','/api/read','/native/save','/favicon.ico'] for t in r['trace'])
    o=rows['native_blocking']['observation']
    assert o['producer_status']==201 and o['created']['title'] is None
    assert o['valid'] is False and o['invalid_events']==1 and o['native_posts']==0
    assert o['before']==o['after']==o['created']
    o=rows['backend_rejection']['observation'];assert o['producer_status']==422 and o['created'] is None
    assert load(DIR/'backend_rejection-state.json') is None
    o=rows['normalized_input']['observation'];assert o['input_title'] is None and o['created']['title']=='Default title'
    o=rows['authorization_failure']['observation'];assert o['producer_status']==201 and o['page_status']==401 and o['native_posts']==0
    o=rows['stale_state']['observation'];assert o['submit_status']==409
    assert o['after']=={**o['before'],'version':o['before']['version']+1}
    o=rows['missing_observation']['observation'];assert 'before' not in o and 'after' not in o
    assert [t['status'] for t in rows['missing_observation']['trace'] if t['path']=='/api/read']==[503,503]
    assert load(DIR/'missing_observation-state.json')['description']=='Edited description'
    frames={r['id']:r['declared_write_contract'] for r in baseline if r['declared_write_contract'] is not None}
    assert set(frames)=={'native_ordinary','api_ordinary','normalized_input','extra_write'}
    assert all(v['contract_violation']==(k=='extra_write') for k,v in frames.items())
    assert frames['extra_write']['frame']['frame_violations']==['title']
    for r in baseline:
        assert r['persistence']['schema_version']==2
        assert r['persistence']['persistence']['restart']=={'state':'not_planned'}
        assert r['persistence']['continuation']=={'state':'not_measured'}
    print(json.dumps({'authored_cases_verified':9,'ordinary_producer_controls':2,'unexpected_write_detected':True,'scientific_cases':0}))
if __name__=='__main__':main()
