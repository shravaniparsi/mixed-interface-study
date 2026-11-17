"""Check preserved predictions and source provenance; no framework reexecution."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RESULT=ROOT/'results/development-http-serialization-v2'
def main():
    original=ROOT/'results/development-http-serialization-v1/expected.json'
    assert original.read_bytes()==(RESULT/'expected.json').read_bytes()
    x=json.loads((RESULT/'measurement.json').read_text());expected=json.loads((RESULT/'expected.json').read_text());execution=json.loads((RESULT/'execution.json').read_text())
    assert execution['freeze']=='40b061a' and x['node']=='v22.22.3' and x['angular']=='14.2.0' and x['typescript']=='6.0.3'
    sources={r['path']:r['sha256'] for name in ['development-service-source-screen-v1.json','development-http-setup-source-v1.json'] for r in json.loads((ROOT/'manifests'/name).read_text())['rows']}
    assert all(sources[r['path']]==r['sha256'] for r in x['sources'])
    assert len(x['rows'])==len(expected['rows'])==9;differences=[]
    for r,e in zip(x['rows'],expected['rows']):
        assert (r['route'],r['mode'])==(e['route'],e['mode'])
        bad=[k for k,v in e.items() if r.get(k)!=v]
        if r['status']!='measured' or bad:differences.append(dict(route=r['route'],mode=r['mode'],status=r['status'],different_fields=bad))
    comparison=dict(planned=9,measured=sum(r['status']=='measured' for r in x['rows']),differences=differences,errors=x['errors'],qualified=not differences and not x['errors'])
    assert comparison==json.loads((RESULT/'comparison.json').read_text());print(json.dumps(comparison,indent=2))
if __name__=='__main__':main()
