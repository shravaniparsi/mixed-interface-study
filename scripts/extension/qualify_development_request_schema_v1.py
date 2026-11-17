#!/usr/bin/env python3
import hashlib,importlib.metadata,json,platform,time
from pathlib import Path
from openapi_schema_validator import OAS30WriteValidator
from referencing import Registry
from referencing.jsonschema import DRAFT4

ROOT=Path(__file__).resolve().parents[2]
SPEC=ROOT/'results/development-spec-startup-v2-ci-44089249914/openapi.body'
SCHEDULE=ROOT/'manifests/development-request-schema-schedule-v1.json'
OUT=ROOT/'results/development-request-schema-qualification-v1'
def main():
    assert not OUT.exists(), 'Closed qualification cannot be overwritten'
    raw=SPEC.read_bytes();scheduled=SCHEDULE.read_bytes();schedule=json.loads(scheduled)
    assert hashlib.sha256(raw).hexdigest()==schedule['spec_sha256']
    doc=json.loads(raw)
    versions={k:importlib.metadata.version(k) for k in ['openapi-schema-validator','jsonschema','referencing']}
    assert versions=={'openapi-schema-validator':'0.6.3','jsonschema':'4.26.0','referencing':'0.36.2'}
    def reject_retrieve(uri):raise RuntimeError('External reference retrieval forbidden: '+uri)
    registry=Registry(retrieve=reject_retrieve).with_resource('urn:study:spec',DRAFT4.create_resource(doc))
    rows=[];start=time.monotonic()
    for case in schedule['cases']:
        row={'id':case['id'],'expected':case['expected']}
        try:
            op=doc['paths'][case['path']][case['method']]
            schema=op['requestBody']['content']['application/json']['schema']
            assert set(schema)=={'$ref'} and schema['$ref'].startswith('#/')
            validator=OAS30WriteValidator({'$ref':'urn:study:spec'+schema['$ref']},registry=registry,format_checker=OAS30WriteValidator.FORMAT_CHECKER)
            errors=list(validator.iter_errors(case['body']))
            row['verdict']='violated' if errors else 'satisfied'
            row['errors']=[dict(validator=e.validator,path=list(e.path),schema_path=list(e.schema_path),message=e.message) for e in errors]
        except Exception as error:row.update(verdict='code_error',error_type=type(error).__name__,message=str(error))
        row['matches_expected']=row['verdict']==case['expected'];rows.append(row)
    result=dict(kind='authored_development_request_schema_qualification',spec_sha256=hashlib.sha256(raw).hexdigest(),schedule_sha256=hashlib.sha256(scheduled).hexdigest(),versions=versions,python=platform.python_version(),elapsed_seconds=time.monotonic()-start,rows=rows,independent_evaluation_cases=0,application_requests=0,logical_mining_baseline_qualified=False)
    OUT.mkdir();(OUT/'measurement.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps(dict(cases=len(rows),matches=sum(r['matches_expected'] for r in rows),code_errors=sum(r['verdict']=='code_error' for r in rows))))
if __name__=='__main__':main()
