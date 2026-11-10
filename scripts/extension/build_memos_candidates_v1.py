#!/usr/bin/env python3
"""Prospective finite source-derived inventory; execution remains gated on probes."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SEED='production-extension-v1:memos:20261110'
def build():
    candidates=[]
    for field in ['content']:
        for kind,value in [('omitted',None),('null',None),('empty',''),('whitespace','   ')]:
            candidates.append({'id':'memo-'+field+'-'+kind,'workflow':'memo','field':field,'mutation':kind,'value':value,'family':'nonempty_content'})
    for field in ['locale','theme','memoVisibility']:
        for kind,value in [('omitted',None),('null',None),('empty',''),('whitespace','   '),('unknown','study-unsupported')]:
            candidates.append({'id':'preferences-'+field+'-'+kind,'workflow':'preferences','field':field,'mutation':kind,'value':value,'family':field+'_options'})
    selected=[];unselected=[]
    for workflow in ['memo','preferences']:
        rows=[c for c in candidates if c['workflow']==workflow];families=sorted({c['family'] for c in rows});queues={f:sorted([c for c in rows if c['family']==f],key=lambda c:hashlib.sha256((SEED+':'+c['id']).encode()).hexdigest()) for f in families};ordered=[]
        while any(queues.values()):
            for f in families:
                if queues[f]:ordered.append(queues[f].pop(0))
        selected+=ordered[:12];unselected+=ordered[12:]
    valid=[{'id':w+'-valid-'+str(i),'workflow':w,'cohort':'valid_control'} for w in ['memo','preferences'] for i in range(1,5)]
    return {'kind':'memos_source_candidate_inventory_v1','source_commit':'b40d8a7b573774c52b022c8d6537d6baf2129dc0','seed':SEED,'execution_authorized':False,'generated_boundary':candidates,'selected_boundary':selected,'unselected_boundary':unselected,'valid_controls':valid,'qualification_pending':['native violating adapter probes','final preference option qualification','frozen finite executor and independent verifier'],'normalization_policy':{'protobuf_strings':'Omitted/null scalar strings may read back as empty by protobuf semantics; compare stored prefix with continuation, not raw input alone.','preference_fallback':'Known display fallback alone is not a persisted-field discrepancy or requirement-backed defect.','memo_content':'Compare exact API content within branch; native editable text representation must be separately qualified for empty/whitespace.'},'scope':'Two workflows. Preference candidates use explicit all-field mask against a separately initialized ordinary GENERAL record. Omission resets masked scalar rather than omitting the mask. Memo audience edit preserves content; no audience candidate is used because that is the continuation edit. No attachment/network-dependent or unqualified extra-resource cases.'}
if __name__=='__main__':
    result=build();target=ROOT/'manifests/memos-candidate-inventory-v1.json';target.write_text(json.dumps(result,indent=2)+'\n');print(json.dumps({k:len(result[k]) for k in ['generated_boundary','selected_boundary','unselected_boundary','valid_controls']}))
