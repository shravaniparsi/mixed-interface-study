#!/usr/bin/env python3
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RUN=44212825790

def build():
 rows=[]
 for arm in ['ui-ui','api-ui','api-api']:
  archive=ROOT/f'results/reserved-kanban-control-v1-{arm}-ci-{RUN}'
  def read(n):return json.loads((archive/n).read_text())
  run=read('github-run.json');assert run['id']==RUN and run['head_sha'].startswith('be80d8f') and run['status']=='completed'
  runtime=read('runtime.json') if (archive/'runtime.json').exists() else {'status':'setup_not_reached'}
  row={'arm':arm,'status':runtime['status'],'elapsed_seconds':runtime.get('elapsed_seconds'),'runtime_error':runtime.get('error')}
  if (archive/'control.json').exists():
   c=read('control.json');assert c['arm']==arm and c['independent_evaluation_cases']==0
   row.update(control_status=c['status'],stages=c['stages'],error=c.get('error'),request_failures=c['request_failures'],page_errors=c['page_errors'])
   assert all(n<=1 for n in c['write_counts'].values())
   if c['status']=='qualified':
    assert runtime['status']=='qualified' and runtime['browser_exit']==0
    assert read('network.json')[0]['Internal'] is True
    assert c['write_counts']=={'board':1,'create':1,'update':1}
    assert c['producer']['body']=={'title':'Study task','description':'Study description','color':'#feff9c','status':'TODO'}
    assert all(200<=c[n]['status']<300 for n in ['board_producer','producer','consumer'])
    assert c['consumer']['body']==dict(c['after_create'],title='Edited task',status='TODO')
    assert c['after_edit']==c['consumer']['body']
    assert c['after_create']['id']==c['after_edit']['id']
  row['evidence_hashes']={str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(archive.iterdir()) if p.is_file()};rows.append(row)
 return {'kind':'closed_ordinary_kanban_controls','run_id':RUN,'rows':rows,'all_qualified':all(r['status']=='qualified' for r in rows),'independent_evaluation_cases':0}
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args();d=build();out=ROOT/'manifests/reserved-kanban-controls-v1.json'
 if a.verify:assert json.loads(out.read_text())==d
 else:out.write_text(json.dumps(d,indent=2)+'\n')
 print(json.dumps({'all_qualified':d['all_qualified'],'rows':[{k:v for k,v in r.items() if k!='evidence_hashes'} for r in d['rows']]},indent=2))
