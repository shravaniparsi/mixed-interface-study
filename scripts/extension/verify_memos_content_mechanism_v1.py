#!/usr/bin/env python3
"""Three qualified input-only counterfactuals for empty memo content."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def index(folder):return {read(p)['unit']['id']:p.parent for p in (ROOT/'results'/folder).rglob('report.json')}
def build():
    initial=index('memos-cases-v1-initial-ci-42901314025');follow=index('memos-followups-v1-ci-42902643603');proof=read(ROOT/'manifests/memos-followup-results-v1.json')
    ids=[('memo-content-empty-r1','memo-valid-1-r1',initial)]
    for c in proof['comparisons']:
        if c['case_id']=='memo-content-empty':
            assert c['control_qualified'] and c['matches_initial_channels'] and c['matches_initial_overlap'];ids.append((c['unit'],c['linked_control'],follow))
    assert len(ids)==3;rows=[]
    for uid,control,inventory in ids:
        row=dict(unit=uid,control=control,branches={})
        for channel in ['api','ui']:
            p=inventory[uid]/channel/'observation.json';q=inventory[control]/channel/'observation.json';a,b=read(p),read(q)
            assert {k for k in set(a['producer_body'])|set(b['producer_body']) if a['producer_body'].get(k)!=b['producer_body'].get(k)}=={'content'}
            assert a['producer_body']['content']=='' and b['producer_body']['content']=='Ordinary memo';assert a['initial_business_state']==b['initial_business_state'];assert a['producer_status']==b['producer_status']==200
            assert {k:v for k,v in a['prefix'].items() if k not in ['content','snippet']}=={k:v for k,v in b['prefix'].items() if k not in ['content','snippet']}
            assert a['prefix']['snippet']=='' and b['prefix']['snippet']=='Ordinary memo';assert not a['prefix']['attachments'] and not b['prefix']['attachments']
            assert b['final']=={**b['prefix'],'visibility':'PROTECTED'}
            if channel=='api':assert a['final']=={**a['prefix'],'visibility':'PROTECTED'}
            else:
                assert a['native_disabled'] is True and a['native_requests']==[] and a['final']==a['prefix'];assert b['native_disabled'] is False and len(b['native_requests'])==1 and b['native_requests'][0]['status']==200
            row['branches'][channel]=dict(boundary_observation=str(p.relative_to(ROOT)),boundary_sha256=sha(p),control_observation=str(q.relative_to(ROOT)),control_sha256=sha(q),producer_fields_differing=['content'],derived_readback_differences=['snippet'])
        rows.append(row)
    return dict(kind='memos_content_input_counterfactual_v1',application_commit='b40d8a7b573774c52b022c8d6537d6baf2129dc0',source_paths=['web/src/components/MemoEditor/edit/services/validationService.ts','web/src/components/MemoEditor/edit/services/memoService.ts'],rows=rows,independent_mechanisms=1,natural_defects_confirmed=0,interpretation='Three fresh qualified empty-content versus nonempty-content controls differ only in producer content; snippet changes are derived and disclosed. With no attachments, native validation disables an unrelated audience edit, while the full API edit succeeds. This validates task blockage, not a new natural defect or source-patch causality. The shared trimmed-nonempty consistency baseline already detects the input. Other empty/null/omitted/whitespace variants are not separate mechanisms; one omitted-content repeat remains control-unqualified in the full dataset.')
if __name__=='__main__':
    p=ROOT/'manifests/memos-content-mechanism-v1.json';assert not p.exists();v=build();p.write_text(json.dumps(v,indent=2)+'\n');print('Verified three matched memo content counterfactuals.')
