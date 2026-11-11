#!/usr/bin/env python3
"""Reconstruct real-route bulk preservation observations without trusting observer labels."""
import argparse
import hashlib
import json
from pathlib import Path
import sys
from collections import Counter
import jsonschema
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from mixed_interface.write_frame import evaluate

CASES={
 'priority_relations':([1,27,30],['priority'],{'priority':3}),
 'priority_clean':([3],['priority'],{'priority':3}),
 'clear_assignees':([30],['assignees'],{'assignees':[]}),
 'clear_reminders':([27],['reminders'],{'reminders':[]}),
 'clear_favorite':([1],['is_favorite'],{'is_favorite':False}),
 'single_priority':([30],['priority'],{'priority':3}),
}
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def content(result):
 if 'structuredContent' in result:return result['structuredContent']
 texts=[c['text'] for c in result.get('content',[]) if c.get('type')=='text']
 assert len(texts)==1, texts
 return json.loads(texts[0])
def relations(entity,table):
 keys={'assignees':['task_id','user_id'],'reminders':['task_id','reminder','relative_to','relative_period'],'favorites':['entity_id','user_id','kind']}[table]
 return sorted([{k:r.get(k) for k in keys} for r in entity[table]],key=lambda x:json.dumps(x,sort_keys=True))
def build(archive):
 regpath=ROOT/'manifests/vikunja-bulk-calibration-v2.json';reg=read(regpath)
 for name,expected in reg['source_sha256'].items():assert sha(ROOT/name)==expected,name
 reports=sorted(archive.glob('*/report.json'));assert len(reports)==2
 scores=[];raw_hashes={};before_by_key={};run_ids=set();heads=set()
 for rp in reports:
  report=read(rp);version=report['version'];assert version in reg['versions']
  assert report['status']=='observed',report
  assert report['registry_sha256']==sha(regpath)
  run_ids.add(report['run_id']);heads.add(report['study_commit'])
  for name,expected in report['files_sha256'].items():assert sha(rp.parent/name)==expected,name
  for name,expected in reg['upstream_git_blobs'][version].items():
   data=(rp.parent/'upstream-source'/name).read_bytes()
   assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==expected,name
  paths=sorted((rp.parent/'observations').glob('*.json'));assert len(paths)==12
  for path in paths:
   o=read(path);case=o['case'];channel=o['channel'];assert channel in ('rest','mcp')
   ids,fields,values=CASES[case]
   assert o['task_ids']==ids and o['fields']==fields and o['values']==values
   assert o['status']=='observed'
   assert set(o['before'])==set(o['after'])==set(map(str,ids))
   before_by_key[(version,case,channel)]=o['before']
   actions=content(o['action_schema_response'])['actions']
   assert len(actions)==1 and actions[0]['name']=='tasks_bulk_update',actions
   canonical={'task_ids':ids,'fields':fields,'values':values}
   if case=='single_priority':
    canonical={'task':ids[0],'priority':3}
    tools=[t for t in o['tool_catalog'] if t['name']=='tasks_update'];assert len(tools)==1
    schema=tools[0]['inputSchema']
   else:schema=actions[0]['input_schema']
   schema_errors=sorted(e.message for e in jsonschema.Draft202012Validator(schema).iter_errors(canonical))
   if channel=='mcp':
    expected=canonical if case=='single_priority' else {'action':'tasks_bulk_update','arguments':canonical}
    assert o['input']==expected
    success=o['response'].get('isError') is not True
   else:
    assert o['input']==(values if case=='single_priority' else canonical)
    success=200<=o['response']['http_status']<300
   assert success==o['operation_success']
   violations=[];requested=[];api_status=[]
   for ident in map(str,ids):
    b,a=o['before'][ident],o['after'][ident]
    assert len(b['tasks'])==len(a['tasks'])==1
    bt,at=b['tasks'][0],a['tasks'][0]
    assert int(bt['id'])==int(at['id'])==int(ident)
    # Fixture qualification is independent of the observed response.
    if ident=='30':assert [int(x['user_id']) for x in b['assignees']]==[1,2]
    if ident=='27':assert len(b['reminders'])==2
    if ident=='1':assert any(int(x['user_id'])==1 for x in b['favorites'])
    if ident=='3':assert not any(b[k] for k in ('assignees','reminders','favorites'))
    assignments={'priority':3} if 'priority' in fields else {}
    frame=evaluate(bt,at,assignments,['updated'])
    violations.extend(ident+'/tasks/'+k for k in frame['frame_violations'])
    if assignments:requested.append(not frame['failed_assignments'])
    for table,field in [('assignees','assignees'),('reminders','reminders'),('favorites','is_favorite')]:
     old,new=relations(b,table),relations(a,table)
     if field not in fields and old!=new:violations.append(ident+'/'+table)
     if field in fields:
      requested.append(not new if field!='is_favorite' else not any(int(r['user_id'])==1 for r in new))
    for phase in ('api_before','api_after'):
     response=o[phase][ident];api_status.append(response['http_status']==200)
     assert isinstance(response['body'],str)
   scores.append({'version':version,'case':case,'channel':channel,'schema_basis':'canonical MCP action arguments (REST body not independently schema-validated)',
     'schema_valid':not schema_errors,'schema_errors':schema_errors,'operation_success':success,
     'requested_postcondition':all(requested),'frame_violations':sorted(violations),
     'all_readbacks_http_200':all(api_status)})
  for path in rp.parent.rglob('*'):
   if path.is_file():raw_hashes[str(path.relative_to(ROOT))]=sha(path)
 assert len(run_ids)==len(heads)==1
 assert len({(s['version'],s['case'],s['channel']) for s in scores})==24
 for version in reg['versions']:
  for case in CASES:assert before_by_key[(version,case,'rest')]==before_by_key[(version,case,'mcp')]
 for case in CASES:assert before_by_key[('historical',case,'rest')]==before_by_key[('fixed',case,'rest')]
 scores.sort(key=lambda s:(s['version'],s['case'],s['channel']))
 return {'kind':'vikunja_bulk_reconstruction_v1','run_id':next(iter(run_ids)),'study_commit':next(iter(heads)),
  'status':'reconstructed','executions':len(scores),'known_repair_families':1,'new_defects_claimed':0,
  'canonical_schema_valid':sum(s['schema_valid'] for s in scores),
  'successful_operations':sum(s['operation_success'] for s in scores),
  'frame_alert_executions':sum(bool(s['frame_violations']) for s in scores),
  'rejections':dict(Counter(s['version'] for s in scores if not s['operation_success'])),
  'all_api_readbacks_http_200':all(s['all_readbacks_http_200'] for s in scores),
  'scores':scores,'raw_sha256':raw_hashes,
  'limits':['Historical, outcome-exposed development calibration; not unseen efficacy or prevalence.',
            'Target task/relation tables only; upstream fixture fakes event delivery.',
            'Field-mask frame is manually specified; baseline is not novel.',
            'Schema score validates canonical MCP arguments, not independently captured REST OpenAPI schemas.']}
def main():
 p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--output',type=Path);p.add_argument('--verify',type=Path);a=p.parse_args();d=build(a.archive.resolve())
 if a.verify:assert read(a.verify)==d
 elif a.output:a.output.write_text(json.dumps(d,indent=2)+'\n')
 print(json.dumps({k:v for k,v in d.items() if k not in ('scores','raw_sha256','limits')}))
if __name__=='__main__':main()
