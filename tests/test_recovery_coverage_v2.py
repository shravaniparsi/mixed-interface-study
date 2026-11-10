from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from build_experiment_completion_v2 import combine_categories
class CoverageTests(unittest.TestCase):
    def test_disjoint_complete_case_coverage(self):
        self.assertEqual(combine_categories({'first':'clean'},{'recovered':'unresolved'},['first','recovered']),{'first':'clean','recovered':'unresolved'})
    def test_duplicate_case_cannot_inflate_coverage(self):
        with self.assertRaisesRegex(ValueError,'twice'):combine_categories({'same':'clean'},{'same':'clean'},['same'])
    def test_missing_case_cannot_complete(self):
        with self.assertRaisesRegex(ValueError,'incomplete'):combine_categories({'first':'clean'},{},['first','missing'])
