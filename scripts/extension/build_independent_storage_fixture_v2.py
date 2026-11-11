#!/usr/bin/env python3
"""Prospective identity-only correction; preserve the original frozen inventory."""
import copy,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build():
    source=ROOT/'manifests/independent-api-input-inventory-v1.json'
    old=json.loads(source.read_text());wid='paperless.storage_path'
    workflow=next(w for w in old['workflows'] if w['id']==wid)
    evidence=sorted((ROOT/'results/independent-paperless-storage-controls-v1-ci-43070783189').glob('*/pair/*/observation.json'))
    assert len(evidence)==4
    for p in evidence:
        o=json.loads(p.read_text());assert o['status']=='ordinary_control_passed'
        assert o['initial_business_state']['actor_id']==2 and o['prefix']['owner']==2
    corrected=copy.deepcopy(workflow);assert corrected['ordinary_payload']['owner']==1
    corrected['ordinary_payload']['owner']=2
    corrected['fixture_constraints']['owner']='Separate nonadmin study_actor must have id2, verified from both ordinary qualification pairs. Scientific runtime must assert id2; null and omission remain unchanged.'
    groups={}
    for group in ['generated','selected','unselected']:
        groups[group]=copy.deepcopy([c for c in old[group] if c['workflow']==wid])
        for c in groups[group]:
            payload=c['producer_payload']
            if payload.get('owner')==1:payload['owner']=2
    return dict(kind='independent_storage_identity_correction_v2',parent_inventory_sha256=sha(source),parent_freeze_commit='215bf7b',cohort='storage_fixture_corrected_v2',workflow=corrected,**groups,ordinary_controls=copy.deepcopy([c for c in old['ordinary_controls'] if c['workflow']==wid]),source_sha256={str(p.relative_to(ROOT)):sha(p) for p in evidence},generator_sha256=sha(Path(__file__)),original_storage_inputs_executed=False,other_workflows_changed=False,new_candidates_added=False,frontend_inspected_before_correction=True,interpretation='Only the assumed ordinary-user primary key changes from 1 to observed 2. Original storage subgroup remains frozen and unexecuted because its fixture assumption was false. Field selection, mutation order, omissions, nulls and all other values are retained. This is a disclosed post-qualification correction, not an untouched holdout.')
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args();target=ROOT/'manifests/independent-paperless-storage-inputs-v2.json';v=build()
    if a.verify:assert json.loads(target.read_text())==v
    else:assert not target.exists();target.write_text(json.dumps(v,indent=2)+'\n')
    print(json.dumps({'selected':len(v['selected']),'ordinary_controls':len(v['ordinary_controls']),'correction':'ordinary owner identity 1 -> 2; no sampled outcomes observed'}))
