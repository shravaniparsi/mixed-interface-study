#!/usr/bin/env python3
"""Independently check primitive schema admissibility and frozen single-field edits."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def read(p):return json.loads(Path(p).read_text())
def sha(p):return hashlib.sha256(Path(p).read_bytes()).hexdigest()
def compatible(value,s):
    if value is None:return s.get('nullable',False) or 'type' not in s or s['type']=='null' or isinstance(s['type'],list) and 'null' in s['type']
    if 'enum' in s and not any(type(value)==type(v) and value==v for v in s['enum']):return False
    kind=s.get('type')
    if kind=='string':return isinstance(value,str) and s.get('minLength',0)<=len(value)<=s.get('maxLength',float('inf'))
    if kind=='boolean':return type(value) is bool
    if kind=='integer':return type(value) is int and s.get('minimum',float('-inf'))<=value<=s.get('maximum',float('inf'))
    if kind=='object':return isinstance(value,dict)
    if kind is None:return True
    return False

def build():
    p=ROOT/'manifests/independent-api-input-inventory-v1.json';v=read(p);selection=ROOT/'manifests/independent-input-selection-v1.json';assert sha(selection)==v['selection_sha256'];assert sha(ROOT/'scripts/extension/build_independent_inputs_v1.py')==v['generator_sha256'];assert not v['scientific_execution_authorized'] and not v['new_frontend_constraints_inspected']
    for path,h in v['source_sha256'].items():assert sha(ROOT/path)==h,path
    specs={w['id']:w for w in v['workflows'] if w['status'].startswith('api_input_frozen')};ids=set();payloads=set();rows=[]
    for c in v['generated']:
        assert c['id'] not in ids;ids.add(c['id']);s=specs[c['workflow']];body=c['producer_payload'];base=s['ordinary_payload'];different={k for k in set(base)|set(body) if k not in base or k not in body or base[k]!=body[k]};assert different=={c['field']} and c['field']!=s['edit_field'];assert c['field'] not in s['unsupported_fields'];assert set(s['api_required'])<=set(body)
        for key,value in body.items():assert compatible(value,s['api_fields'][key]),(c['id'],key,value)
        identity=(c['workflow'],json.dumps(body,sort_keys=True));assert identity not in payloads;payloads.add(identity)
        rows.append(c['id'])
    selected={c['id'] for c in v['selected']};unselected={c['id'] for c in v['unselected']};assert not selected&unselected and selected|unselected==ids
    assert all(sum(c['workflow']==wid for c in v['selected'])<=12 for wid in specs)
    assert len(v['ordinary_controls'])==4*len(specs)
    # Check that the schema checker does not silently accept common type/enum confusions.
    assert not compatible(True,{'type':'integer'}) and not compatible('1',{'type':'integer'}) and not compatible(None,{'type':'string'}) and not compatible('other',{'type':'string','enum':['valid']})
    return dict(kind='independent_input_inventory_verification_v1',inventory_sha256=sha(p),verifier_sha256=sha(__file__),generated_count=len(ids),selected_count=len(selected),unselected_count=len(unselected),ordinary_controls=len(v['ordinary_controls']),candidate_workflows=len(v['workflows']),schema_supported_workflows=len(specs),all_single_field_schema_admissibility_checks_passed=True,limitations='Checks resolved primitive schema syntax and nullable/required flags; does not assert server business validity, eligibility of native workflow, or preservation success.')
if __name__=='__main__':
    p=ROOT/'manifests/independent-api-input-verification-v1.json';assert not p.exists();v=build();p.write_text(json.dumps(v,indent=2)+'\n');print(json.dumps(v,indent=2))
