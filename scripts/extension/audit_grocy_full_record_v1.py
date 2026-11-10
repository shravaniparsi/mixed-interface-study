#!/usr/bin/env python3
"""Reconstruct full persisted-field changes in already-retained ordinary controls."""
import hashlib,json,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def read(p):return json.loads(p.read_text())
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build():
    sources=[('results/grocy-extension-controls-v1-ci-42886883102','manifests/grocy-extension-controls-v1.json'),('results/grocy-extension-controls-v2-ci-42889952089','manifests/grocy-extension-controls-v2.json')]
    records=[]
    for folder,registry in sources:
        reg=read(ROOT/registry);flows={w['id']:w for w in reg['workflows']}
        for report in sorted((ROOT/folder).rglob('report.json')):
            pair=read(report)
            if pair['status']!='ordinary_pair_passed':continue
            assert pair['cleanup_confirmed'] and pair['registry_sha256']==sha(ROOT/registry)
            for channel in ['api','ui']:
                p=report.parent/channel/'observation.json';o=read(p);w=flows[o['workflow']];path=w['collection']+'/'+str(o['resource_id'])
                assert pair['files_sha256'][channel+'/observation.json']==sha(p)
                reads=[q for q in o['requests'] if q['method']=='GET' and q['path']==path]
                assert len(reads)==2 and all(q['status']==200 for q in reads)
                before,after=[q['response'] for q in reads];assert set(before)==set(after)
                changes={k:{'before':before[k],'after':after[k]} for k in before if before[k]!=after[k]}
                assert after[w['edit_field']]==w['edit_value']
                unintended={k:v for k,v in changes.items() if k!=w['edit_field']}
                records.append({'unit':pair['unit']['id'],'workflow':w['id'],'channel':channel,'source':str(p.relative_to(ROOT)),'source_sha256':sha(p),'registered_edit_field':w['edit_field'],'all_persisted_field_changes':changes,'additional_changes':unintended})
    assert len(records)==12
    return {'kind':'exploratory_grocy_ordinary_full_record_audit_v1','cohort':'ordinary_qualification_posthoc_full_record_audit','records':records,'branches_with_additional_changes':sum(bool(x['additional_changes']) for x in records),'interpretation':'Post-hoc audit of full retained records, outside the original ten-field product control assertion. Not a prospectively registered boundary result or a requirement-backed defect. Preserve exposure when constructing the finite inventory.','next_action':'Qualify full-field preservation and full-record API continuation; separately register replication and counterfactual tests for the observed nullable-energy behavior.'}
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args();v=build();target=ROOT/'manifests/grocy-exploratory-full-record-audit-v1.json'
    if a.verify:assert read(target)==v
    else:
        assert not target.exists();target.write_text(json.dumps(v,indent=2)+'\n')
    print(json.dumps({'branches':len(v['records']),'branches_with_additional_changes':v['branches_with_additional_changes']}))
