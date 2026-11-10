#!/usr/bin/env python3
"""Source/probe qualified finite Gitea inventory, generated before boundary writes."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
SEED='production-extension-v1:gitea:20261110'
def build():
    generated=[]
    def add(w,f,m,v=None,family=None):
        c=dict(id=w+'-'+f+'-'+m,workflow=w,field=f,mutation=m,family=family or f,cohort='boundary')
        if m!='omitted':c['value']=v
        generated.append(c)
    for w,f in [('milestone','title'),('label','name')]:
        for m,v in [('omitted',None),('null',None),('empty',''),('whitespace','   '),('below','X'*49),('at','X'*50),('above','X'*51)]:add(w,f,m,v)
    add('label','name','unscoped','ordinary')
    for m,v in [('omitted',None),('null',None),('empty',''),('invalid','invalid'),('short','#abc'),('below_short','#ab'),('above_long','#1234567'),('uppercase','#ABCDEF'),('no_hash','336699')]:add('label','color',m,v)
    selected=[]
    for w in ['milestone','label']:
        groups={f:sorted([c for c in generated if c['workflow']==w and c['family']==f],key=lambda c:hashlib.sha256((SEED+':'+c['id']).encode()).hexdigest()) for f in sorted({c['family'] for c in generated if c['workflow']==w})}
        chosen=[]
        while any(groups.values()) and len(chosen)<12:
            for f in groups:
                if groups[f] and len(chosen)<12:chosen.append(groups[f].pop(0))
        selected+=chosen
    ids={c['id'] for c in selected}
    valid=[dict(id=w+'-valid-'+str(i),workflow=w,cohort='valid_control') for w in ['milestone','label','issue'] for i in range(1,5)]
    return dict(kind='gitea_candidate_inventory_v1',seed=SEED,execution_authorized=False,generated=generated,selected=selected,unselected=[c for c in generated if c['id'] not in ids],valid_controls=valid,selection_rule='SHA256 order per family, round-robin families, cap12perworkflow before outcomes',source_constraints={'milestone.title':'Native required/max50; server Required/MaxSize50. Empty and maxlength adapter probes qualified.','label.name':'Native required/max50; source exclusive requires slash-delimited scope. Required/max50 and live unscoped deselection probes qualified.','label.color':'Native required/max7/optional-hash three-or-six hex pattern; live valid/invalid probe qualified.'},excluded_constraints={'issue':'Body editor is field-local, has no native required/length constraint and does not resubmit title. Separate title-editor maxlength255 is not a body-continuation constraint; retain four ordinary controls and record zero generated boundaries.','description':'Continuation edit, not a producer mutation target','milestone.due_on':'Date-only day-end semantics disclosed before outcomes; no independent business restriction established.','label.exclusive_order':'Not API writable/returned; native preservation metadata only.'},interpretation='Shared consistency baseline includes qualified title/name/color constraints and source name/exclusive relation. Whitespace is not treated as a native HTML required violation merely by trimming. All variants and repeats are correlated; no novelty claim from source-exposed rules.')
if __name__=='__main__':
    p=ROOT/'manifests/gitea-candidate-inventory-v1.json';assert not p.exists();v=build();p.write_text(json.dumps(v,indent=2)+'\n');print({k:len(v[k]) for k in ['generated','selected','unselected','valid_controls']})
