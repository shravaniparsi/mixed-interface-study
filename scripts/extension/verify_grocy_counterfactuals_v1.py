#!/usr/bin/env python3
"""Reconstruct all registered Grocy differential/control input comparisons."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def index(folder):return {read(p)['unit']['id']:p.parent for p in (ROOT/'results'/folder).rglob('report.json')}
def build():
    initial=index('grocy-cases-v1-initial-ci-42893369321');follow=index('grocy-followups-v1-ci-42894961954');first=read(ROOT/'manifests/grocy-initial-results-v1.json');later=read(ROOT/'manifests/grocy-followup-results-v1.json');reg=read(ROOT/'manifests/grocy-execution-v1.json');specs={s['id']:s for s in reg['workflows']};ids=[]
    for uid,r in first['records'].items():
        if r['classification']=='channel_difference':ids.append((uid,r['case_id'].split('-')[0]+'-valid-1-r1',initial))
    for c in later['comparisons']:
        assert c['control_qualified'] and c['matches_initial_channels'] and c['matches_initial_overlap'];ids.append((c['unit'],c['linked_control'],follow))
    assert len(ids)==39;rows=[]
    for uid,control,inventory in ids:
        workflow=uid.split('-')[0];s=specs[workflow];row=dict(unit=uid,control=control,workflow=workflow,branches={})
        for channel in ['api','ui']:
            p=inventory[uid]/channel/'observation.json';q=inventory[control]/channel/'observation.json';a,b=read(p),read(q)
            changed={k for k in set(a['resolved_payload'])|set(b['resolved_payload']) if a['resolved_payload'].get(k)!=b['resolved_payload'].get(k)};assert len(changed)==1;field=next(iter(changed));assert field!=s['edit_field']
            assert a['initial_business_state']==b['initial_business_state'] and a['fixture_ids']==b['fixture_ids'];assert {k:v for k,v in a['prefix'].items() if k!=field}=={k:v for k,v in b['prefix'].items() if k!=field}
            assert b['final']=={**b['prefix'],s['edit_field']:s['edit_value']};assert b['immutable_before']==b['immutable_after'];assert a['immutable_before']==a['immutable_after']
            if channel=='api':assert a['final']=={**a['prefix'],s['edit_field']:s['edit_value']} and a['continuation']=='clean_preserving_continuation'
            else:
                assert a['continuation'] in ['blocked_native_validation','preservation_or_edit_discrepancy']
                if a['continuation']=='blocked_native_validation':assert a['native_submission']['form_valid'] is False and not a['native_submission']['attempts'] and a['final']==a['prefix']
                else:assert a['final']!={**a['prefix'],s['edit_field']:s['edit_value']}
            row['branches'][channel]=dict(boundary_observation=str(p.relative_to(ROOT)),boundary_sha256=sha(p),control_observation=str(q.relative_to(ROOT)),control_sha256=sha(q),producer_fields_differing=[field],boundary_continuation=a['continuation'],control_continuation=b['continuation'])
        rows.append(row)
    return dict(kind='grocy_input_counterfactuals_v1',application_commit=reg['source_commit'],rows=rows,initial_variants=13,repetitions_per_variant=3,natural_defects_confirmed=0,interpretation='All39registered differential/control comparisons differ in exactly one producer field, with matched starting fixtures and other persisted business fields. Ordinary input repair permits the unrelated native edit; API semantic continuations succeed in both inputs. These are13correlated variants, not39defects or13independent mechanisms. Required values, minimum stock and reference existence are already shared baseline signals. This is input-only counterfactual evidence, not a source-patch intervention; requirement and novelty adjudication remain separate.')
if __name__=='__main__':
    p=ROOT/'manifests/grocy-counterfactuals-v1.json';assert not p.exists();v=build();p.write_text(json.dumps(v,indent=2)+'\n');print('Verified39Grocy matched input-only counterfactuals.')
