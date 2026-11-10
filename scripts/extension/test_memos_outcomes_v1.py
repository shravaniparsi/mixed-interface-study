import copy,unittest
from memos_outcomes_v1 import classify,ordinary_gate
class Outcomes(unittest.TestCase):
    def base(self):
        prefix={'locale':'en','theme':'paper','memoVisibility':'PROTECTED','saveMediaMetadata':False}
        return {'status':'observed','browser_cleanup_confirmed':True,'workflow':'preferences','channel':'api','prefix_status':'accepted','prefix':prefix,'final':{**prefix,'saveMediaMetadata':True},'continuation_status':200}
    def test_complete_api_control(self):self.assertTrue(ordinary_gate(self.base()))
    def test_success_without_edit_is_discrepancy(self):
        o=self.base();o['final']=dict(o['prefix']);self.assertEqual(classify(o)['outcome'],'preservation_or_edit_discrepancy')
    def test_preserved_field_change_is_discrepancy(self):
        o=self.base();o['final']['theme']='default';self.assertFalse(ordinary_gate(o));self.assertEqual(classify(o)['outcome'],'preservation_or_edit_discrepancy')
    def test_unknown_theme_shared_not_server_enum(self):
        o=self.base();o['prefix']['theme']=o['final']['theme']='study-unsupported';r=classify(o);self.assertEqual(r['contract'],[]);self.assertEqual(r['consistency'],['theme:native_option']);self.assertFalse(ordinary_gate(o))
    def test_server_failure_not_rejection(self):
        o=self.base();o['continuation_status']=500;o['final']=dict(o['prefix']);self.assertEqual(classify(o)['outcome'],'unresolved')
    def test_native_block_requires_no_write_and_unchanged_record(self):
        o=self.base();o.update(channel='ui',native_disabled=True,native_requests=[]);self.assertEqual(classify(o)['outcome'],'unresolved');o['final']=dict(o['prefix']);self.assertEqual(classify(o)['outcome'],'blocked_native_control')
    def test_decode_failure_remains_measurement_error(self):
        o=self.base();o.update(channel='ui',native_requests=[{'status':200,'decode_error':'unknown field'}]);self.assertTrue(classify(o)['measurement_error']);self.assertEqual(classify(o)['outcome'],'unresolved')
if __name__=='__main__':unittest.main()
