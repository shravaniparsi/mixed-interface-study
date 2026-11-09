#!/usr/bin/env python3
"""Independent checks of the predeclared PetClinic integrity control evidence."""
import hashlib,json
from pathlib import Path
from summarize_petclinic_oracle_components import same,digest

ROOT=Path(__file__).resolve().parents[1]
SOURCES=['scripts/petclinic_boundary_slice.mjs','scripts/petclinic_integrity.mjs','scripts/petclinic_response_capture.mjs','scripts/petclinic_cleanup.mjs','scripts/validate_petclinic_integrity.py','scripts/summarize_petclinic_oracle_components.py','scripts/ci/run_petclinic_integrity.py','scripts/ci/prepare_petclinic.py','scripts/ci/run_applications.sh','.github/workflows/applications.yml','protocol/petclinic-integrity-validation-v1.md','manifests/petclinic-candidates-v1.json','manifests/petclinic-integrity-controls-v1.json']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def read(p):return json.loads(p.read_bytes())
def require(value,message):
 if not value:raise ValueError(message)
def validate_case(r,case):
 require(r['prefix_status']==case['prefix_status'],'Unexpected prefix status')
 require(r['backend_cleanup']['confirmed'] is True,'Backend exit not confirmed')
 require(not r['page_errors'],'Native page errors')
 integrity=r['integrity'];require(integrity['version']==1,'Integrity version')
 guards=integrity['guards'];names=[g['name'] for g in guards]
 require(len(names)==len(set(names)),'Duplicate guard')
 required={'pre_candidate_state_readable','candidate_prefix_command'}
 if case['prefix_status']==201:
  required|={'loaded_target_binding','returned_target_id_valid','continuation_edit_command'}
  if r['template']!='owner_address_edit':required|={'returned_pet_owner','bound_owner_read_status','bound_owner_identity'}
  if r['template']=='visit_reschedule':required|={'returned_visit_parent','bound_pet_read_status','bound_pet_identity'}
  if r['oracle']=='fresh_ui':
   required|={'native_loaded_target','native_loaded_fields'}
   if r['template']!='owner_address_edit':required|={'native_owner_status','native_owner_binding'}
   if r['template']=='visit_reschedule':required|={'native_pet_status','native_pet_binding'}
  require(r['status']=='continuation_passed' and r['continuation_http_status']==204,'Positive continuation did not pass')
 else:
  require(r['status']=='prefix_rejected' and r['continuation_reachable'] is False,'Unexpected rejected-prefix continuation')
  require(not any(e.get('method')=='PUT' for e in r['trace']),'Write after rejected prefix')
 require(required<=set(names),'Missing required guard: '+str(required-set(names)))
 for g in guards:
  require(g['passed'] is True and same(g['expected'],g['observed']),'Failed or forged guard: '+g['name'])
  if g['name'].endswith('_command'):
   actual=g['observed'];source='ui_network' if g['name']=='continuation_edit_command' and r['oracle']=='fresh_ui' else 'direct_api'
   events=[e for e in r['trace'] if e.get('source')==source and e.get('method')==actual['method'] and e.get('path').removeprefix('/petclinic/api')==actual['path'] and same(e.get('request'),actual['payload'])]
   require(len(events)==1,'Command does not match one captured request')
 # Reconstruct intended commands and returned-resource bindings from raw evidence.
 registered=next(c for c in read(ROOT/'manifests/petclinic-candidates-v1.json')['candidates'] if c['id']==case['id'])
 direct=[e for e in r['trace'] if e.get('source')=='direct_api']
 prefix=next(e for e in direct if e['phase']=='candidate_prefix')
 setup=[e for e in direct if e['phase']=='prefix_setup' and e['method']=='POST']
 owner=next((e['response'] for e in setup if e['path']=='/owners'),None)
 pet=next((e['response'] for e in setup if e['path'].endswith('/pets')),None)
 wanted_path=('/owners' if r['template']=='owner_address_edit' else '/owners/'+str(owner['id'])+'/pets'+('' if r['template']=='pet_rename' else '/'+str(pet['id'])+'/visits'))
 require(prefix['path']==wanted_path and same(prefix['request'],registered['payload']),'Candidate prefix differs from registered command')
 guardmap={g['name']:g for g in guards}
 if case['prefix_status']==201:
  target=prefix['response'];kind={'owner_address_edit':'owners','pet_rename':'pets','visit_reschedule':'visits'}[r['template']]
  keys={'owners':['id','firstName','lastName','address','city','telephone'],'pets':['id','name','birthDate','type','ownerId'],'visits':['id','date','description','petId']}[kind]
  loaded=next(e['response'] for e in direct if e['phase']=='continuation_read' and e['path']=='/'+kind+'/'+str(target['id']))
  require(same(loaded,r['before']),'Loaded target is not trace-backed')
  g=guardmap['loaded_target_binding']
  require(same(g['expected'],{k:target[k] for k in keys}) and same(g['observed'],{k:loaded[k] for k in keys}),'Loaded-target guard is not bound to producer')
  change={'owners':{'address':'2 Pilot Lane'},'pets':{'name':'Renamedpet'},'visits':{'date':'2026-11-07'}}[kind]
  if kind=='owners':payload={**{k:loaded[k] for k in keys},**change}
  elif kind=='pets':
   require(loaded['ownerId']==owner['id'],'Pet belongs to wrong owner')
   payload={**{k:loaded[k] for k in ['id','name','birthDate','type']},**change}
  else:
   require(loaded['petId']==pet['id'],'Visit belongs to wrong pet')
   bound=next(e['response'] for e in direct if e['phase']=='binding_read' and e['path']=='/pets/'+str(loaded['petId']))
   require(bound['id']==pet['id'] and bound['ownerId']==owner['id'],'Wrong returned pet/owner chain')
   payload={'id':loaded['id'],'pet':bound,'date':change['date'],'description':loaded['description']}
  require(same(guardmap['continuation_edit_command']['expected'],{'method':'PUT','path':'/'+kind+'/'+str(target['id']),'payload':payload}),'Intended edit payload is not bound to loaded state')
  require(same(r['after'],{**loaded,**change}),'Final entity does not preserve untouched fields')
 before=integrity['before'];require(before['readable'] is True,'Unreadable before state')
 events=[e for e in r['trace'] if e.get('source')=='direct_api' and e.get('phase')=='pre_candidate_state' and e.get('path')=='/owners']
 require(len(events)==1 and events[0]['status']==200 and same(events[0]['response'],before['data']),'Before graph not trace-backed')
 if case['prefix_status']!=201:
  after=integrity['rejection']['after'];require(after['readable'] is True,'Unreadable after state')
  require(integrity['rejection']['status']=='unchanged' and same(before['data'],after['data']),'Rejected prefix changed observable graph')
  require(same(after['data'],r['post_prefix_graph']),'After graph not backed by post-prefix evidence')
  events=[e for e in r['trace'] if e.get('phase')=='post_prefix_state' and e.get('path')=='/owners']
  require(len(events)==1 and events[0]['status']==200 and same(events[0]['response'],after['data']),'After graph not trace-backed')
 capture=r['capture_integrity'];require(not capture['errors'],'Native capture errors')
 requests={};responses={}
 for e in r['trace']:
  if e.get('source') not in ('ui_request','ui_network'):continue
  target=requests if e['source']=='ui_request' else responses
  key=e['capture_request_id'];require(key not in target,'Duplicate capture request identifier')
  target[key]={k:e[k] for k in ['context_id','method','path','request_phase']}
 require(requests==responses,'Incomplete native request/response accounting')
 contexts=capture['contexts'];require(len(contexts)==(1 if case['prefix_status']==201 and r['oracle']=='fresh_ui' else 0),'Unexpected capture context count')
 for c in contexts:
  require(c['complete'] is True and c['timed_out'] is False and not c['outstanding'] and c['failures']==0,'Incomplete context drain')
  require(c['admitted']==c['completed']==len(requests),'Capture counts disagree')
 return {'guards':len(guards),'native_requests':len(requests),'capture_contexts':len(contexts),'rejection_state':(integrity.get('rejection') or {}).get('status')}

