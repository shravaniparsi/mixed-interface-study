"""Verify saved mocked-boundary records, not full application behavior."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]

def main():
    p=ROOT/'results/petclinic-submission-boundary-qualification-v1'
    run=json.loads((p/'execution.json').read_text());assert run['returncode']==0 and run['attempts']==1
    assert run['freeze'].startswith('c33d912')
    data=json.loads((p/'measurement.json').read_text())
    inventory=json.loads((ROOT/'manifests/petclinic-source-rule-inventory-v1.json').read_text())
    for name,sha in data['source_hashes'].items():
        assert sha==next(x['sha256'] for x in inventory['sources'] if x['path'].endswith('/'+name))
    rows=data['rows'];assert len(rows)==6
    assert {(x['route'],x['input_label']) for x in rows}=={(r,i) for r in ('add','edit') for i in ('present','omitted','null')}
    ordinary=dict(firstName='Ana',lastName='Test',address='Street1',city='Rome',telephone='1234567890')
    for row in rows:
        assert 'error' not in row and row['loaded_resource_unchanged'] is True
        original=ordinary.copy()
        if row['input_label']=='omitted':del original['address']
        elif row['input_label']=='null':original['address']=None
        assert row['input']==original
        expected=original.copy()
        if row['route']=='edit' and row['input_label']=='omitted':expected['address']=''
        assert row['model_before_submission']==expected
        assert len(row['requests'])==1 and len(row['navigations'])==1
        request=row['requests'][0];payload=dict(id=None if row['route']=='add' else 7,**expected)
        assert request['body']==payload and json.loads(request['json'])==payload
        assert request['address_present']==('address' in payload)
        assert request['method']==('POST' if row['route']=='add' else 'PUT')
        assert request['url']=='http://isolated.invalid/api/owners'+('' if row['route']=='add' else '/7')
    print('Six saved source-body checks verified; edit omission default retained; no Angular/native/API acceptance qualification.')

if __name__=='__main__':main()
