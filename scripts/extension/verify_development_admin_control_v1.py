#!/usr/bin/env python3
"""Verify retained paired controls, including failures, without rerunning them."""
import argparse, hashlib, json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RUN=44105021413

def build():
    rows=[]
    for arm in ['ui','api']:
        archive=ROOT/f'results/development-admin-control-v1-{arm}-ci-{RUN}'
        def read(name):return json.loads((archive/name).read_text())
        run=read('github-run.json');m=read('measurement.json');u=read('admin-workflow.json') if (archive/'admin-workflow.json').exists() else {'arm':arm,'status':'not_run','stages':[],'error':'Application failed before browser execution','write_counts':{},'independent_evaluation_cases':0}
        assert run['id']==RUN and run['head_sha'].startswith('464e501')
        if u['status']=='not_run':
            assert m['readiness_response_observed'] is False and m['process_exit_before_cleanup']==1
            assert 'java.net.UnknownHostException' in (archive/'application.log').read_text()
        assert u['arm']==arm and u['independent_evaluation_cases']==0
        assert m['jar_sha256']=='1c7500685740eb01994aa13ea381f3eb9af2c65bfb92f2379e42bb909225c71b'
        assert {i['ifname'] for i in read('interfaces.json')}=={'lo'}
        assert all(n<=1 for n in u['write_counts'].values())
        if u['status']=='qualified':
            assert m['status']=='admin_workflow_qualified' and m['browser_exit']==0
            assert u['producer']['body']==u['expected_create'] and u['producer']['status']==201
            assert u['consumer']['status']==200
            assert u['after_create']['id'] is not None
            assert dict(u['after_create'],id=None)==u['expected_create']
            assert u['after_edit']==dict(u['after_create'],firstName='Edited')
            assert u['write_counts']=={'authenticate':1,'create':1,'update':1}
            assert u['edit_save_enabled_before'] is True
        rows.append({'arm':arm,'status':u['status'],'stages':u['stages'],'error':u.get('error'),'elapsed_seconds':m['elapsed_seconds'],'hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(archive.iterdir()) if p.is_file()}})
    return {'kind':'closed_ordinary_admin_workflow_controls','run_id':RUN,'arms':rows,'both_qualified':all(r['status']=='qualified' for r in rows),'independent_evaluation_cases':0,'natural_defects_demonstrated':0}

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args();d=build();out=ROOT/'manifests/development-admin-control-v1.json'
    if a.verify:assert json.loads(out.read_text())==d
    else:out.write_text(json.dumps(d,indent=2)+'\n')
    print(json.dumps({'both_qualified':d['both_qualified'],'arms':[{k:v for k,v in r.items() if k!='hashes'} for r in d['arms']]},indent=2))
