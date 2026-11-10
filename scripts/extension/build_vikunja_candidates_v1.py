#!/usr/bin/env python3
"""Deterministic finite inventory before Vikunja boundary observations."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SEED='production-extension-v1:vikunja:20261110'
def build():
    generated=[]
    def add(workflow,field,mutation,value=None,family=None):
        d=dict(id=workflow+'-'+field+'-'+mutation,workflow=workflow,field=field,mutation=mutation,family=family or field,cohort='boundary')
        if mutation!='omitted':d['value']=value
        generated.append(d)
    for wf in ['project','label']:
        for mutation,value in [('omitted',None),('null',None),('empty',''),('whitespace','   '),('invalid','not-a-color'),('shorthand','abc'),('below_short','ab'),('above_long','1234567'),('uppercase','ABCDEF')]:add(wf,'hex_color',mutation,value)
    for mutation,value in [('omitted',None),('null',None),('empty',''),('whitespace','   '),('below','ABCDEFGHI'),('at','ABCDEFGHIJ'),('above','ABCDEFGHIJK')]:add('project','identifier',mutation,value)
    for mutation,value in [('omitted',None),('null',None),('empty',''),('whitespace','   '),('leading_space',' Ordinary task'),('trailing_space','Ordinary task ')]:add('task','title',mutation,value)
    selected=[]
    for wf in ['project','label','task']:
        groups={f:sorted([x for x in generated if x['workflow']==wf and x['family']==f],key=lambda x:hashlib.sha256((SEED+':'+x['id']).encode()).hexdigest()) for f in sorted({x['family'] for x in generated if x['workflow']==wf})}
        chosen=[]
        while any(groups.values()) and len(chosen)<12:
            for f in groups:
                if groups[f] and len(chosen)<12:chosen.append(groups[f].pop(0))
        selected.extend(chosen)
    valid=[dict(id=wf+'-valid-'+str(i),workflow=wf,cohort='valid_control') for wf in ['project','label','task'] for i in range(1,5)]
    selected_ids={c['id'] for c in selected}
    return dict(kind='vikunja_candidate_inventory_v1',seed=SEED,execution_authorized=False,generated=generated,selected=selected,unselected=[c for c in generated if c['id'] not in selected_ids],valid_controls=valid,selection_rule='Stable SHA256 ordering within field families, round-robin families, cap12perworkflow. No observed boundary outcomes.',source_constraints={'project.identifier':'ProjectSettingsEdit.vue maxlength10; actual DOM qualification required','project.hex_color':'ColorPicker.vue native color input plus explicit empty reset and3/6character binding; server hexcolor validator','label.hex_color':'Same shared ColorPicker component; not an independent mechanism','task.title':'Heading.vue trimmed-nonempty rule and taskMutations.ts trim-on-write; leading/trailing normalization deliberately retained'},excluded_constraints={'project.title':'Unrelated continuation edit; cannot also mutate it','label.title':'Unrelated continuation edit; no native required/length attributes in qualified view','task.priority':'Source explicitly permits arbitrary priority; finite selector is not an established business range','task.other_fields':'No constraint extraction or violating adapter qualification in this registered task workflow'},interpretation='Color representability is distinct from business validity. Empty picker reset and task title trimming are source-declared behavior, not automatic defects. All generated/unselected cases remain recorded.')
if __name__=='__main__':
    target=ROOT/'manifests/vikunja-candidate-inventory-v1.json';assert not target.exists();v=build();target.write_text(json.dumps(v,indent=2)+'\n');print(json.dumps({k:len(v[k]) for k in ['generated','selected','unselected','valid_controls']}))
