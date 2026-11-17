#!/usr/bin/env python3
"""Package already measured development confirmation evidence; no new replay."""
import argparse,hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2];sys.path.insert(0,str(ROOT/'src'))
from mixed_interface.shared_reconstruction import digest,package_shared_evidence
SOURCE=ROOT/'results/development-confirmation-reconstruction-v1/measurement.json'
OUT=ROOT/'manifests/development-shared-evidence-v1.json'
def build():
    raw=SOURCE.read_bytes();m=json.loads(raw)
    closed=json.loads((ROOT/'manifests/development-confirmation-reconstruction-v1.json').read_text())
    assert hashlib.sha256(raw).hexdigest()==closed['measurement_sha256']
    result=[]
    for row in m['rows']:
        obs={'target':'submit_decision','point':'candidate_api_projection',
             'context':dict(revision='29f5a77069bee0163e3cfebbb6fd5969f23160a1',operation='register',actor='authored_development_actor',lifecycle='isolated_source_slice_reset'),
             'document':row['candidate_api_projection']}
        fact=dict(id='confirmation.value',status='known',value=row['controls']['confirmPassword']['value'],
                  observation_sha256=digest(obs),origin='observed_frontend',
                  evidence=str(SOURCE.relative_to(ROOT))+'#'+row['id']+'/controls/confirmPassword/value')
        result.append({'id':row['id'],'api_projection_only':package_shared_evidence(obs,['confirmation.value'],[]),
                       'with_recorded_confirmation':package_shared_evidence(obs,['confirmation.value'],[fact])})
    return dict(kind='development_shared_evidence_packaging',measurement_sha256=hashlib.sha256(raw).hexdigest(),
        scope='confirmation_requirement_only_not_complete_workflow_reconstruction',rows=result,
        new_runtime_executions=0,independent_evaluation_cases=0,method_consumers_integrated=False)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');a=p.parse_args();text=json.dumps(build(),indent=2)+'\n'
    if a.verify:assert OUT.read_text()==text;print('Shared records reproduce the closed confirmation evidence')
    else:OUT.write_text(text)
