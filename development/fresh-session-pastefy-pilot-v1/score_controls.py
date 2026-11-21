"""Independent gate for complete ordinary paired-control evidence; never scores altered cases."""
import json,pathlib,sys
from state_frame import frame,check_intervention,no_probe_effect
from score_create import score_create,score_files
from source_check import require
ROOT=pathlib.Path(__file__).resolve().parents[2]
def score(base):
 base=pathlib.Path(base);read=lambda name:json.loads((base/name).read_text());run=read('controls.json')
 schedule=json.loads((ROOT/'manifests/fresh-session-pastefy-pilot-inputs-v1.json').read_text())['cases'][:2]
 require(run['status']=='schedule_finished_requires_independent_score','complete_control_schedule')
 require([c['id'] for c in run['cases']]==[s['id'] for s in schedule],'complete_ordered_control_pairs')
 require({x['ifname'] for x in run['network']['interfaces']}=={'lo'} and not run['network']['routes'],'isolated_network')
 def success(receipt,method,path):
  require(receipt['method']==method and receipt['path']==path and receipt['status']==200,'expected_api_transport')
  require(isinstance(receipt['body'],dict) and receipt['body'].get('success') is True,'api_success')
 def identity(actor,expected):require(actor==dict(user_id=expected['user_id'],role='USER',key_sha256=expected['key_sha256']),'same_native_actor')
 def readback(receipt,key,owner,expected):
  require(receipt['method']=='GET' and receipt['path']=='/api/v2/paste/'+key and receipt['status']==200,'readback_transport')
  body=receipt['body'];require(body.get('exists') is True and body.get('id')==key and body.get('user_id')==owner,'readback_identity')
  require(all(body.get(f)==v for f,v in expected.items()),'readback_fields')
 results=[]
 for case,record in zip(schedule,run['cases']):
  require(case['mutation']=='ordinary' and record['status']=='executed_requires_score' and record['jvm_stopped'] and record['database_stopped'],'ordinary_control_complete_and_stopped')
  key=record['key'];owner=record['actor']['user_id'];ordinary=case['input'];before=read(record['producer_before']);produced=read(record['produced'])
  require(record['identity']['status']==200 and record['identity']['body'].get('id')==owner and record['identity']['body'].get('logged_in') is True,'api_same_actor')
  success(record['producer'],'POST','/api/v2/paste');require(record['producer']['request']==ordinary and record['producer']['body']['paste']['id']==key,'exact_producer_input_and_key')
  score_create(before['database'],produced['database'],key,owner,ordinary['title'],ordinary['content']);score_files(before['files'],produced['files']);readback(record['producer_readback'],key,owner,{f:ordinary[f] for f in ['title','content']})
  require(read(record['probe_before'])==produced,'probe_restored_producer_state');no_probe_effect(read(record['probe_before']),read(record['probe_after']))
  probe=read(record['probe']);identity(probe['actor'],record['actor']);require(probe['prediction']=='native_request_emitted','ordinary_probe_emits')
  writes=probe['writes'];require(len(writes)==1 and writes[0]['method']=='PUT' and writes[0]['origin']=='http://127.0.0.1:1337' and writes[0]['path']=='/api/v2/paste/'+key and writes[0]['disposition']=='aborted_before_forwarding','one_blocked_probe_write')
  expected={**ordinary,case['continuation']['field']:case['continuation']['value']};require(probe['request']==expected and json.loads(writes[0]['request'])==expected,'exact_original_probe_serialization')
  require([b['arm'] for b in record['branches']]==['sham','repair'],'complete_ordered_intervention_pair')
  for b in record['branches']:
   require(b['status']=='executed_requires_score' and read(b['before'])==produced,'branch_completed_from_same_state');success(b['intervention'],'PUT','/api/v2/paste/'+key);require(b['intervention']['request']==case[b['arm']],'fixed_intervention')
   intervened=read(b['intervened']);intervention=check_intervention(produced,intervened,key,owner,case['target'],ordinary[case['target']],b['arm']);require(intervention['causal_branch_qualified'],'exact_intervention_frame')
   readback(b['intervention_readback'],key,owner,{f:ordinary[f] for f in ['title','content']})
   native=read(b['browser']);require(native['status']=='native_action_completed','native_completion');identity(native['actor'],record['actor'])
   nw=[r for r in native['receipts'] if r['method'] not in ['GET','HEAD','OPTIONS']];require(len(nw)==1 and nw[0]['method']=='PUT' and nw[0]['path']=='/api/v2/paste/'+key and nw[0]['status']==200 and json.loads(nw[0]['body']).get('success') is True,'one_successful_native_write');require(json.loads(nw[0]['request'])==expected,'probe_matches_actual_native_serialization')
   result=frame(intervened,read(b['after']),key,owner,{case['continuation']['field']:case['continuation']['value']});require(result['status']=='exact_expected_write','exact_native_continuation_frame');readback(b['readback'],key,owner,{f:expected[f] for f in ['title','content']})
  results.append(dict(id=case['id'],probe_no_effect=True,sham_passed=True,repair_passed=True))
 return dict(status='ordinary_paired_controls_verified',controls=results,altered_inputs_executed=0,independent_research_cases=0)
if __name__=='__main__':
 result=score(sys.argv[1]);pathlib.Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