def validate_run(out,artifact):
 plan=read(artifact/'petclinic-integrity-plan.json');selection=read(ROOT/'manifests/petclinic-integrity-controls-v1.json');summary=read(out/'summary.json')
 for name,h in plan['source_sha256'].items():require(sha(ROOT/name)==h==sha(artifact/'petclinic-integrity-sources'/name),'Source changed: '+name)
 for name,h in plan['environment_sha256'].items():require(sha(artifact/name)==h,'Environment changed')
 for name,key in [('executed_boundary_slice.mjs','runner_sha256'),('petclinic_integrity.mjs','integrity_helper_sha256'),('petclinic_response_capture.mjs','capture_helper_sha256'),('petclinic_cleanup.mjs','cleanup_helper_sha256')]:
  require(sha(out/name)==summary[key],'Archived executing source changed')
  source='scripts/petclinic_boundary_slice.mjs' if name=='executed_boundary_slice.mjs' else 'scripts/'+name
  require(summary[key]==plan['source_sha256'][source],'Executing source differs from plan')
 require(summary['registry_sha256']==sha(out/'registered-candidates.json')==plan['source_sha256']['manifests/petclinic-candidates-v1.json'],'Registry mismatch')
 require(summary['jar_sha256']==read(artifact/'petclinic-bootstrap.json')['jar_sha256'],'Jar mismatch')
 wanted=[(c['id'],o) for c in selection['cases'] for o in selection['oracles']]
 require([(b['candidate_id'],b['oracle']) for b in summary['branches']]==wanted,'Incomplete/extra/reordered branches')
 require(not summary.get('stopped_after_harness_or_pair_failure') and summary['backend_stopped'],'Incomplete run')
 rows=[]
 for b in summary['branches']:
  p=out/b['result'];r=read(p);case=next(c for c in selection['cases'] if c['id']==b['candidate_id'])
  require(r['integrity']['helper_sha256']==summary['integrity_helper_sha256'] and r['capture_integrity']['helper_sha256']==summary['capture_helper_sha256'],'Helper mismatch')
  rows.append({'candidate_id':b['candidate_id'],'oracle':b['oracle'],'observation_sha256':sha(p),**validate_case(r,case)})
 require(len(summary['pairs'])==6,'Missing pairs')
 for pair,case in zip(summary['pairs'],selection['cases']):
  require(pair['candidate_id']==case['id'] and pair['initial_state_equal'] and pair['post_prefix_state_equal'],'Pair mismatch')
  members=[read(out/b['result']) for b in summary['branches'] if b['candidate_id']==case['id']]
  require(members[0]['initial_state_sha256']==members[1]['initial_state_sha256'],'Initial state hash mismatch')
  require(same(members[0]['post_prefix_graph'],members[1]['post_prefix_graph']),'Post-prefix pair state differs')
  for r in members:require(digest(r['post_prefix_graph'])==r['post_prefix_state_sha256'],'Post-prefix hash mismatch')
  if case['prefix_status']==201:require(pair['final_state_equal'] and same(members[0]['final_graph'],members[1]['final_graph']),'Positive pair final states differ')
 return {'status':'passed','branches':12,'positive_branches':6,'known_rejection_branches':6,'cases':rows,'source_commit':plan['source_commit'],'plan_sha256':sha(artifact/'petclinic-integrity-plan.json'),'primary_freeze_complete':False,'new_boundary_cases_executed':0,'historical_component_reducer_extended':False}
