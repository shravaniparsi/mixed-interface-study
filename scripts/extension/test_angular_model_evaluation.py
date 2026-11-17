"""Regression safeguards learned from development; not independent evaluation."""
import copy,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from mixed_interface.angular_rule_inventory import inventory
from mixed_interface.angular_string_lowering import lower
from mixed_interface.angular_model_evaluation import evaluate_model_template,snapshot_sha256
SOURCE="""import {required, schema} from '@angular/forms/signals';
export interface Model {
  name: string;
}
export const testSchema = schema<Model>(path => {
  required(path.name);
});
"""
class ModelTests(unittest.TestCase):
    def setUp(self):
        self.t=lower(SOURCE,inventory(SOURCE,'synthetic'),'22.2.3')['templates'][0]
        self.o=dict(point='frontend_model',complete=True,context=dict(revision='r',operation='edit',actor='member',lifecycle='draft'),document={'name':''})
        self.s=dict(evidence='synthetic fixture',context=copy.deepcopy(self.o['context']),field='name',framework_version='22.2.3',materialized=True,disabled=False,hidden=False,readonly=False)
        self.bind()
    def bind(self):self.s['snapshot_sha256']=snapshot_sha256(self.o['document'])
    def result(self):return evaluate_model_template(self.t,self.o,self.s)
    def test_missing_field_is_not_required_failure(self):
        self.o['document']={};self.bind()
        self.assertEqual(self.result()['verdict'],'unknown')
        self.s['materialized']=False
        self.assertEqual(self.result()['reason'],'field_not_materialized')
        self.assertIs(self.result()['applicable'],False)
    def test_null_and_empty_remain_required_failures(self):
        for value in [None,'']:
            self.o['document']['name']=value;self.bind()
            self.assertEqual(self.result()['verdict'],'violated')
    def test_valid_string(self):
        self.o['document']['name']='A';self.bind();self.assertEqual(self.result()['verdict'],'satisfied')
    def test_unknown_or_stale_field_state_abstains(self):
        for key,value in [('materialized',None),('evidence',''),('snapshot_sha256','stale'),('disabled',None),('field','other')]:
            state=dict(self.s);state[key]=value
            self.assertEqual(evaluate_model_template(self.t,self.o,state)['verdict'],'unknown')
    def test_scope_cannot_be_reused(self):
        self.o['context']['operation']='create';self.assertEqual(self.result()['verdict'],'unknown')
    def test_disabled_invalid_value_is_not_an_alert(self):
        self.s['disabled']=True
        self.assertEqual(self.result()['verdict'],'unknown');self.assertIs(self.result()['applicable'],False)
    def test_hidden_and_readonly_not_claimed_qualified(self):
        for key in ['hidden','readonly']:
            state=dict(self.s);state[key]=True
            self.assertEqual(evaluate_model_template(self.t,self.o,state)['reason'],'activity_mode_not_runtime_qualified')
    def test_api_response_is_not_frontend_model(self):
        self.o['point']='api_response';self.assertEqual(self.result()['verdict'],'unknown')
    def test_non_string_values_not_satisfied_by_presence(self):
        for value in [False,0,[],{}, {'javascript':'undefined'}]:
            self.o['document']['name']=value;self.bind();self.assertEqual(self.result()['verdict'],'unknown')
    def test_no_mutation(self):
        before=copy.deepcopy((self.t,self.o,self.s));self.result();self.assertEqual(before,(self.t,self.o,self.s))
if __name__=='__main__':unittest.main()
