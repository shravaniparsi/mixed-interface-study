#!/usr/bin/env python3
import hashlib,importlib.metadata,json
from pathlib import Path
from openapi_schema_validator import OAS30WriteValidator
from referencing import Registry
from referencing.jsonschema import DRAFT4
ROOT=Path(__file__).resolve().parents[2]
out=ROOT/'results/development-fixture-schema-v1'
assert not out.exists(), 'Closed comparison'
out.mkdir()
raw=(ROOT/'results/development-spec-startup-v2-ci-44089249914/openapi.body').read_bytes()
assert hashlib.sha256(raw).hexdigest()=='2c8546ccc3d04eb7166aec4a10aea1434a89a25ea3f78188bd3df5d0b8231af1'
doc=json.loads(raw)
versions={k:importlib.metadata.version(k) for k in ['openapi-schema-validator','jsonschema','referencing']}
assert versions=={'openapi-schema-validator':'0.6.3','jsonschema':'4.26.0','referencing':'0.36.2'}
def reject(uri):raise RuntimeError('External reference: '+uri)
registry=Registry(retrieve=reject).with_resource('urn:study:spec',DRAFT4.create_resource(doc))
schema=doc['paths']['/api/register']['post']['requestBody']['content']['application/json']['schema']
validator=OAS30WriteValidator({'$ref':'urn:study:spec'+schema['$ref']},registry=registry,format_checker=OAS30WriteValidator.FORMAT_CHECKER)
source=(ROOT/'results/development-test-serialization-v1/measurement.json').read_bytes()
rows=[]
for row in json.loads(source)['rows']:
    r={'id':row['id'],'body_sha256':row['body_sha256']}
    try:
        errors=list(validator.iter_errors(row['body']))
        r.update(verdict='violated' if errors else 'satisfied',errors=[{'validator':e.validator,'path':list(e.path),'message':e.message} for e in errors])
    except Exception as e:r.update(verdict='code_error',error=str(e))
    rows.append(r)
result={'kind':'original_fixture_spec_conformance','input_sha256':hashlib.sha256(source).hexdigest(),'versions':versions,'rows':rows,'application_requests':0,'independent_evaluation_cases':0}
(out/'measurement.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result,indent=2))
