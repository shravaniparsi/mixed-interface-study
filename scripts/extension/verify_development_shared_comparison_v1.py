#!/usr/bin/env python3
import argparse,collections,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from mixed_interface.shared_reconstruction import digest
S=ROOT/'manifests/development-shared-comparison-schedule-v1.json'
M=ROOT/'results/development-shared-comparison-v1/measurement.json'
OUT=ROOT/'manifests/development-shared-comparison-v1.json'
def build():
    raw=S.read_bytes();s=json.loads(raw);data=M.read_bytes();m=json.loads(data)
    assert hashlib.sha256(raw).hexdigest()==m['schedule_sha256'] and not m['errors']
    assert (m['node'],m['typescript'],m['angular'])==('v22.22.3','6.0.3','14.2.0')
    prior=json.loads((ROOT/'manifests/development-confirmation-reconstruction-v1.json').read_text())
    assert m['source_sha256']==prior['source_sha256'] and m['method_sha256']==prior['method_sha256']
    assert m['manual_conditional_source_bound'] is True
    rows={r['id']:r for r in m['rows']};assert len(rows)==len(m['rows'])==len(s['rows'])==6
    for case in s['rows']:
        row=rows[case['id']];assert row['status']=='measured'
        package=dict(case['shared']);package_hash=package.pop('shared_input_sha256')
        assert digest(package)==package_hash==row['shared_input_sha256']
        for arm in ['C','D']:
            assert row[arm]['shared_input_sha256']==package_hash
            assert row[arm]['verdict']==case['expected']
        if case['expected']=='unknown':
            assert package['unresolved'] and not package['evidence_complete_for_declared_requirements']
            assert row['C']['reason']==row['D']['reason']=='missing_shared_context'
        else:
            assert not package['unresolved']
            payloads=row['D']['captured_payloads']
            assert len(payloads)==(1 if case['expected']=='would_emit' else 0)
            assert all(payload==package['observation']['document'] for payload in payloads)
    return dict(kind='closed_shared_input_integration',freeze='8a1b0e7',measurement_sha256=hashlib.sha256(data).hexdigest(),
        schedule_sha256=m['schedule_sha256'],cases=6,agreement=6,errors=0,
        verdict_counts={arm:dict(collections.Counter(r[arm]['verdict'] for r in m['rows'])) for arm in ['C','D']},
        shared_setup_seconds=m['shared_setup_seconds'],total_seconds=m['elapsed_seconds'],
        conditional_method='manually_specified_source_bound_guard_not_automatic_inference',
        target='direct_submit_method_transport_call_reachability',
        independent_evaluation_cases=0,server_requests=0,comparative_advantage_established=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args();text=json.dumps(build(),indent=2)+'\n'
    if a.verify:assert OUT.read_text()==text;print('Six paired rows retain identical shared inputs and all unknowns')
    else:OUT.write_text(text)
