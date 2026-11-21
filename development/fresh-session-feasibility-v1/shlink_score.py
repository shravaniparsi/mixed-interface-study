"""Independent complete ordinary-schedule scoring; deployment gates remain separate."""
import json,pathlib
from urllib.parse import urlsplit
from source_check import require
from shlink_database_score import creation,edit,locate,normalized,ordinary_record,records
from shlink_files import compare_non_database
from shlink_redis import logical as redis_logical
from shlink_metadata_cache import compare as compare_cache,metadata

def non_database(before,after,allow_metadata_additions=False,cache_mode='exact'):
 require(set(before)==set(after)=={'database','filesystem','redis'},'complete_cross_store_observation')
 compare_non_database(before['filesystem'],after['filesystem'],allow_metadata_additions)
 compare_cache(before['redis'],after['redis'],'add_metadata' if allow_metadata_additions else cache_mode)
def unchanged(before,after,cache_mode='exact'):
 non_database(before,after,cache_mode=cache_mode);require(normalized(before['database'])==normalized(after['database']),'database_unchanged')
def actor(state,identity,fingerprint):
 rows=records(state['database'],'api_keys');matches=[r for r in rows if r['id']==identity]
 require(len(matches)==1,'unique_actor');key=matches[0]
 require(key['key']==fingerprint and key['enabled']==1 and key['expiration_date'] is None,'persistent_key_and_validity')
 require(not any(r['api_key_id']==identity for r in records(state['database'],'api_key_roles')),'unrestricted_same_actor')
def readback(state,identity,value):
 _,record=locate(state['database'],identity)
 for field,column in [('shortCode','short_code'),('longUrl','original_url'),('title','title'),('domain','domain_id')]:require(value[field]==record[column],'api_readback_field',field=field)
 require(value['tags']==[],'api_readback_tags')

