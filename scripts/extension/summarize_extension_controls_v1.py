#!/usr/bin/env python3
"""Audit fixed extension controls; mismatches remain explicit unavailable results."""
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
HEAD='1c8d6b95b18cb96326c5d268b5c0a44c7121304c'
RUNS={'booklore':44219639911,'kanban':44219643279}
ORDINARY={
 'booklore':{'oidcGroupClaim':'study-readers','isAdmin':False,'permissions':['permissionRead'],'libraryIds':[],'description':'Study description'},
 'kanban':{'title':'Study task','description':'Study description','color':'#feff9c','status':'TODO'}}
NAMES={'booklore':['study-booklore-app','study-booklore-db'],'kanban':['study-kanban-ui','kanban-app','study-kanban-db']}
def read(p):return json.loads(p.read_text())
def build(project):
 run_id=RUNS[project];archive=ROOT/f'results/extension-{project}-controls-v1-ci-{run_id}'
 run=read(archive/'github-run.json');assert run['id']==run_id and run['head_sha']==HEAD and run['status']=='completed'
 rows=[];traces=[];identities=[]
 for arm in ['ui-ui','api-ui','api-api']:
  p=archive/arm;r=read(p/'runtime.json') if (p/'runtime.json').exists() else {'status':'not_reached_or_interrupted'}
  c=read(p/'control.json') if (p/'control.json').exists() else None
  row={'arm':arm,'runtime_status':r['status'],'runtime_error':r.get('error'),'elapsed_seconds':r.get('elapsed_seconds'),'control_status':c.get('status') if c else None,'control_error':c.get('error') if c else None,'qualified':False}
  if c and c.get('status')=='qualified':
   try:
    assert r['status']=='qualified' and r['browser_exit']==0,'Runtime did not qualify'
    assert c['arm']==arm and c['independent_evaluation_cases']==0,'Trace identity mismatch'
    counts={'create':1,'update':1}
    stages=['original_local_admin_and_settings','mapping_persisted','edit_persisted']
    names=['producer','consumer']
    if project=='kanban':
     counts['board']=1;stages=['parent_persisted','task_persisted','edit_persisted'];names.insert(0,'board_producer')
     assert c['board_producer']['body']=={'title':'Study Board'} and c['board_id'] is not None,'Parent control differs'
    assert c['write_counts']==counts,'Write count mismatch'
    assert c['stages']==stages,'Stage mismatch'
    assert c['producer']['body']==ORDINARY[project],'Producer differs'
    assert all(200<=c[k]['status']<300 for k in names),'Non-successful write'
    assert c['after_create']['id'] is not None,'Missing persistent identity'
    assert all(c['after_create'][k]==v for k,v in ORDINARY[project].items()),'Ordinary readback differs'
    expected=dict(c['after_create'])
    expected.update({'description':'Edited description','permissions':['permissionRead'],'libraryIds':[]} if project=='booklore' else {'title':'Edited task','status':'TODO'})
    assert c['consumer']['body']==expected and c['after_edit']==expected,'Serializer or final state differs'
    net=read(p/'network.json')[0];assert net['Internal'] is True,'Application network not isolated'
    ids={'network':net['Id']}
    for name in NAMES[project]:ids[name]=read(p/(name+'.json'))[0]['Id']
    identities.append(ids);traces.append(c);row['qualified']=True
   except (AssertionError,KeyError,TypeError,ValueError,IndexError,FileNotFoundError) as error:
    row['verification_error']=f'{type(error).__name__}: {error}'
  rows.append(row)
 all_qualified=all(r['qualified'] for r in rows);equivalence=False;equivalence_error=None
 if all_qualified:
  try:
   assert all(len({x[k] for x in identities})==3 for k in identities[0]),'Reset identities reused'
   browser=read(archive/'browser.json');assert browser['playwright']=='1.62.1' and browser['declared']['browserVersion']=='151.0.7922.34','Browser differs'
   def normalize(x):return {k:v for k,v in x.items() if k!='id'}
   for key in ['after_create','after_edit']:
    assert all(normalize(c[key])==normalize(traces[0][key]) for c in traces),'Cross-arm '+key+' differs'
   assert all(normalize(c['consumer']['body'])==normalize(traces[0]['consumer']['body']) for c in traces),'Cross-arm update body differs'
   equivalence=True
  except (AssertionError,KeyError,TypeError,ValueError,IndexError,FileNotFoundError) as error:equivalence_error=f'{type(error).__name__}: {error}'
 return {'kind':'extension_ordinary_control_closure','project':project,'run_id':run_id,'head_sha':HEAD,'github_conclusion':run['conclusion'],'rows':rows,'all_arms_qualified':all_qualified,'cross_arm_equivalence':equivalence,'equivalence_error':equivalence_error,'qualified_for_future_variant_freeze':all_qualified and equivalence,'independent_scientific_cases':0,'interpretation':'Infrastructure extension ordinary controls only, separate from the closed original frame. No variation, defect or causal result.','evidence_hashes':{str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(archive.rglob('*')) if p.is_file()}}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--project',choices=sorted(RUNS),required=True);p.add_argument('--verify',action='store_true');a=p.parse_args();d=build(a.project)
 out=ROOT/f'manifests/extension-{a.project}-controls-v1.json'
 if a.verify:assert read(out)==d
 else:out.write_text(json.dumps(d,indent=2)+'\n')
 print(json.dumps({k:v for k,v in d.items() if k!='evidence_hashes'},indent=2))
