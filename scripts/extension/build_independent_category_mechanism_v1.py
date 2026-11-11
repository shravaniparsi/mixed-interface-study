#!/usr/bin/env python3
"""Verify the finite empty-name mechanism against linked ordinary records."""
import hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build():
    initial=ROOT/'results/independent-grocy-category-cases-v1-ci-43071019063'
    follow=ROOT/'results/independent-grocy-category-followups-v1-ci-43072084690'
    indexed={read(p)['unit']['id']:p.parent for parent in [initial,follow] for p in parent.rglob('report.json')}
    pairs=[('category-sample-3','category-valid-1'),('category-empty-r2','category-control-r2'),('category-empty-r3','category-control-r3')];rows=[];sources={}
    for case_id,control_id in pairs:
        row={'case_unit':case_id,'control_unit':control_id,'channels':{}}
        for channel in ['api','ui']:
            a=indexed[case_id]/channel/'observation.json';b=indexed[control_id]/channel/'observation.json';case,control=read(a),read(b)
            for p in [a,b]:sources[str(p.relative_to(ROOT))]=sha(p)
            assert case['status']==control['status']=='observed' and case['browser_cleanup_confirmed'] and control['browser_cleanup_confirmed']
            assert case['initial_business_state']==control['initial_business_state'] and case['fixture_ids']==control['fixture_ids']=={}
            assert set(case['prefix'])==set(control['prefix'])=={'name','description','active'}
            changed=[k for k in case['prefix'] if case['prefix'][k]!=control['prefix'][k]];assert changed==['name']
            assert case['resolved_payload']['name']=='' and case['prefix']['name'] is None and control['prefix']['name']=='Ordinary category'
            assert case['persisted_contract_violations']==['name'] and control['persisted_contract_violations']==[]
            assert control['continuation']=='clean_preserving_continuation'
            assert control['final']=={**control['prefix'],'description':'Edited ordinary description'}
            assert case['immutable_before']==case['immutable_after'] and control['immutable_before']==control['immutable_after']
            if channel=='api':
                assert case['continuation']=='clean_preserving_continuation' and case['final']=={**case['prefix'],'description':'Edited ordinary description'}
            else:
                assert case['continuation']=='blocked_native_validation' and case['final']==case['prefix']
                assert not case['native_submission']['form_valid'] and case['native_submission']['attempts']==[]
                form=case['forms'][1];name=next(f for f in form['fields'] if f['name']=='name');assert name['value']=='' and name['details']['required'] and name['details']['valueMissing']
                desc=next(f for f in form['fields'] if f['name']=='description');assert desc['value']=='Edited ordinary description'
            row['channels'][channel]={'only_changed_preserved_field':'name','case_outcome':case['continuation'],'control_outcome':control['continuation'],'case_shared_alert':['name'],'producer_name':'','persisted_name':None}
        rows.append(row)
    return dict(kind='independent_category_input_counterfactuals_v1',comparisons=rows,comparison_pairs=len(rows),mechanisms=1,native_only_detections=0,natural_defects_confirmed=0,source_sha256=sources,interpretation='Three observations of one schema-sampled empty-name mechanism. API creation converts the empty name to null and the API description edit preserves that null, while native required-name validation blocks the same edit. The shared nonnullable-string/required-name baseline predicts this state in every observation; this is not a novel mechanism or an incremental native-only detection.')
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args();target=ROOT/'manifests/independent-grocy-category-mechanism-v1.json';v=build()
    if a.verify:assert read(target)==v
    else:assert not target.exists();target.write_text(json.dumps(v,indent=2)+'\n')
    print(json.dumps({k:v[k] for k in ['comparison_pairs','mechanisms','native_only_detections']}))
