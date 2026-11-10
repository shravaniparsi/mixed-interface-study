#!/usr/bin/env python3
"""Input-only counterfactual packet from registered, independently qualified controls."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def records(folder):
    return {read(p)['unit']['id']:p.parent for p in (ROOT/'results'/folder).rglob('report.json')}
def build():
    initial=records('vikunja-cases-v1-initial-ci-42907501262');follow=records('vikunja-followups-v1-ci-42908626421');proof=read(ROOT/'manifests/vikunja-followup-results-v1.json');rows=[]
    ids=[('task-title-whitespace-r1','task-valid-1-r1',initial)]
    for c in proof['comparisons']:
        if c['case_id']=='task-title-whitespace':
            assert c['control_qualified'] and c['matches_initial_channels'] and c['matches_initial_overlap'];ids.append((c['unit'],c['linked_control'],follow))
    assert len(ids)==3
    for uid,control,inventory in ids:
        row={'unit':uid,'control':control,'branches':{}}
        for channel in ['api','ui']:
            p=inventory[uid]/channel/'observation.json';q=inventory[control]/channel/'observation.json';a,b=read(p),read(q)
            differing={k for k in set(a['producer_body'])|set(b['producer_body']) if a['producer_body'].get(k)!=b['producer_body'].get(k)};assert differing=={'title'};assert a['producer_body']['title']=='   ' and b['producer_body']['title']=='Ordinary task'
            assert a['initial_business_state']==b['initial_business_state'] and a['fixture_business']==b['fixture_business']
            assert {k:v for k,v in a['prefix_business'].items() if k!='title'}=={k:v for k,v in b['prefix_business'].items() if k!='title'}
            assert b['continuation_status']==200 and b['final']['description']=='<p>Edited ordinary description</p>'
            assert a['continuation_status']==(200 if channel=='api' else 422)
            if channel=='ui':
                body=json.loads(a['fetch_requests'][0]['body']);assert next(x for x in body if x['path']=='/title')['value']==''
                response=json.loads(a['native_requests'][0]['response']);assert any(e['location']=='body.title' and e['value']=='' for e in response['errors']);assert a['final']==a['prefix']
            else:assert a['final']['title']=='   ' and a['final']['description']=='<p>Edited ordinary description</p>'
            row['branches'][channel]={'boundary_observation':str(p.relative_to(ROOT)),'boundary_sha256':sha(p),'control_observation':str(q.relative_to(ROOT)),'control_sha256':sha(q),'producer_fields_differing':['title'],'boundary_status':a['continuation_status'],'control_status':200}
        rows.append(row)
    return dict(kind='vikunja_title_input_counterfactual_v1',application_commit='6e788bf87cebe50e2b8d034b213fcf94ae5449ee',source_paths=['frontend/src/client/queries/taskMutations.ts','frontend/src/components/tasks/partials/Heading.vue','pkg/models/tasks.go'],rows=rows,independent_mechanisms=1,natural_defects_confirmed=0,interpretation='Three fresh matched observations support title trimming as the mechanism for failed native description edits. Original ordinary controls change only producer title. This is input-only counterfactual evidence, not an application patch intervention or a novelty claim. Shared trimmed-nonempty baseline already detects the boundary value.')
if __name__=='__main__':
    p=ROOT/'manifests/vikunja-title-mechanism-v1.json';assert not p.exists();v=build();p.write_text(json.dumps(v,indent=2)+'\n');print('Verified three matched input-only counterfactual pairs.')
