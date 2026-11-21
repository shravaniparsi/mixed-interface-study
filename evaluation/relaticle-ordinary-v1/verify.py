import json,pathlib,sys
p=pathlib.Path(sys.argv[1]);r=json.loads((p/'result.json').read_text());b=json.loads((p/'browser-result.json').read_text());assert r['status']=='ordinary_role1_passed' and b['status']=='ordinary_role1_passed'
def rows(label,table):
 t=json.loads((p/(label+'.json')).read_text())['tables'][table];cols=([t['rowid_alias']] if t['rowid_alias'] else [])+[c[1] for c in t['columns'] if c[6]!=1];assert t['rows'] is not None;assert all(len(row)==len(cols) for row in t['rows']);return [dict(zip(cols,[v['value'] for v in row])) for row in t['rows']]
create=json.loads((p/'api-create.json').read_text());read=json.loads((p/'api-readback.json').read_text());assert create['status']==201 and read['status']==200;api_id=create['body']['data']['id'];assert read['body']['data']['id']==api_id
native_rows=rows('after-native-create','notes');old=rows('before-native-create','notes');fresh=[n for n in native_rows if n['id'] not in {v['id'] for v in old}];assert len(fresh)==1;native_id=fresh[0]['id'];assert native_id!=api_id
for role,nid in [('native',native_id),('api',api_id)]:
 for label,title,body in [(('after-native-create' if role=='native' else 'after-api-create'),'Study title','<p>Study body</p>'),(role+'_title_edit','Study edited title','<p>Study body</p>'),(role+'_body_edit','Study edited title','<p>Study edited body</p>')]:
  n=[n for n in rows(label,'notes') if n['id']==nid];assert len(n)==1 and n[0]['title']==title;assert n[0]['creator_id']==b['actor']['user_id'] and n[0]['workspace_id']==b['actor']['workspace_id'];field_ids={v['id'] for v in rows(label,'custom_fields') if v['code']=='body'};v=[v for v in rows(label,'custom_field_values') if v['entity_id']==nid and v['custom_field_id'] in field_ids];assert len(v)==1 and v[0]['text_value']==body
assert r['elapsed_seconds']<=600
result=dict(status='ordinary_role1_evidence_verified',native_id=native_id,api_id=api_id,scientific_cases=0,scope='same-actor ordinary create/readback and two native text edits; not full restoration qualification');(p/'verification.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
