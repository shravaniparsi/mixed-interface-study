"""Deterministic pilot inputs and actual OpenAPI 3.0 schema predictions, no app calls."""
import copy,hashlib,json,pathlib
from openapi_schema_validator import OAS30Validator
from referencing import Registry,Resource
from referencing.jsonschema import DRAFT4
ROOT=pathlib.Path(__file__).resolve().parents[2]
SCHEMA=pathlib.Path(__file__).with_name('fixtures')/'original.openapi.json'
def validator():
 document=json.loads(SCHEMA.read_text());assert document['openapi']=='3.0.3'
 schema=document['paths']['/paste']['post']['requestBody']['content']['application/json']['schema']
 registry=Registry().with_resource('urn:pastefy:original',Resource.from_contents(document,default_specification=DRAFT4))
 return OAS30Validator({'$ref':'urn:pastefy:original'+schema['$ref']},registry=registry)
def cases():
 ordinary=json.loads((ROOT/'manifests/fresh-session-pastefy-ordinary-input-v1.json').read_text())['producer']
 edits={'title':'study-note-edited','content':'Disposable revised study text.'}
 rows=[]
 # Ordinary controls cover each target/continuation pair before altered states.
 for target in ['content','title']:
  rows.append(dict(id='ordinary-'+target,target=target,mutation='ordinary',input=copy.deepcopy(ordinary)))
 for target in ['content','title']:
  for mutation in ['omit','null']:
   payload=copy.deepcopy(ordinary)
   if mutation=='omit':del payload[target]
   else:payload[target]=None
   rows.append(dict(id=target+'-'+mutation,target=target,mutation=mutation,input=payload))
 v=validator()
 for row in rows:
  unrelated=next(field for field in ['content','title'] if field!=row['target'])
  errors=sorted(v.iter_errors(row['input']),key=lambda e:(str(list(e.path)),e.message))
  row.update(continuation=dict(field=unrelated,value=edits[unrelated]),repair={row['target']:ordinary[row['target']]},sham={},schema_prediction=dict(target='original_creation_request_schema_conformance',valid=not errors,errors=[dict(path=list(e.path),keyword=e.validator,message=e.message) for e in errors]))
 return dict(phase='development_pilot_inputs_and_schema_predictions_frozen_no_dispatch',repository='interaapps/pastefy',revision='caf35d8f279e2e1386a066753f2d644a0ba79507',schema_path='docs/openapi.json',schema_sha256=hashlib.sha256(SCHEMA.read_bytes()).hexdigest(),schema_dialect='OpenAPI 3.0.3 Schema Object; OAS30Validator 0.6.3; original internal refs resolved offline',cases=rows,independent_application_evaluation=False,independently_authored_inputs=False,scientific_outcomes_collected=False)
if __name__=='__main__':print(json.dumps(cases(),indent=2))
