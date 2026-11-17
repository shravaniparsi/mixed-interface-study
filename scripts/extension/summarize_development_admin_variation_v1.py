#!/usr/bin/env python3
"""Summarize a closed nine-case schedule from retained evidence, never execute it."""
import argparse,collections,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RUN=44106848687

def build():
    schedule=json.loads((ROOT/'manifests/development-admin-variation-schedule-v1.json').read_text());rows=[]
    for case in schedule['cases']:
        archive=ROOT/f"results/development-admin-variation-v1-{case['id']}-ci-{RUN}"
        def read(name):return json.loads((archive/name).read_text())
        run=read('github-run.json');m=read('measurement.json')
        assert run['id']==RUN and run['head_sha'].startswith('818e315') and run['status']=='completed'
        assert m['jar_sha256']=='1c7500685740eb01994aa13ea381f3eb9af2c65bfb92f2379e42bb909225c71b'
        assert read('hostname-resolution.json')['address']=='127.0.0.1'
        assert {i['ifname'] for i in read('interfaces.json')}=={'lo'}
        u=read('admin-variation.json') if (archive/'admin-variation.json').exists() else None
        row={'case':case,'outcome':'not_run','runtime_status':m['status'],'elapsed_seconds':m['elapsed_seconds']}
        if u:
            assert u['case']==case and u['independent_evaluation_cases']==0
            assert all(n<=1 for n in u['write_counts'].values())
            row.update(outcome=u.get('outcome','harness_failure'),status=u['status'],error=u.get('error'),producer_status=u.get('producer',{}).get('status'),save_enabled_after_unrelated_edit=u.get('save_enabled_after_unrelated_edit'),save_enabled_after_target_repair=u.get('save_enabled_after_target_repair'))
            if row['outcome']=='producer_rejected':assert 400<=row['producer_status']<500 and u['write_counts']['update']==0
            if row['outcome'] in ['native_edit_saved','blocked_then_target_repair_saved']:
                assert row['producer_status']==201 and u['consumer']['status']==200
                assert u['after_create']['id']==u['after_edit']['id']
                assert u['after_edit'][u['edit_field']]=='Edited'
            if row['outcome']=='blocked_then_target_repair_saved':
                assert row['save_enabled_after_unrelated_edit'] is False and row['save_enabled_after_target_repair'] is True
                assert u['after_edit'][case['field']]==u['expected_create'][case['field']]
            row['page_errors']=u['page_errors']
            if 'after_create' in u:
                row['created_non_target_differences']={k:{'ordinary':v,'stored':u['after_create'].get(k)} for k,v in u['expected_create'].items() if k not in ['id',case['field']] and u['after_create'].get(k)!=v}
            if 'after_edit' in u:
                row['other_edit_changes']={k:{'before':v,'after':u['after_edit'].get(k)} for k,v in u['after_create'].items() if k not in [case['field'],u['edit_field']] and u['after_edit'].get(k)!=v}
            if case['id']=='control':
                assert row['outcome']=='native_edit_saved'
                assert not row['created_non_target_differences'] and not row['other_edit_changes']
        row['hashes']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(archive.iterdir()) if p.is_file()};rows.append(row)
    assert len(rows)==9
    return {'kind':'closed_exposed_development_input_variations','run_id':RUN,'cases':rows,'outcome_counts':dict(collections.Counter(r['outcome'] for r in rows)),'independent_evaluation_cases':0,'independent_defect_count_established':False}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args();d=build();out=ROOT/'manifests/development-admin-variation-v1.json'
    if a.verify:assert json.loads(out.read_text())==d
    else:out.write_text(json.dumps(d,indent=2)+'\n')
    print(json.dumps({'counts':d['outcome_counts'],'cases':[{k:v for k,v in r.items() if k!='hashes'} for r in d['cases']]},indent=2))
