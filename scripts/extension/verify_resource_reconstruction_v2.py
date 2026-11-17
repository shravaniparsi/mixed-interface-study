"""Verify retained reconstruction evidence without reexecuting Angular."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RESULT=ROOT/'results/petclinic-resource-reconstruction-v2'
def main():
    x=json.loads((RESULT/'measurement.json').read_text());execution=json.loads((RESULT/'execution.json').read_text())
    assert execution['freeze']=='03b7abb'
    assert x['node']=='v22.22.3' and x['angular']=='22.2.3' and x['typescript']=='6.0.3'
    assert [r['mode'] for r in x['rows']]==['ordinary','omitted','null']
    fields=['firstName','lastName','address','city','telephone']
    qualifies=not x['errors']
    for row in x['rows']:
        qualifies &= row['status']=='reconstructed' and row.get('projection_matches') is True
        qualifies &= row.get('transfer_state_empty_before') is True and row.get('transfer_state_empty_after') is True
        if row['status']!='reconstructed':continue
        assert row['request']==dict(method='GET',url='http://localhost:9966/petclinic/api/owners/7')
        assert row['resource_value']==row['response']
        assert row['model']==row['projected']['model']
        assert set(row['model'])==set(fields)
        assert row['before']['has_value'] is False and row['before']['resource_status']=='loading'
        assert row['before']['model']=={f:'' for f in fields}
        if row['mode']=='omitted':assert 'address' not in row['response'] and row['model']['address']==''
        if row['mode']=='null':assert row['response']['address'] is None and row['model']['address'] is None
        if row['validation']['status']=='error':assert row['validation']['error'] and row['validation']['stack']
    summary=dict(planned=3,reconstructed=sum(r['status']=='reconstructed' for r in x['rows']),reconstruction_qualified=bool(qualifies),validation_measured=sum(r.get('validation',{}).get('status')=='measured' for r in x['rows']),validation_errors=sum(r.get('validation',{}).get('status')=='error' for r in x['rows']),complete_run_without_errors=execution['returncode']==0 and not x['errors'],transport='Angular HttpClientTestingBackend, no live server',independent_scientific_cases=0)
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
