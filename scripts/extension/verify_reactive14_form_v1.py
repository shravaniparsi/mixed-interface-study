"""Recompute comparisons against frozen expectations without rerunning Angular."""
import json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
RESULT=ROOT/'results/reactive14-form-measurement-v1'
def main():
    x=json.loads((RESULT/'measurement.json').read_text());expected=json.loads((RESULT/'expected.json').read_text());execution=json.loads((RESULT/'execution.json').read_text())
    assert execution['freeze']=='2ba3140' and x['node']=='v22.22.3' and x['angular']=='14.2.0' and x['typescript']=='6.0.3'
    evidence=json.loads((ROOT/'manifests/development-form-source-screen-v1.json').read_text())['rows'][0]
    assert x['source_sha256']==evidence['sha256']
    assert len(x['rows'])==len(expected['rows'])==6
    differences=[]
    for row,e in zip(x['rows'],expected['rows']):
        assert row['mode']==e['mode']
        bad=[k for k,v in e.items() if row.get(k)!=v]
        if row['status']!='measured' or bad:differences.append(dict(mode=row['mode'],status=row['status'],different_fields=bad))
    result=dict(planned=6,measured=sum(r['status']=='measured' for r in x['rows']),differences=differences,errors=x['errors'],qualified=not differences and not x['errors'])
    assert result==json.loads((RESULT/'comparison.json').read_text())
    print(json.dumps(result,indent=2))
if __name__=='__main__':main()
