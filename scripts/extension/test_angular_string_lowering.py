import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/'src'))
from mixed_interface.angular_rule_inventory import inventory
from mixed_interface.angular_string_lowering import lower
from mixed_interface.constraint_transfer import evaluate

SOURCE="""import {required, minLength, schema} from '@angular/forms/signals';
export interface Model {
  name: string;
  date: string | null;
}
export const testSchema = schema<Model>(path => {
  required(path.name);
  minLength(path.name, 2);
  required(path.date);
});
"""
class LoweringTests(unittest.TestCase):
    def setUp(self):self.inv=inventory(SOURCE,'synthetic')
    def test_union_is_retained_unresolved(self):
        x=lower(SOURCE,self.inv,'22.2.3');self.assertEqual(len(x['templates']),2)
        self.assertEqual(x['unresolved'][0]['reason'],'non_string_or_union_domain')
        self.assertEqual(x['complete_api_rules'],0)
    def test_unqualified_version_rejected(self):
        with self.assertRaises(ValueError):lower(SOURCE,self.inv,'22.2.2')
    def test_changed_source_rejected(self):
        with self.assertRaises(ValueError):lower(SOURCE+' ',self.inv,'22.2.3')
    def test_optional_length_and_required_are_separate(self):
        templates=lower(SOURCE,self.inv,'22.2.3')['templates'];scope=dict(revision='r',operation='create',actor='a',lifecycle='l')
        for value,expected in [('', ['violated','satisfied']),(' ',['satisfied','violated']),('😀',['satisfied','satisfied'])]:
            results=[]
            for t in templates:
                rule=dict(rule_id='test',source_evidence='fixture',conflicting_evidence=False,scope=scope,
                    mapping=dict(status='known',evidence='fixture',path=['name'],transform='identity'),guards=[],
                    observation_point='fixture',predicate=t['predicate'],value_policy=t['value_policy'])
                results.append(evaluate(rule,dict(context=scope,point='fixture',complete=True,document={'name':value}))['verdict'])
            self.assertEqual(results,expected)

if __name__=='__main__':unittest.main()
