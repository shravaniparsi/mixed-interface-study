"""Audit retained replay structure/provenance, not application correctness."""
import hashlib,json
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RESULT=ROOT/'results/petclinic-original-schema-replay-v1'
def main():
    x=json.loads((RESULT/'measurement.json').read_text())
    execution=json.loads((RESULT/'execution.json').read_text())
    assert execution['freeze']=='a5d9871'
    assert x['node']=='v22.22.3' and x['angular']=='22.2.3' and x['typescript']=='6.0.3'
    assert x['original_schemas_loaded']==['owner','pet','visit']
    inventory=json.loads((ROOT/'manifests/petclinic-source-rule-inventory-v1.json').read_text())
    expected={Path(s['path']).name:s['sha256'] for s in inventory['sources'] if s['path'].endswith('-form.ts')}
    expected['form-utils.ts']=json.loads((RESULT/'helper-source.json').read_text())['sha256']
    assert {s['file']:s['sha256'] for s in x['sources']}==expected
    assert len(x['compiled'])==4
    assert all(len(c['sha256'])==64 for c in x['compiled'])
    keys=[(s,m) for s in ['owner','pet','visit'] for m in ['ordinary','all_empty','selected_null','selected_omitted']]
    keys += [('owner','special_address'),('owner','special_firstName'),('pet','special_name'),('visit','special_description')]
    assert [(r['schema'],r['mode']) for r in x['rows']]==keys
    for row in x['rows']:
        assert row['status'] in ['measured','error','not_run']
        if row['status']=='measured':
            assert type(row['root_valid']) is bool
            assert row['root_valid']==(not row['root_error_kinds'])
        if row['status']=='error':assert row['error'] and row['stack'] and row['phase']
    controls=[r for r in x['rows'] if r['mode']=='ordinary']
    basic=not x['errors'] and all(r['status']=='measured' and r['root_valid'] for r in controls)
    summary=dict(kind='development_replay_summary',planned=len(keys),statuses=dict(Counter(r['status'] for r in x['rows'])),ordinary_controls=len(controls),basic_adapter_usable=basic,
                 complete_schedule_without_errors=not x['errors'] and all(r['status']=='measured' for r in x['rows']),
                 omitted_field_rows=[dict(schema=r['schema'],status=r['status'],root_valid=r.get('root_valid'),absent_fields=[f['field'] for f in r.get('fields',[]) if not f['materialized']]) for r in x['rows'] if r['mode']=='selected_omitted'],
                 independent_scientific_cases=0,api_or_browser_runs=0)
    print(json.dumps(summary,indent=2))
if __name__=='__main__':main()
