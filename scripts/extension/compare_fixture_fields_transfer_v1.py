#!/usr/bin/env python3
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from mixed_interface.constraint_transfer import evaluate
OUT=ROOT/'results/development-fixture-field-transfer-v1'
assert not OUT.exists(),'Closed field comparison'
OUT.mkdir()
raw=(ROOT/'results/development-test-serialization-v1/measurement.json').read_bytes();data=json.loads(raw)
lineage_raw=(ROOT/'manifests/development-lineage-v1.json').read_bytes();lineage=json.loads(lineage_raw)['rows'][0]
controls={r['payload_field']:r['control'] for r in lineage['calls'][0]['arguments'][0]['fields'] if 'control' in r}
scope={'revision':lineage['component_source']['commit'],'operation':'controlled_field_projection','actor':'analyst_fixture_adapter','lifecycle':'fresh_original_control_explicit_string'}
rows=[]
for fixture in data['rows']:
 for field in ['login','email','password']:
  row={'id':fixture['id']+':'+field,'body_sha256':fixture['body_sha256'],'field':field,'rules':[]}
  if field not in fixture['body'] or not isinstance(fixture['body'][field],str):row.update(verdict='unknown',reason='no_observed_string');rows.append(row);continue
  observation={'context':scope,'point':'field_validation','complete':True,'document':{'value':fixture['body'][field]}}
  for declaration in controls[field]['validators']:
   name=declaration['validator'];predicate={'kind':name}
   if name=='required':predicate={'kind':'present_nonnull'}
   if name in ['minLength','maxLength']:predicate={'kind':'length','units':'utf16_code_units','minimum':declaration['argument'] if name=='minLength' else None,'maximum':declaration['argument'] if name=='maxLength' else None}
   rule={'rule_id':field+':'+name,'source_evidence':lineage['component_source'],'conflicting_evidence':False,'mapping':{'status':'known','evidence':'controlled direct field assignment; not inferred original state','path':['value'],'transform':'identity'},'scope':scope,'observation_point':'field_validation','guards':[],'value_policy':{'missing':'unknown','null':'unknown','empty':'reject' if name=='required' else 'allow'},'predicate':predicate}
   row['rules'].append({'rule':rule,'outcome':evaluate(rule,observation)})
  verdicts=[x['outcome']['verdict'] for x in row['rules']]
  row['verdict']='code_error' if 'code_error' in verdicts else 'violated' if 'violated' in verdicts else 'unknown' if 'unknown' in verdicts else 'satisfied'
  rows.append(row)
result={'kind':'controlled_fixture_field_transfer','input_sha256':hashlib.sha256(raw).hexdigest(),'lineage_sha256':hashlib.sha256(lineage_raw).hexdigest(),'evaluator_sha256':hashlib.sha256((ROOT/'src/mixed_interface/constraint_transfer.py').read_bytes()).hexdigest(),'rows':rows,'independent_evaluation_cases':0,'full_frontend_state_reconstructed':False}
(OUT/'measurement.json').write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({'rows':len(rows),'verdicts':{k:sum(r['verdict']==k for r in rows) for k in ['satisfied','violated','unknown','code_error']}}))
