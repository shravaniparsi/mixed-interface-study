"""Score the fixed ordinary run from private snapshots and transport receipts."""
import json,pathlib,sys
from score_create import score_create,score_files
from score_edit import score_edit
from source_check import require
ROOT=pathlib.Path(__file__).resolve().parents[2]
def score(base):
 base=pathlib.Path(base);read=lambda name:json.loads((base/name).read_text());run=read('execution.json')
 require(run['status']=='ordinary_execution_completed_requires_independent_score' and run['jvm_stopped'] and run['database_stopped'],'complete_execution_and_shutdown')
 require(len(run['creations'])==2 and {x['arm'] for x in run['creations']}=={'native','api'},'complete_creation_schedule')
 require(len(run['branches'])==4 and {(x['arm'],x['field']) for x in run['branches']}=={(a,f) for a in ['native','api'] for f in ['title','content']},'complete_edit_schedule')
 require({x['ifname'] for x in run['network']['interfaces']}=={'lo'} and not run['network']['routes'],'isolated_network')
 owner=run['actor']['user_id'];ordinary=json.loads((ROOT/'manifests/fresh-session-pastefy-ordinary-input-v1.json').read_text())['producer'];created={}
 def browser(name,method,path):
  b=read(name);require(b['status']=='native_action_completed','native_completion');require(b['actor']['user_id']==owner and b['actor']['role']=='USER' and b['actor']['key_sha256']==run['actor']['key_sha256'],'native_same_actor')
  writes=[x for x in b['receipts'] if x['method'] not in ['GET','HEAD','OPTIONS']]
  require(len(writes)==1 and writes[0]['method']==method and writes[0]['path']==path,'one_expected_native_write');require(200<=writes[0]['status']<300 and json.loads(writes[0]['body']).get('success') is True,'native_write_success');return writes[0]
 def readback(record,key,title,content):
  require(record['status']==200 and record['method']=='GET' and record['path']=='/api/v2/paste/'+key,'readback_transport');d=record['body'];require(d['id']==key and d['title']==title and d['content']==content and d['user_id']==owner and d['exists'] is True,'readback_identity_and_values')
 for c in run['creations']:
  before,after=read(c['before']),read(c['after']);created[c['arm']]=(c,after)
  require(c['identity']['body']['id']==owner and c['identity']['body']['logged_in'] is True,'api_identity')
  if c['arm']=='native':require(json.loads(browser(c['browser'],'POST','/api/v2/paste')['request'])==ordinary,'native_original_input')
  else:require(c['api']['request']==ordinary and c['api']['body']['paste']['id']==c['key'],'api_original_input_and_key')
  score_create(before['database'],after['database'],c['key'],owner,ordinary['title'],ordinary['content']);score_files(before['files'],after['files']);readback(c['readback'],c['key'],ordinary['title'],ordinary['content'])
 require(read(run['creations'][0]['before'])==read(run['creations'][1]['before']),'same_initial_producer_state')
 expected={'title':'study-note-edited','content':'Disposable revised study text.'}
 for b in run['branches']:
  c,root=created[b['arm']];before,after=read(b['before']),read(b['after']);require(before==root and b['key']==c['key'],'restored_creation_state');require(b['value']==expected[b['field']],'registered_ordinary_edit')
  browser(b['browser'],'PUT','/api/v2/paste/'+b['key']);score_edit(before['database'],after['database'],b['key'],owner,b['field'],b['value']);score_files(before['files'],after['files'])
  values={'title':ordinary['title'],'content':ordinary['content']};values[b['field']]=b['value'];readback(b['readback'],b['key'],**values)
 return dict(status='ordinary_private_evidence_verified',creations=2,edit_branches=4,independent_cases=0,scope='Ordinary qualification only; build provenance and public evidence transport require separate gates.')
if __name__=='__main__':
 result=score(sys.argv[1]);pathlib.Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(result))
