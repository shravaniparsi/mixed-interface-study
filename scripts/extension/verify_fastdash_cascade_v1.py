#!/usr/bin/env python3
"""Reconstruct schema, state, cascade and naive-frame outcomes from raw traces."""
import argparse,hashlib,json,sys
from pathlib import Path
import jsonschema
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from mixed_interface.write_frame import evaluate

def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def current(desc):return {r['id']:r['current_value'] for r in desc['inputs']}
def strings(v):
 if isinstance(v,str):return [v]
 if isinstance(v,dict):return sum([strings(x) for x in v.values()],[])
 if isinstance(v,list):return sum([strings(x) for x in v],[])
 return []
def build(archive):
 regpath=ROOT/'manifests/fastdash-cascade-calibration-v1.json';reg=read(regpath)
 for name,expected in reg['source_sha256'].items():assert sha(ROOT/name)==expected,name
 reports=sorted(archive.glob('*/fastdash-calibration/report.json'));assert len(reports)==2
 locks=list(archive.glob('fastdash-write-environment*/requirements.txt'));assert len(locks)==1
 lock=locks[0].read_text();scores=[];raw={};heads=set();runs=set()
 for rp in reports:
  report=read(rp);v=report['version'];assert report['status']=='observed' and v in reg['versions']
  assert report['registry_sha256']==sha(regpath);heads.add(report['study_commit']);runs.add(report['run_id'])
  for name,expected in report['files_sha256'].items():assert sha(rp.parent/name)==expected,name
  assert (rp.parent/'requirements.txt').read_text()==lock
  freeze=[c for c in report['commands'] if c['args']==['python','-m','pip','freeze','--all']];assert len(freeze)==1
  assert sorted((rp.parent/freeze[0]['log']).read_text().splitlines())==sorted(lock.splitlines())
  for name,expected in reg['upstream_git_blobs'][v].items():
   data=(rp.parent/'upstream-source'/name).read_bytes();assert hashlib.sha1(b'blob '+str(len(data)).encode()+b'\0'+data).hexdigest()==expected,name
  paths=sorted((rp.parent/'observations').glob('*.json'));assert len(paths)==4
  for path in paths:
   o=read(path);case=o['case'];assert case in reg['cases'] and o['status']=='observed'
   expected_before={'country':'India','state':None if case=='already_clear' else 'Karnataka','label':'original'}
   assert o['before']==expected_before
   assert current(o['describe_before'])==o['before']
   assert current(o['describe_after'])==o['after']==current(o['fresh_client_readback'])
   assert o['before_invoke']==o['after']==o['after_invoke']
   field,value={'parent_change':('country','USA'),'already_clear':('country','USA'),'explicit_clear':('state',None),'label_edit':('label','edited')}[case]
   assert o['input']=={'component_id':field,'value':value}
   schemas=[t['inputSchema'] for t in o['tool_catalog']['tools'] if t['name']=='set_input'];assert len(schemas)==1
   errors=sorted(e.message for e in jsonschema.Draft202012Validator(schemas[0]).iter_errors(o['input']))
   correct=dict(expected_before);correct[field]=value
   if case in ('parent_change','already_clear'):correct['state']=None
   mismatches=sorted(k for k in correct if o['after'].get(k)!=correct[k])
   naive=evaluate(o['before'],o['after'],{field:value})
   after_desc={x['id']:x for x in o['describe_after']['inputs']}
   options=after_desc['state']['options'];child=o['after']['state']
   invoke_expected='{label}: {state}, {country}'.format(**o['after'])
   invoke_success=o['invoke_response'].get('ok') is True
   output_matches=invoke_expected in strings(o['invoke_response'].get('outputs'))
   scores.append({'version':v,'case':case,'schema_valid':not errors,'schema_errors':errors,'operation_success':o['operation_response'].get('ok') is True,
    'requested_postcondition':o['after'].get(field)==value,'documented_contract_mismatches':mismatches,
    'naive_unnamed_field_alerts':naive['frame_violations'],'child_membership_valid':child is None or child in options,
    'invoke_success':invoke_success,'invoke_output_matches_actual_state':output_matches})
 for p in archive.rglob('*'):
  if p.is_file():raw[str(p.relative_to(ROOT))]=sha(p)
 assert len(heads)==len(runs)==1
 assert len({(s['version'],s['case']) for s in scores})==8
 controls=all(not s['documented_contract_mismatches'] and s['operation_success'] for s in scores if s['case']!='parent_change')
 predicted=all(s['documented_contract_mismatches']==(['state'] if s['version']=='historical' and s['case']=='parent_change' else []) for s in scores)
 return {'kind':'fastdash_cascade_reconstruction_v1','run_id':next(iter(runs)),'study_commit':next(iter(heads)),
  'executions':8,'known_reported_mechanisms':1,'new_defects_claimed':0,'controls_qualified':controls,
  'predicted_repair_pattern_reproduced':predicted,'contract_violation_executions':sum(bool(s['documented_contract_mismatches']) for s in scores),
  'naive_unnamed_preservation_alerts':sum(bool(s['naive_unnamed_field_alerts']) for s in scores),
  'scores':sorted(scores,key=lambda s:(s['version'],s['case'])),'raw_sha256':raw,'dependency_lock_sha256':sha(locks[0]),
  'limits':['Known issue-selected development case; no held-out efficacy or prevalence.',
  'Cross-request process memory only; no database, restart durability or browser execution.',
  'Repair commit contains other changes; no component-specific causal isolation.',
  'Documented cascade check is a manually specified competent baseline, not a new method.']}
def main():
 p=argparse.ArgumentParser();p.add_argument('--archive',type=Path,required=True);p.add_argument('--output',type=Path);p.add_argument('--verify',type=Path);a=p.parse_args();d=build(a.archive.resolve())
 if a.verify:assert read(a.verify)==d
 elif a.output:a.output.write_text(json.dumps(d,indent=2)+'\n')
 print(json.dumps({k:v for k,v in d.items() if k not in ('scores','raw_sha256','limits')}))
if __name__=='__main__':main()
