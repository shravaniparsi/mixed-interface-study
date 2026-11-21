"""Independent feasibility scoring from PostgreSQL observations, not UI success flags."""
import collections,copy,datetime,hashlib,json,pathlib
from urllib.parse import urlsplit
from source_check import require

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)
def digest(value):return hashlib.sha256(canonical(value).encode()).hexdigest()
def timestamp(value):
 require(isinstance(value,str),'timestamp_string')
 parsed=datetime.datetime.fromisoformat(value.replace('Z','+00:00'))
 require(parsed.tzinfo is not None,'timestamp_timezone')
 return parsed

def state(value):
 require(set(value)=={'metadata','tables','sequences','files'},'complete_state_sections')
 require(isinstance(value['metadata'],dict) and isinstance(value['tables'],dict) and isinstance(value['sequences'],dict) and isinstance(value['files'],list),'state_types')
 for name,table in value['tables'].items():
  require(set(table)=={'rows','row_sha256'},'table_sections',table=name)
  require(table['row_sha256']==[digest(row) for row in table['rows']],'row_digest',table=name)
 require('public.Url' in value['tables'] and 'public.UserSession' in value['tables'],'required_tables')
 require(len({f['path'] for f in value['files']})==len(value['files']),'unique_files')
 return value

def logical(value):
 value=copy.deepcopy(state(value))
 for table in value['tables'].values():
  table['rows']=sorted(table['rows'],key=canonical);del table['row_sha256']
 value['files']=sorted(value['files'],key=canonical)
 return value

def row(value,table,identity):
 matches=[r for r in value['tables'][table]['rows'] if r.get('id')==identity]
 require(len(matches)==1,'unique_record',table=table,identity=identity)
 return matches[0]
def put(value,pointer,replacement):
 parts=pointer.split('/')[1:];require(bool(parts),'nonempty_pointer')
 for part in parts[:-1]:value=value[int(part)] if isinstance(value,list) else value[part]
 key=int(parts[-1]) if isinstance(value,list) else parts[-1]
 require(isinstance(value,list) or key in value,'existing_target_field');value[key]=replacement

def creation(before,after,identity,actor,ordinary):
 b,a=logical(before),logical(after);created=row(a,'public.Url',identity)
 require(not any(r['id']==identity for r in b['tables']['public.Url']['rows']),'new_record_id')
 require(created['userId']==actor,'record_actor')
 for key,value in ordinary.items():require(created[key]==value,'created_ordinary_value',field=key)
 a['tables']['public.Url']['rows'].remove(created)
 require(a==b,'creation_unrelated_state')
 return created

def authentication(before,after,actor,previous_session_ids):
 b,a=logical(before),logical(after);old=b['tables']['public.UserSession']['rows'];new=a['tables']['public.UserSession']['rows']
 additions=[r for r in new if r not in old];require(len(additions)==1 and len(new)==len(old)+1,'one_session_insert')
 session=additions[0]
 require(set(session)=={'id','createdAt','ua','client','device','oauthProvider','oidcIdToken','userId'},'session_columns')
 require(isinstance(session['id'],str) and len(session['id'])==32 and session['id'] not in previous_session_ids,'fresh_session_id')
 require(session['userId']==actor and session['oauthProvider'] is None and session['oidcIdToken'] is None,'local_same_actor_session')
 require(all(isinstance(session[k],str) and session[k] for k in ['ua','client','device']),'session_client_identity')
 timestamp(session['createdAt']);a['tables']['public.UserSession']['rows'].remove(session)
 require(a==b,'authentication_unrelated_state');return session['id']

def edit(before,after,identity,changes,request):
 b,a=logical(before),logical(after);old=row(b,'public.Url',identity);new=row(a,'public.Url',identity)
 require(request['method']=='PATCH' and request['path']=='/api/user/urls/'+identity,'exact_edit_request')
 require(isinstance(request['body'],dict),'request_body_object')
 require(timestamp(new['updatedAt'])>=timestamp(old['updatedAt']),'edit_timestamp_order')
 for pointer,value in changes.items():
  put(old,pointer,value)
  body=request['body']
  for part in pointer.split('/')[1:]:body=body[int(part)] if isinstance(body,list) else body[part]
  require(body==value,'request_expected_field',pointer=pointer)
 new['updatedAt']=old['updatedAt']
 require(a==b,'edit_unrelated_state')
 return True


def readback_record(persisted,observed):
 # Source: original GET uses IS NOT NULL for password; Drizzle serializes timestamps.
 projected={**persisted,'password':persisted.get('password') is not None}
 require(set(observed)==set(projected),'complete_api_readback_fields')
 for key,value in observed.items():
  expected=projected[key]
  matches=timestamp(expected)==timestamp(value) if key in {'createdAt','updatedAt'} else expected==value
  require(matches,'readback_matches_database',field=key)

