from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from audit_quartz_form_measurement_v1 import measurement_issue

class MeasurementAuditTests(unittest.TestCase):
    def attempt(self,number):
        return next((ROOT/'results/primary-initial-ci-42780444191').glob('*'+number+'*/primary-unit-v1/*candidate-r1'))
    def test_nonempty_string_map_cannot_receive_defect_credit(self):
        issue=measurement_issue(self.attempt('067'))
        self.assertEqual(issue['kind'],'quartz_dynamic_name_selector_measurement_invalid')
        self.assertTrue(any('ordinary value' in x['native_preview'] for x in issue['affected_form_measurements']))
    def test_blank_key_still_affected_even_when_preview_normalizes_it_away(self):
        self.assertIsNotNone(measurement_issue(self.attempt('058')))
    def test_empty_map_control_not_marked_affected(self):
        self.assertIsNone(measurement_issue(self.attempt('051')))
