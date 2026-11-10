#!/usr/bin/env python3
"""Input-only comparisons and concrete native failure evidence for Gitea."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def index(folder):return {read(p)['unit']['id']:p.parent for p in (ROOT/'results'/folder).rglob('report.json')}
def business(v):return {k:x for k,x in v.items() if k not in ['created_at','updated_at']}
def preserve(v):return {k:x for k,x in v.items() if k!='updated_at'}
def build():
    first=read(ROOT/'manifests/gitea-initial-results-v1.json');later=read(ROOT/'manifests/gitea-followup-results-v1.json');initial=index('gitea-cases-v1-initial-ci-42911846583');follow=index('gitea-followups-v1-ci-42912939898');reg=read(ROOT/'manifests/gitea-execution-v1.json');specs={s['id']:s for s in reg['workflows']};ids=[];excluded=[]
    for uid in first['followup_candidates']:ids.append((uid,first['records'][uid]['unit']['linked_valid_control'],initial,first['records'][uid]['unit']))
    for c in later['comparisons']:
        if c['qualified'] and c['matches_initial_outcomes'] and c['matches_initial_overlap']:ids.append((c['unit'],c['linked_control'],follow,later['records'][c['unit']]['unit']))
        else:excluded.append(c)
    rows=[]
    for uid,control,inventory,unit in ids:
        s=specs[unit['workflow']];collection='/api/v1/repos/study-actor/study-repo/'+s['collection'];field='title' if s['id']=='milestone' else 'name';row=dict(unit=uid,control=control,branches={})
        for channel in ['api','ui']:
            p=inventory[uid]/channel/'observation.json';q=inventory[control]/channel/'observation.json';a,b=read(p),read(q);pa=next(r['body'] for r in a['requests'] if r['method']=='POST' and r['path']==collection);pb=next(r['body'] for r in b['requests'] if r['method']=='POST' and r['path']==collection)
            assert {k for k in set(pa)|set(pb) if k not in pa or k not in pb or pa[k]!=pb[k]}=={field};assert a['initial_business_state']==b['initial_business_state'];assert {k:v for k,v in business(a['prefix']).items() if k!=field}=={k:v for k,v in business(b['prefix']).items() if k!=field}
            assert preserve(b['final'])==preserve({**b['prefix'],'description':s['edit_value']});evidence='clean_api_edit'
            if channel=='api':assert preserve(a['final'])==preserve({**a['prefix'],'description':s['edit_value']})
            else:
                writes=a['native_requests']
                if not writes:
                    assert a['save_control']['form_valid'] is False and not a['native_attempts'] and a['final']==a['prefix'];evidence='blocked_invalid_native_form'
                elif writes[0]['status']==400:
                    assert a['final']==a['prefix'] and 'at most 50 characters' in writes[0]['response'];evidence='native_400_length_rejection'
                elif a['final']==a['prefix']:
                    assert writes[0]['status']==200 and 'Title must contain at most 50 characters.' in writes[0]['response'];evidence='native_200_length_error_without_edit'
                else:
                    assert s['id']=='label' and a['prefix']['exclusive'] is True and preserve(a['final'])==preserve({**a['prefix'],'description':s['edit_value'],'exclusive':False});evidence='native_clears_exclusive_for_unscoped_name'
            row['branches'][channel]=dict(boundary_observation=str(p.relative_to(ROOT)),boundary_sha256=sha(p),control_observation=str(q.relative_to(ROOT)),control_sha256=sha(q),producer_fields_differing=[field],evidence=evidence)
        rows.append(row)
    return dict(kind='gitea_input_counterfactuals_v1',application_commit=reg['source_commit'],rows=rows,excluded_unqualified_or_nonmatching_repeats=excluded,natural_defects_confirmed=0,source_paths=['services/forms/repo_form.go','web_src/js/features/comp/LabelEdit.ts','routers/web/repo/milestone.go','routers/web/repo/issue_label.go'],interpretation='Input-only ordinary repairs recover the edit. Required title, maximum length and scoped-name/exclusive rules were source-exposed and credited to both baselines. A200milestone response can be a validation-error page; unchanged readback proves the edit did not occur, not data corruption. The overlong label also lacks a scope, so its input repair changes two logical constraint conditions despite changing only one field. No independent source-patch intervention or new-defect assertion.')
if __name__=='__main__':
    p=ROOT/'manifests/gitea-counterfactuals-v1.json';assert not p.exists();v=build();p.write_text(json.dumps(v,indent=2)+'\n');print('Verified',len(v['rows']),'Gitea input counterfactuals; excluded',len(v['excluded_unqualified_or_nonmatching_repeats']))
