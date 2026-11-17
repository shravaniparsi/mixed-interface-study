#!/usr/bin/env python3
"""Verify closed qualification accounting without executing the validator again."""
import argparse,collections,hashlib,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
S=ROOT/'manifests/development-request-schema-schedule-v1.json'
M=ROOT/'results/development-request-schema-qualification-v1/measurement.json'
O=ROOT/'manifests/development-request-schema-qualification-v1.json'
def build():
    raw=S.read_bytes();schedule=json.loads(raw);data=M.read_bytes();m=json.loads(data)
    assert hashlib.sha256(raw).hexdigest()==m['schedule_sha256']
    assert schedule['spec_sha256']==m['spec_sha256']=='2c8546ccc3d04eb7166aec4a10aea1434a89a25ea3f78188bd3df5d0b8231af1'
    expected={r['id']:r for r in schedule['cases']};assert len(expected)==len(schedule['cases'])==60
    actual={r['id']:r for r in m['rows']};assert len(actual)==len(m['rows'])==60
    assert set(actual)==set(expected)
    for key,row in actual.items():
        assert row['expected']==expected[key]['expected']
        assert row['verdict']==row['expected'] and row['matches_expected'] is True
        assert isinstance(row['errors'],list)
        assert bool(row['errors'])==(row['verdict']=='violated')
    assert m['versions']=={'openapi-schema-validator':'0.6.3','jsonschema':'4.26.0','referencing':'0.36.2'}
    return dict(kind='closed_authored_schema_qualification',freeze='7b10e7a',
        measurement_sha256=hashlib.sha256(data).hexdigest(),schedule_sha256=m['schedule_sha256'],
        spec_sha256=m['spec_sha256'],cases=60,matches=60,code_errors=0,
        verdict_counts=dict(collections.Counter(r['verdict'] for r in m['rows'])),
        by_operation={op:dict(collections.Counter(r['verdict'] for r in m['rows'] if r['id'].startswith(op+':'))) for op in ['register','admin-create','admin-update']},
        qualification_scope='fixed_development_request_schema_cases_in_recorded_python_validator',
        python=m['python'],versions=m['versions'],elapsed_seconds=m['elapsed_seconds'],
        independent_evaluation_cases=0,application_requests=0,logical_mining_baseline_qualified=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args();text=json.dumps(build(),indent=2)+'\n'
    if a.verify:assert O.read_text()==text;print('All 60 frozen rows and schema-derived expectations reconciled')
    else:O.write_text(text)
