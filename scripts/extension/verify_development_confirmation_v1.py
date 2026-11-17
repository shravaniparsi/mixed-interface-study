#!/usr/bin/env python3
import argparse,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
S=ROOT/'manifests/development-confirmation-schedule-v1.json'
M=ROOT/'results/development-confirmation-reconstruction-v1/measurement.json'
OUT=ROOT/'manifests/development-confirmation-reconstruction-v1.json'
def build():
    raw=S.read_bytes();s=json.loads(raw);data=M.read_bytes();m=json.loads(data)
    assert m['schedule_sha256']==hashlib.sha256(raw).hexdigest() and not m['errors']
    assert (m['node'],m['typescript'],m['angular'])==('v22.22.3','6.0.3','14.2.0')
    source=json.loads((ROOT/'manifests/development-form-source-screen-v1.json').read_text())
    assert m['source_sha256']==next(r['sha256'] for r in source['rows'] if r['index']==1)
    rows={r['id']:r for r in m['rows']};assert len(rows)==len(m['rows'])==len(s['rows'])==3
    for case in s['rows']:
        row=rows[case['id']];assert row['status']=='measured'
        for key,value in case['expected'].items():assert row[key]==value
        assert row['save_calls']==len(row['captured_payloads'])
        assert {k:v['value'] for k,v in row['controls'].items()}==case['form']
        expected={k:case['form'][k] for k in ('login','email','password')};expected['langKey']=case['language']
        assert row['candidate_api_projection']==expected
        assert all(payload==expected for payload in row['captured_payloads'])
    assert rows['matching']['candidate_api_projection']==rows['mismatching']['candidate_api_projection']==rows['empty']['candidate_api_projection']
    return dict(kind='closed_development_reconstruction_qualification',freeze='53c5147',
        measurement_sha256=hashlib.sha256(data).hexdigest(),schedule_sha256=m['schedule_sha256'],
        source_sha256=m['source_sha256'],initializer_sha256=m['initializer_sha256'],method_sha256=m['method_sha256'],
        cases=3,matched_expectations=3,errors=0,distinct_candidate_api_projections=1,
        submission_call_counts={k:v['save_calls'] for k,v in rows.items()},
        form_statuses={k:v['form_status'] for k,v in rows.items()},
        interpretation='Full frontend confirmation-dependent behavior is not uniquely determined by these API-mapped fields.',
        elapsed_seconds=m['elapsed_seconds'],server_requests=0,independent_evaluation_cases=0,
        complete_component_runtime=False,conditional_transfer_advantage_established=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args();text=json.dumps(build(),indent=2)+'\n'
    if a.verify:assert OUT.read_text()==text;print('Three original-source states and shared candidate projection verified')
    else:OUT.write_text(text)