def score(root,matrix):
 root=pathlib.Path(root);metadata_values={}
 def load(name):
  require(pathlib.PurePosixPath(name).name==name,'evidence_basename');p=root/(name+'.json')
  require(p.is_file() and not p.is_symlink() and p.stat().st_size<=16*1024**2,'evidence_file',name=name)
  value=json.loads(p.read_text())
  if isinstance(value,dict) and 'redis' in value:
   for row in value['redis']['entries']:
    if metadata(row):
     require(row['key'] not in metadata_values or metadata_values[row['key']]==row['value'],'metadata_content_stable_across_all_snapshots')
     metadata_values[row['key']]=row['value']
  return value
 result=load('result');require(result['status']=='controls_completed' and result['cleanup_complete'] is True,'completed_and_cleaned')
 plan=next(s for s in matrix['systems'] if s['id']=='shlink');identity=result['record_id'];key_id=result['actor_id'];fingerprint=result['api_key_sha256'];root_state=load('root-state')
 require(load('actor-key')['sha256']==fingerprint,'key_fingerprint');actor(root_state,key_id,fingerprint);ordinary_record(root_state['database'],identity,key_id,plan['api'])
 require(locate(root_state['database'],identity)[1]['short_code']==result['short_code'],'stable_short_code')
 api_trace=load('api-trace');require(bool(api_trace) and all(r['api_key_sha256']==fingerprint and 200<=r['status']<300 for r in api_trace),'api_trace_identity_and_success')
 def context(prefix):
  require(load(prefix+'-initial-context')=={'cookies':[],'origins':[]},'fresh_browser_context')
  require(load(prefix+'-browser-errors')==[],'no_browser_errors')
  require(load(prefix+'-selected-server')['api_key_sha256']==fingerprint,'native_server_key')
  captures=load(prefix+'-response-capture');require(bool(captures) and all(c['capture']['status']=='complete' for c in captures),'complete_native_capture')
  trace=load(prefix+'-browser-trace')
  for row in trace:
   if row['kind']=='request' and urlsplit(row['url']).path.startswith('/rest/v3/'):
    require(row['api_key_sha256']==fingerprint,'native_request_actor')
  return trace
 def operation(prefix,label,changes,method='PATCH',expected_form=None):
  trace=context(prefix);control=load(prefix+'-'+label+'-control');request=load(prefix+'-'+label+'-request');response=load(prefix+'-'+label+'-response')
  expected_actions=[dict(pointer=p,value=v) for p,v in changes.items()]
  require(control['label']==label and control['actions']==expected_actions,'exact_native_actions')
  fills=[{k:r[k] for k in ['pointer','value']} for r in trace if r.get('phase')==label and r['kind']=='native_fill']
  require(fills==expected_actions,'native_control_trace')
  if expected_form is not None:require(control['form_before']==expected_form,'native_hydration')
  require(control['request']==request and control['response_status']==response['status'] and 200<=response['status']<300,'native_response_consistency')
  require(request['method']==method and request['query']=='','native_method_and_domain')
  writes=[]
  for r in trace:
   if r.get('phase')==label and r['kind']=='request' and r['method'] not in ['GET','HEAD','OPTIONS']:
    u=urlsplit(r['url']);writes.append(dict(method=r['method'],path=u.path,query=('?'+u.query if u.query else ''),body=json.loads(r['body'])))
  require(writes==load(prefix+'-'+label+'-writes')==[request],'exactly_one_native_write')
  sent=[r for r in trace if r.get('phase')==label and r['kind']=='request' and r['method']==method]
  require(len(sent)==1,'single_observed_mutation')
  captured=[r for r in load(prefix+'-response-capture') if r.get('id')==sent[0]['id'] and r.get('phase')==label]
  require(len(captured)==1 and captured[0]['status']==response['status'] and captured[0]['capture']['body']==response['text'],'native_response_capture_binding')
  return request
 def bound_readback(label,filename,state,record_id):
  value=load(filename);readback(state,record_id,value)
  rows=[r for r in api_trace if r['label']==label]
  short_code=locate(state['database'],record_id)[1]['short_code']
  require(len(rows)==1 and rows[0]['method']=='GET' and rows[0]['path']=='/rest/v3/short-urls/'+short_code and json.loads(rows[0]['response'])==value,'api_readback_trace_binding')
 native_request=operation('native','create',{'/longUrl':plan['native']['longUrl'],'/title':plan['native']['title']},'POST',{'longUrl':'','title':''})
 require(native_request['path']=='/rest/v3/short-urls','native_create_route')
 for key in ['longUrl','title']:require(native_request['body'][key]==plan['native'][key],'native_create_value')
 for label,record_id,body in [('native',result['native_record_id'],plan['native']),('api',identity,plan['api'])]:
  before,after=load(label+'-before'),load(label+'-after');creation(before['database'],after['database'],record_id,key_id,body);non_database(before,after,True);actor(after,key_id,fingerprint)
 require(result['native_record_id']!=identity,'distinct_native_and_api_records')
 bound_readback('native-readback','native-api-readback',load('native-after'),result['native_record_id']);bound_readback('api-created-readback','api-created-readback',load('api-after'),identity)
 creates=[r for r in api_trace if r['method']=='POST'];require(len(creates)==1 and creates[0]['label']=='api-create' and creates[0]['path']=='/rest/v3/short-urls' and creates[0]['body']==plan['api'],'one_original_api_creation')
 require(json.loads(creates[0]['response'])==load('api-create-response'),'api_creation_response_binding');readback(load('api-after'),identity,load('api-create-response'))
 unchanged(load('api-after'),root_state)
 def start(prefix):
  restored=load(prefix+'-restored');loaded=load(prefix+'-loaded');unchanged(root_state,restored);unchanged(root_state,loaded,cache_mode='restart_metadata');actor(loaded,key_id,fingerprint);return loaded
 def edited(prefix,label,before,changes,action_changes=None):
  prior=locate(before['database'],identity)[1]
  request=operation(prefix,label,action_changes if action_changes is not None else changes,expected_form={'longUrl':prior['original_url'],'title':prior['title']});after=load(label+'-after')
  edit(before['database'],after['database'],identity,key_id,changes,request);non_database(before,after,True);bound_readback(label+'-readback',label+'-api-readback',after,identity);return after
 cycles=load('control-cycles');require(cycles==[dict(label='cycle-'+str(i),field=f['pointer']) for i,f in enumerate(plan['fields'])],'complete_reset_schedule')
 for i,field in enumerate(plan['fields']):
  prefix='cycle-'+str(i);loaded=start(prefix);replaced=edited(prefix,prefix+'-replace',loaded,{field['pointer']:field['replacement']});reset_before=load(prefix+'-reset-before');unchanged(replaced,reset_before);edited(prefix,prefix+'-reset',reset_before,{field['pointer']:field['ordinary']})
 branches=load('branches');require(branches==[{'id':b['id']} for b in plan['branches']],'complete_branch_schedule')
 for branch in plan['branches']:
  label=branch['id'];loaded=start(label);target=next(f for f in plan['fields'] if f['pointer']==branch['target']);other=next(f for f in plan['fields'] if f['pointer']==branch['unrelated'])
  changes={other['pointer']:other['replacement']};actions={**({target['pointer']:target['ordinary']} if branch['arm']=='noop_repair' else {}),**changes}
  edited(label,label,loaded,changes,actions)
 return dict(status='ordinary_controls_verified',branches=len(branches),field_reset_cycles=len(cycles),independent_evaluation_cases=0,scope='schedule and cross-store evidence only; runtime/worker/network/dependency gates separate')
if __name__=='__main__':
 import sys
 result=score(sys.argv[1],json.loads(pathlib.Path(sys.argv[2]).read_text()));pathlib.Path(sys.argv[3]).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
