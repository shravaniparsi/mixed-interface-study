#!/usr/bin/env python3
"""Derive a fixed development input schedule without executing any input."""
import copy,hashlib,json,pathlib,sys
root=pathlib.Path(__file__).resolve().parents[2]
source=root/'development/redesign-gomodel-ordinary-v2/input.json'
form_path=root/'results/redesign-gomodel-ordinary-v2/checkpoint-form.json'
x=json.loads(source.read_text());form=json.loads(form_path.read_text())
def pointer(control):
 key=control['id']
 if key.startswith('guardrail-field-'):return '/config/'+key.removeprefix('guardrail-field-')
 return {'guardrail-description':'/description','guardrail-user-path':'/user_path'}.get(key)
rows=[]
for c in form:
 p=pointer(c);eligible=not c['disabled'] and c['type'] in ['text','textarea'] and p is not None
 rows.append({'control_id':c['id'],'json_pointer':p,'eligible':eligible,'reason':'independent editable scalar text' if eligible else 'disabled identity/type or non-text control','ordinary_value':c['value']})
eligible=sorted([r for r in rows if r['eligible']],key=lambda r:r['json_pointer'].encode('utf-8'))
assert len(eligible)==8
selected=eligible[:4]
body={k:x[k] for k in ['type','description','user_path','config']};body['name']='study-api-scheduled'
edits={'/config/request_remove':'X-Study-Remove-Edited','/config/request_set':'X-Study-Request: edited'}
producers=[{'id':'ordinary','body':body}];branches=[]
for target in selected:
 p=target['json_pointer'];other=next(r for r in eligible if r['json_pointer']!=p);assert other['json_pointer'] in edits
 for variant in ['omission','null']:
  v=copy.deepcopy(body);parts=p.lstrip('/').split('/');parent=v
  for key in parts[:-1]:parent=parent[key]
  if variant=='omission':del parent[parts[-1]]
  else:parent[parts[-1]]=None
  case_id=p.lstrip('/').replace('/','-')+'-'+variant
  producers.append({'id':case_id,'target':p,'variant':variant,'body':v})
  branches.append({'producer_id':case_id,'target':p,'repair_control':target['control_id'],'repair_value':target['ordinary_value'],'unrelated_pointer':other['json_pointer'],'unrelated_control':other['control_id'],'unrelated_value':edits[other['json_pointer']],'branch_order':['sham','repair']})
 branches.append({'producer_id':'ordinary','target':p,'repair_control':target['control_id'],'repair_value':target['ordinary_value'],'unrelated_pointer':other['json_pointer'],'unrelated_control':other['control_id'],'unrelated_value':edits[other['json_pointer']],'branch_order':['sham','repair']})
out={'status':'literal_schedule_only_not_execution_authorization','development_only':True,'scientific_cases_executed':0,'source_sha256':{str(p.relative_to(root)):hashlib.sha256(p.read_bytes()).hexdigest() for p in [source,form_path]},'inventory':rows,'ordered_eligible':[r['json_pointer'] for r in eligible],'selected_targets':[r['json_pointer'] for r in selected],'producers':producers,'branch_pairs':branches,'counts':{'projects':1,'workflows':1,'producer_payloads':9,'altered_payloads':8,'branch_pairs_if_all_accepted':12,'branches_if_all_accepted':24},'scope':'Correlated development observations; neither independent defects nor evaluation samples.'}
target=root/'development/redesign-gomodel-inputs-v1/schedule.json'
text=json.dumps(out,indent=2)+'\n'
if '--verify' in sys.argv:assert target.read_text()==text
else:target.write_text(text)
print(json.dumps(out['counts']))
