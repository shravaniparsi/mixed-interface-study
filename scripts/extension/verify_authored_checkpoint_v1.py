#!/usr/bin/env python3
"""Recheck authored branch gates and complete write frames from saved evidence."""
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from mixed_interface.write_frame import equal
from mixed_interface.write_contract import check
DIR=ROOT/'results/continuation-authored-checkpoint-v1-ci-44374936403'
def load(p):return json.loads(p.read_text())
def main():
    freeze='75f1d963c60572592d2b2a812678183cef929f09'
    assert (DIR/'freeze.txt').read_text().strip()==freeze
    run=load(DIR/'run.json');assert run['headSha']==freeze and run['status']=='completed' and run['conclusion']=='success'
    reg=load(ROOT/'manifests/continuation-authored-checkpoint-v1.json')
    for p,h in reg['sha256'].items():assert hashlib.sha256((ROOT/p).read_bytes()).hexdigest()==h,p
    planned=load(ROOT/'development/continuation-checkpoint-v1/schedule.json');s=load(DIR/'summary.json')
    assert s['status']=='qualified_authored_checkpoint' and s['scientific_cases']==0
    assert s['node_version']=='v20.20.2'
    assert [g['id'] for g in s['groups']]==[g['id'] for g in planned]
    frames=[];n=0
    for plan,g in zip(planned,s['groups']):
        cp=g['checkpoint'];assert equal(cp['api'],cp['disk']) and cp['actor']=={'actor':'study'}
        assert cp['disk']['title']==plan['title']
        raw=json.dumps(cp['disk'],separators=(',',':')).encode();assert hashlib.sha256(raw).hexdigest()==g['checkpoint_sha256']
        assert [b['id'] for b in g['branches']]==[b['id'] for b in plan['branches']]
        for expected,b in zip(plan['branches'],g['branches']):
            n+=1;before=b['before']
            actor=before['actor_status']==200 and equal(before['actor'],cp['actor']) and equal(before['storage'],cp['storage'])
            state=all(equal(before[k],cp[k]) for k in ['disk','api','form'])
            assert b['actor_gate'] is actor and b['state_gate'] is state
            assert b['expected']==b['observed']==expected['expected'] and b['matches_expected']
            posts=[t for t in b['trace'] if t['method']=='POST'];assert len(posts)==b['native_posts']
            if b['id'] in ['corrupt_state','corrupt_actor']:
                assert not posts and 'after' not in b
                assert (not actor) if b['id']=='corrupt_actor' else (actor and not state)
                continue
            assert actor and state and b['checkpoint_bytes_match']
            if b['id']!='warm':assert b['epoch']>g['branches'][0]['epoch']
            if b['observed']=='blocked':
                assert b['valid'] is False and b['invalid_events']==1 and not posts
                assert equal(b['after'],before['disk'])
            else:
                assert b['submit_status']==200 and len(posts)==1 and posts[0]['status']==200
                from urllib.parse import parse_qsl
                assert dict(parse_qsl(posts[0]['body'],keep_blank_values=True))==b['form_before_click']
                assignments={'description':'Edited description'}
                if b['id']=='restored_repair':assignments['title']='Repaired title'
                frame=check({'id':g['id']+'/'+b['id'],'before':before['disk'],'after':b['after'],
                             'contract':{'assignments':assignments,'derived_assignments':{'version':before['disk']['version']+1}}})
                assert not frame['contract_violation'];frames.append(frame['id'])
        warm,sham,repair=g['branches'][:3]
        assert equal(warm['after'],sham['after']) and warm['observed']==sham['observed']
        assert equal(warm['form_before_click'],sham['form_before_click'])
        assert equal(repair['form_before_click'],{**sham['form_before_click'],'title':'Repaired title'})
        assert equal(repair['before'],sham['before'])
    assert n==8 and len(frames)==4
    print(json.dumps({'authored_branches_verified':n,'complete_write_frames_verified':len(frames),'scientific_cases':0}))
if __name__=='__main__':main()
