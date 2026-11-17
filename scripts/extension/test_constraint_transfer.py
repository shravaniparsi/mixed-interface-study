"""Development falsification cases, not application or scientific observations."""
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / 'src'))
from mixed_interface.constraint_transfer import evaluate

class TransferTests(unittest.TestCase):
    def setUp(self):
        self.rule=dict(rule_id='fixture-only',source_evidence='synthetic test definition',conflicting_evidence=False,
            scope=dict(revision='r1',operation='create',actor='member',lifecycle='draft'),
            mapping=dict(status='known',evidence='synthetic explicit binding',path=['title'],transform='identity'),
            guards=[],observation_point='post_readback',
            value_policy=dict(missing='reject',null='reject',empty='reject'),
            predicate=dict(kind='length',minimum=1,maximum=4,units='unicode_codepoints'))
        self.obs=dict(context=copy.deepcopy(self.rule['scope']),point='post_readback',complete=True,document={'title':'abc'})

    def verdict(self):return evaluate(self.rule,self.obs)['verdict']

    def test_valid_and_invalid_lengths(self):
        self.assertEqual(self.verdict(),'satisfied');self.obs['document']['title']='abcde'
        self.assertEqual(self.verdict(),'violated')

    def test_update_does_not_inherit_create_requiredness(self):
        self.obs['context']['operation']='update';self.obs['document']={}
        result=evaluate(self.rule,self.obs);self.assertEqual(result['verdict'],'unknown');self.assertIs(result['applicable'],False)

    def test_optional_empty_needs_explicit_permission(self):
        self.obs['document']['title']='';self.assertEqual(self.verdict(),'violated')
        self.rule['value_policy']['empty']='allow';self.assertEqual(self.verdict(),'satisfied')

    def test_missing_and_null_are_distinct(self):
        self.rule['value_policy']['missing']='allow';self.obs['document']={};self.assertEqual(self.verdict(),'satisfied')
        self.obs['document']={'title':None};self.assertEqual(self.verdict(),'violated')

    def test_no_invented_default_in_observed_state(self):
        self.rule['mapping']['transform']='default_to_abc';self.obs['document']={}
        self.assertEqual(self.verdict(),'unknown')

    def test_conditional_field_guard(self):
        self.rule['guards']=[dict(path=['enabled'],equals=True)]
        self.assertEqual(self.verdict(),'unknown')
        self.obs['document']['enabled']=False;self.assertFalse(evaluate(self.rule,self.obs)['applicable'])
        self.obs['document']['enabled']=True;self.assertEqual(self.verdict(),'satisfied')

    def test_actor_and_revision_scope(self):
        for key in ('actor','revision','lifecycle'):
            obs=copy.deepcopy(self.obs);obs['context'][key]='other'
            self.assertEqual(evaluate(self.rule,obs)['verdict'],'unknown')

    def test_mapping_conflict_and_incomplete_readback(self):
        for rulekey in ('mapping','conflicting_evidence'):
            r=copy.deepcopy(self.rule)
            if rulekey=='mapping':r['mapping']['status']='unresolved'
            else:r['conflicting_evidence']=True
            self.assertEqual(evaluate(r,self.obs)['verdict'],'unknown')
        self.obs['complete']=False;self.assertEqual(self.verdict(),'unknown')

    def test_known_json_decoding(self):
        self.rule['mapping']['transform']='json_string_decode';self.obs['document']['title']='"abc"'
        self.assertEqual(self.verdict(),'satisfied')
        self.obs['document']['title']='not-json';self.assertEqual(self.verdict(),'unknown')

    def test_length_units_are_not_silently_equated(self):
        self.rule['predicate'].update(minimum=1,maximum=1);self.obs['document']['title']='😀'
        self.assertEqual(self.verdict(),'satisfied')
        self.rule['predicate']['units']='utf16_code_units';self.assertEqual(self.verdict(),'violated')

    def test_boolean_is_not_number_or_enum_integer(self):
        self.obs['document']['title']=True;self.rule['predicate']=dict(kind='numeric_range',minimum=0,maximum=2)
        self.assertEqual(self.verdict(),'unknown')
        self.rule['predicate']=dict(kind='enum',values=[1]);self.assertEqual(self.verdict(),'violated')

    def test_missing_rule_metadata_is_error_not_pass(self):
        del self.rule['scope'];self.assertEqual(self.verdict(),'code_error')

    def test_container_mismatch_is_not_field_omission(self):
        self.rule['mapping']['path']=['nested','title'];self.obs['document']={'nested':None}
        self.assertEqual(self.verdict(),'unknown')

    def test_reversed_bounds_are_configuration_error(self):
        self.rule['predicate'].update(minimum=5,maximum=1)
        self.assertEqual(self.verdict(),'code_error')

    def test_wrong_observation_point_is_unknown(self):
        self.obs['point']='immediate_response';self.assertEqual(self.verdict(),'unknown')

if __name__=='__main__':unittest.main()
