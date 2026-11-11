#!/usr/bin/env python3
"""Retain raw ordinary-control metadata rewriting without assigning harmful semantics."""
import json,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def build():
    archive=ROOT/'results/independent-paperless-custom-controls-v1-ci-43072847302';rows=[];sources={}
    for p in sorted(archive.glob('*/pair/report.json')):
        report=json.loads(p.read_text());assert report['cleanup_confirmed'] and report['status']=='incomplete';row={'unit':report['unit']['id'],'branch_order':report['unit']['branch_order'],'channels':{}};sources[str(p.relative_to(ROOT))]=sha(p)
        for channel in ['api','ui']:
            q=p.parent/channel/'observation.json';o=json.loads(q.read_text());sources[str(q.relative_to(ROOT))]=sha(q);requests=o['requests'];made=[x for x in requests if x['method']=='POST'];assert len(made)==1 and made[0]['status']==201 and made[0]['body']=={'name':'Ordinary custom field','data_type':'string','extra_data':{}}
            path='/api/custom_fields/'+str(made[0]['response']['id'])+'/';reads=[x for x in requests if x['method']=='GET' and x['path']==path];assert len(reads)==2 and all(x['status']==200 for x in reads)
            before,after=[x['response'] for x in reads];assert before['extra_data']=={};assert before['data_type']==after['data_type']=='string';assert before['name']=='Ordinary custom field' and after['name']=='Edited ordinary name'
            expected_extra={} if channel=='api' else {'select_options':[],'default_currency':None};assert after['extra_data']==expected_extra
            assert {k:v for k,v in before.items() if k not in ['name','extra_data']}=={k:v for k,v in after.items() if k not in ['name','extra_data']}
            edits=[x for x in requests if x['method']=='PUT'];assert len(edits)==1 and edits[0]['channel']==channel and edits[0]['status']==200 and edits[0]['body']['name']=='Edited ordinary name' and edits[0]['body']['extra_data']==expected_extra
            assert o['browser_cleanup_confirmed'];row['channels'][channel]={'write_status':200,'extra_data_before':{},'extra_data_after':expected_extra,'requested_rename_persisted':True}
        rows.append(row)
    assert len(rows)==2
    return dict(kind='independent_custom_field_eligibility_exclusion_v1',workflow='paperless.custom_field',dispatch_attempts=1,ordinary_pairs=rows,selected_inputs_unexecuted=11,input_payload_changed=False,natural_defects_confirmed=0,reason='Fixed ordinary native control does not preserve exact metadata: both native renames add empty select options and null default currency, whereas both API renames preserve the empty object. No sampled input is eligible under the registered strict control.',interpretation='Observed transformation agrees with inspected form initialization, but source behavior alone establishes neither harmful semantics nor a requirement-backed defect. Retain as a qualification observation, not a scientific native-only detection. No fresh-final editor snapshot was reached because the strict readback assertion failed; this limitation is retained.',source_sha256=sources)
if __name__=='__main__':
    import argparse
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args();target=ROOT/'manifests/independent-paperless-custom-exclusion-v1.json';v=build()
    if a.verify:assert json.loads(target.read_text())==v
    else:assert not target.exists();target.write_text(json.dumps(v,indent=2)+'\n')
    print(json.dumps({'ordinary_pairs':len(v['ordinary_pairs']),'selected_inputs_unexecuted':11,'confirmed_defects':0}))
