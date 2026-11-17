"""Generate preregistered engineering predictions, optionally compare retained rows."""
import json, sys
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from mixed_interface.angular_rule_inventory import inventory
from mixed_interface.angular_string_lowering import lower
from mixed_interface.constraint_transfer import evaluate
source="""import {required, minLength, maxLength, schema} from '@angular/forms/signals';
export interface Model {
  name: string;
}
export const testSchema = schema<Model>(path => {
  required(path.name);
  minLength(path.name, 2);
  maxLength(path.name, 2);
});
"""
templates=lower(source,inventory(source,'synthetic-runtime-grid'),'22.2.3')['templates']
cases=[('missing',{}),('undefined',{}),('null',{'name':None}),('empty',{'name':''}),('space',{'name':' '}),('letter',{'name':'A'}),('astral',{'name':'😀'}),('three',{'name':'ABC'})]
scope=dict(revision='synthetic',operation='validate',actor='test',lifecycle='form')
expected=[]
for t in templates:
    for inactive in [False,True]:
        for name,document in cases:
            rule=dict(rule_id='grid',source_evidence='synthetic source',conflicting_evidence=False,scope=scope,
                mapping=dict(status='known',evidence='synthetic identity',path=['name'],transform='identity'),
                guards=[dict(path=['active'],equals=True)],observation_point='model',predicate=t['predicate'],value_policy=t['value_policy'])
            verdict=evaluate(rule,dict(context=scope,point='model',complete=True,document=dict(document,active=not inactive)))
            errors=[t['validator']] if verdict['verdict']=='violated' else []
            expected.append(dict(validator=t['validator'],inactive=inactive,input=name,prediction=verdict,disabled=inactive,valid=not errors,error_kinds=errors))
if len(sys.argv)==1:
    print(json.dumps(dict(rows=expected,undefined_representation='Missing in Python expectation only; separate actual JS input'),indent=2))
else:
    actual=json.loads(Path(sys.argv[1]).read_text()); rows=actual['rows']
    assert len(rows)==48 and len(expected)==48
    differences=[]
    for e,a in zip(expected,rows):
        assert all(e[k]==a[k] for k in ['validator','inactive','input'])
        bad=[k for k in ['disabled','valid','error_kinds'] if a.get(k)!=e[k]]
        if a['status']!='measured' or bad:differences.append(dict(validator=e['validator'],inactive=e['inactive'],input=e['input'],status=a['status'],different_fields=bad))
    result=dict(planned=48,measured=sum(a['status']=='measured' for a in rows),differences=differences,errors=actual['errors'],qualified=not differences and not actual['errors'])
    print(json.dumps(result,indent=2))