def score(root,matrix):
 root=pathlib.Path(root)
 def load(name):
  require(pathlib.PurePosixPath(name).name==name,'evidence_basename')
  p=root/name;require(p.is_file() and not p.is_symlink() and p.stat().st_size<=8*1024**2,'evidence_file',file=name)
  return json.loads(p.read_text())
 result=load('result.json');require(result['status']=='controls_completed' and result['cleanup_complete'] is True,'runner_complete')
 plan=next(s for s in matrix['systems'] if s['id']=='zipline');actual=load('branches.json')
 require([b['id'] for b in actual]==[b['id'] for b in plan['branches']],'exact_branch_schedule')
 initial=load('root-state.json');identity=result['record_id'];actor=result['actor_id'];row(initial,'public.Url',identity)
 native=load('native-create-response.json');require(200<=native['status']<300,'native_creation_response')
 creation(load('native-before.json'),load('native-after.json'),native['record']['id'],actor,plan['native'])
 creation(load('api-before.json'),load('api-after.json'),identity,actor,plan['api'])
 require(load('api-create-response.json')['id']==identity,'api_creation_identity')
 require(logical(initial)==logical(load('api-after.json'))==logical(load('root-backup-verified.json')),'checkpoint_verified')
 trace=load('trace.json');require(not any(r['channel'] in ['pageerror','requestfailed'] for r in trace),'browser_execution_integrity')
 captures=load('response-capture.json');require(bool(captures) and all(r['capture']['status']=='complete' for r in captures),'complete_response_capture')
 def verify_edit(label,before,changes):
  request=load(label+'-request.json');response=load(label+'-response.json');writes=load(label+'-writes.json')
  require(200<=response['status']<300,'native_edit_response')
  recorded=[dict(method=r['method'],path=urlsplit(r['url']).path,body=json.loads(r['body'])) for r in trace if r.get('phase')==label and r['channel']=='browser-request' and r['method'] not in ['GET','HEAD','OPTIONS']]
  require(recorded==writes==[request],'single_native_write')
  after=load(label+'-after.json');edit(before,after,identity,changes,request)
  readback=load(label+'-api-readback.json');require(isinstance(readback,list),'readback_list')
  matches=[r for r in readback if r['id']==identity];require(len(matches)==1,'api_readback_identity')
  persisted=row(after,'public.Url',identity)
  readback_record(persisted,matches[0])
  return after
 session_ids={r['id'] for r in initial['tables']['public.UserSession']['rows']}
 cycles=load('control-cycles.json');require([c['field'] for c in cycles]==[f['pointer'] for f in plan['fields']],'all_field_reset_cycles')
 for i,(cycle,field) in enumerate(zip(cycles,plan['fields'])):
  label='cycle-'+str(i);require(cycle['label']==label and cycle['context_initial']=={'cookies':[],'origins':[]},'fresh_cycle')
  restored=load(label+'-restored.json');require(logical(restored)==logical(initial),'cycle_root_restored')
  loaded=load(label+'-loaded.json');sid=authentication(restored,loaded,actor,session_ids);session_ids.add(sid)
  require(cycle['browser_actor']==cycle['api_actor']=={'id':actor,'role':result['actor_role']},'cycle_actor')
  require(logical(loaded)==logical(load(label+'-before.json')),'cycle_start_unchanged')
  replaced=verify_edit(label+'-replace',loaded,{field['pointer']:field['replacement']})
  reset_before=load(label+'-reset-before.json');require(logical(replaced)==logical(reset_before),'reset_start_unchanged')
  verify_edit(label+'-reset',reset_before,{field['pointer']:field['ordinary']})
 for planned,observed in zip(plan['branches'],actual):
  label=planned['id'];require(observed['context_initial']=={'cookies':[],'origins':[]},'empty_context')
  restored=load(label+'-restored.json');require(logical(restored)==logical(initial),'root_restored')
  loaded=load(label+'-loaded.json');sid=authentication(restored,loaded,actor,session_ids);session_ids.add(sid)
  require(observed['browser_actor']==observed['api_actor']=={'id':actor,'role':result['actor_role']},'actor_privileges')
  other=next(f for f in plan['fields'] if f['pointer']==planned['unrelated']);changes={other['pointer']:other['replacement']}
  target=next(f for f in plan['fields'] if f['pointer']==planned['target'])
  expected_actions=([{ 'pointer':target['pointer'],'value':target['ordinary']}] if planned['arm']=='noop_repair' else [])+[{'pointer':other['pointer'],'value':other['replacement']}]
  require(load(label+'-actions.json')==expected_actions,'planned_native_actions')
  verify_edit(label,loaded,changes)
 return dict(status='ordinary_controls_verified',branches=len(actual),field_reset_cycles=len(cycles),independent_evaluation_cases=0,scope='ordinary execution evidence; deployment/runtime/source gates remain separate')

if __name__=='__main__':
 import sys
 result=score(sys.argv[1],json.loads(pathlib.Path(sys.argv[2]).read_text()))
 pathlib.Path(sys.argv[3]).write_text(json.dumps(result,indent=2)+'\n')
 print(json.dumps(result))
