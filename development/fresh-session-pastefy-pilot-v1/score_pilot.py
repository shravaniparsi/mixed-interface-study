"""Independent complete-schedule development-pilot classification, including null results."""
import json,pathlib,sys
from outcomes import producer,continuation,accepted
from state_frame import check_intervention
from score_controls import score as score_controls,ROOT
from source_check import require

def score(base):
 base=pathlib.Path(base);read=lambda name:json.loads((base/name).read_text());run=read('pilot.json')
 cases=json.loads((ROOT/'manifests/fresh-session-pastefy-pilot-inputs-v1.json').read_text())['cases']
 require(run['status']=='schedule_finished_requires_independent_score' and [r['id'] for r in run['cases']]==[c['id'] for c in cases],'complete_fixed_pilot_schedule')
 ordinary=score_controls(base,{**run,'cases':run['cases'][:2]});results=[]
 for case,record in zip(cases,run['cases']):
  require(record['jvm_stopped'] and record['database_stopped'],'all_case_processes_stopped')
  result=dict(id=case['id'],mutation=case['mutation'],target=case['target'],S=case['schema_prediction'],branches=[],D=dict(prediction='unknown',qualified=False))
  if 'producer' in record:require(record['producer']['method']=='POST' and record['producer']['path']=='/api/v2/paste' and record['producer']['request']==case['input'],'frozen_producer_request')
  if not all(k in record for k in ['producer_before','produced']):result['H']=dict(outcome='unavailable',qualified=False);results.append(result);continue
  before,produced=read(record['producer_before']),read(record['produced']);result['H']=producer(case,record,before,produced)
  actor=record['actor'];owner=actor['user_id'];key=record.get('key');identity=record.get('identity',{})
  actor_ok=identity.get('status')==200 and identity.get('body',{}).get('logged_in') is True and identity['body'].get('id')==owner
  result['H']['qualified']=result['H']['qualified'] and actor_ok
  expected_actor=dict(user_id=owner,role='USER',key_sha256=actor['key_sha256'])
  if 'probe' in record and 'probe_before' in record and 'probe_after' in record:
   probe=read(record['probe']);unchanged=read(record['probe_before'])==produced==read(record['probe_after']);writes=probe.get('writes',[])
   guarded=all(w.get('disposition')=='aborted_before_forwarding' for w in writes)
   valid=unchanged and guarded and probe.get('actor')==expected_actor
   prediction=probe.get('prediction','unknown')
   if prediction=='native_request_emitted':
    valid=valid and len(writes)==1 and writes[0]['method']=='PUT' and writes[0]['origin']=='http://127.0.0.1:1337' and writes[0]['path']=='/api/v2/paste/'+key and json.loads(writes[0]['request'])==probe['request']
   elif prediction=='client_blocks_submission':valid=valid and not writes and not probe.get('pageErrors') and (probe.get('control',{}).get('disabled') is True or probe.get('control',{}).get('invalid',0)>0)
   else:valid=False
   result['D']=dict(prediction=prediction,qualified=bool(valid),persistent_state_unchanged=unchanged)
  for branch in record['branches']:
   arm=branch['arm'];require(arm in ['sham','repair'],'registered_arm');b=dict(arm=arm,intervention_qualified=False,continuation=dict(outcome='unavailable',available=False))
   try:
    pre=read(branch['before']);intervened=read(branch['intervened']);receipt=branch['intervention'];require(receipt['method']=='PUT' and receipt['path']=='/api/v2/paste/'+key and receipt['request']==case[arm],'frozen_intervention')
    intervention=check_intervention(pre,intervened,key,owner,case['target'],cases[0]['input'][case['target']],arm)
    b['intervention']=intervention;b['restored_producer_state']=pre==produced;b['intervention_qualified']=bool(pre==produced and accepted(receipt) and intervention['causal_branch_qualified'])
    native=read(branch['browser']);after=read(branch['after']);b['continuation']=continuation(intervened,after,native,key,owner,case['continuation'],branch['readback'])
    if native.get('actor')!=expected_actor:b['continuation']=dict(outcome='unavailable_actor_not_verified',available=False)
   except (KeyError,ValueError,TypeError,FileNotFoundError) as error:b['diagnostic']=str(error)
   result['branches'].append(b)
  eligible=result['H']['qualified'] and [b['arm'] for b in result['branches']]==['sham','repair'] and all(b['intervention_qualified'] and b['continuation']['available'] for b in result['branches'])
  result['paired_comparison_qualified']=bool(eligible)
  result['repair_restores_exact_edit']=bool(result['branches'][0]['continuation']['outcome']!='exact_intended_edit' and result['branches'][1]['continuation']['outcome']=='exact_intended_edit') if eligible else None
  results.append(result)
 return dict(status='fixed_development_pilot_classified',ordinary_gate=ordinary,cases=results,scheduled_cases=6,altered_cases=4,application_workflows=1,independent_research_cases=0,scope='Development-exposed generated stress inputs. Comparator targets differ; no pooled accuracy or product-defect claim. Unknown execution is not evidence of incompatibility.')
if __name__=='__main__':
 result=score(sys.argv[1]);pathlib.Path(sys.argv[2]).write_text(json.dumps(result,indent=2)+'\n');print(json.dumps(dict(status=result['status'],cases=len(result['cases']))))
