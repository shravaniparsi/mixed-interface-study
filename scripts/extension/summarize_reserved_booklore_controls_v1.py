#!/usr/bin/env python3
"""Verify ordinary-control traces, fresh reset identities and cross-arm equivalence."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RUN=44217681753
ORDINARY={'oidcGroupClaim':'study-readers','isAdmin':False,'permissions':['permissionRead'],'libraryIds':[],'description':'Study description'}
def build():
 archive=ROOT/f'results/reserved-booklore-controls-v1-ci-{RUN}'
 def read(p):return json.loads(p.read_text())
 run=read(archive/'github-run.json');assert run['id']==RUN and run['head_sha']=='b10e0225e3dc65828c8394c915fc8b0db65cf4ba' and run['status']=='completed'
 rows=[];traces=[];ids={'app':[],'db':[],'network':[]}
 for arm in ['ui-ui','api-ui','api-api']:
  p=archive/arm
  r=read(p/'runtime.json') if (p/'runtime.json').exists() else {'status':'not_reached_or_interrupted'}
  row={'arm':arm,'runtime_status':r['status'],'elapsed_seconds':r.get('elapsed_seconds'),'error':r.get('error'),'qualified':False}
  if (p/'control.json').exists():
   c=read(p/'control.json');assert c['arm']==arm and c['independent_evaluation_cases']==0
   row.update(control_status=c['status'],control_error=c.get('error'),stages=c['stages'],blocked=c['blocked'])
   assert all(v<=1 for v in c['write_counts'].values())
   if c['status']=='qualified':
    assert r['status']=='qualified' and r['browser_exit']==0
    assert c['write_counts']=={'create':1,'update':1}
    assert c['producer']['body']==ORDINARY
    assert all(200<=c[k]['status']<300 for k in ['producer','consumer'])
    assert all(c['after_create'][k]==v for k,v in ORDINARY.items())
    assert c['after_create']['id'] is not None
    expected=dict(c['after_create'],description='Edited description',permissions=['permissionRead'],libraryIds=[])
    assert c['consumer']['body']==expected and c['after_edit']==expected
    assert c['stages']==['original_local_admin_and_settings','mapping_persisted','edit_persisted']
    net=read(p/'network.json')[0];assert net['Internal'] is True;ids['network'].append(net['Id'])
    for label,name in [('app','study-booklore-app'),('db','study-booklore-db')]:ids[label].append(read(p/(name+'.json'))[0]['Id'])
    traces.append(c);row['qualified']=True
  rows.append(row)
 all_qualified=all(r['qualified'] for r in rows)
 equivalence=False
 if all_qualified:
  assert all(len(v)==3 and len(set(v))==3 for v in ids.values())
  def omit_id(x):return {k:v for k,v in x.items() if k!='id'}
  for field in ['after_create','after_edit']:
   assert all(omit_id(c[field])==omit_id(traces[0][field]) for c in traces)
  assert all(omit_id(c['consumer']['body'])==omit_id(traces[0]['consumer']['body']) for c in traces)
  equivalence=True
 return {'kind':'closed_booklore_ordinary_controls','run_id':RUN,'rows':rows,'all_qualified':all_qualified,'cross_arm_equivalence':equivalence,'independent_evaluation_cases':0,'interpretation':'Ordinary qualification only; no input-variation or defect finding.','evidence_hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(archive.rglob('*')) if p.is_file()}}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args();d=build();out=ROOT/'manifests/reserved-booklore-controls-v1.json'
 if a.verify:assert json.loads(out.read_text())==d
 else:out.write_text(json.dumps(d,indent=2)+'\n')
 print(json.dumps({k:v for k,v in d.items() if k!='evidence_hashes'},indent=2))
