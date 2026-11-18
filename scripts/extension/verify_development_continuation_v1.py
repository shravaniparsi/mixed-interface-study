#!/usr/bin/env python3
"""Recompute ordinary continuation comparisons from retained phase observations."""
import argparse
import json
from pathlib import Path


def verify(path):
    m = json.loads(path.read_text())
    if m['kind'] != 'ordinary_development_continuation_control' or m['independent_evaluation_cases'] != 0:
        raise ValueError('Wrong development scope')
    if m['status'] != 'measurement_complete':
        return {'status':'qualification_failed','error':m.get('error'),'phases_started':[r['phase'] for r in m['phases']]}
    if [r['phase'] for r in m['phases']] != ['warm','seed','native','api']:
        raise ValueError('Incomplete phase schedule')
    phases = {}
    for phase in m['phases']:
        p = phase['phase']; r = json.loads((path.parent/(p+'-browser.json')).read_text())
        if r != phase['browser'] or r['status'] != 'observed':
            raise ValueError('Phase observation mismatch')
        if r['write_counts'] != {'authenticate':1,'create':int(p in ('warm','seed')),'update':int(p!='seed')}:
            raise ValueError('Wrong write counts')
        if p in ('warm','seed') and r['producer_status'] != 201:
            raise ValueError('Ordinary producer did not accept')
        if p in ('native','api') and (not r['seed_record_gate_passed'] or r['record'] != phases['seed']['record'] or r['actor'] != phases['seed']['actor']):
            raise ValueError('Seed record/actor mismatch')
        if p != 'seed':
            if r['consumer']['status'] != 200:
                raise ValueError('Ordinary update did not accept')
            body = {k:r['record'][k] for k in ['id','login','firstName','lastName','email','activated','langKey','authorities']}
            body['firstName'] = 'Edited'
            if r['consumer']['body'] != body:
                raise ValueError('Complete request differs from registered ordinary edit')
            expected = dict(r['record'], firstName='Edited', lastModifiedDate=r['after_edit']['lastModifiedDate'])
            if r['after_edit'] != expected:
                raise ValueError('Non-target returned field changed')
        phases[p] = r
    n,a,w = phases['native'],phases['api'],phases['warm']
    if not a['matched_start_gate_passed']:
        raise ValueError('API matching gate missing')
    without_time = lambda d: {k:v for k,v in d.items() if k!='lastModifiedDate'}
    checks = {'restored_start_full_record_equal':n['record']==a['record'],
              'restored_start_actor_equal':n['actor']==a['actor'],
              'restored_start_search_equal':n['search_before']==a['search_before'],
              'complete_update_body_equal':n['consumer']['body']==a['consumer']['body'],
              'both_updates_200':n['consumer']['status']==a['consumer']['status']==200,
              'after_record_equal_except_lastModifiedDate':without_time(n['after_edit'])==without_time(a['after_edit']),
              'warm_native_update_200':w['consumer']['status']==200,
              'post_update_search_equal':n['search_after']==a['search_after']}
    if not all(v for k,v in checks.items() if k!='post_update_search_equal'):
        raise ValueError('Registered ordinary comparison did not qualify')
    if checks != m['comparisons']:
        raise ValueError('Saved comparisons differ from evidence')
    if m['snapshot']['snapshot']['state']!='SUCCESS' or m['snapshot']['snapshot']['shards']['failed']:
        raise ValueError('Checkpoint snapshot failed')
    if len(m['restores'])!=2 or any(not r['relational_bytes_match_before_startup'] or r['response']['snapshot']['shards']['failed'] for r in m['restores']):
        raise ValueError('Restoration incomplete')
    return {'status':'ordinary_continuation_observations_verified','comparisons':checks,'independent_evaluation_cases':0,'general_continuation_equivalence_qualified':False}


if __name__=='__main__':
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('measurement',type=Path);a=p.parse_args()
    print(json.dumps(verify(a.measurement),indent=2))
