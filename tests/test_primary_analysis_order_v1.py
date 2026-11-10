"""Filesystem enumeration must not change a reconstructed research report."""
from pathlib import Path
import sys,unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from analyze_primary_units_v1 import analyze
from primary_preflight_v1 import read
class AnalysisOrderTests(unittest.TestCase):
    def test_reversed_artifact_enumeration_matches_registered_report(self):
        original=Path.glob
        def reversed_glob(path,pattern):
            found=original(path,pattern)
            return iter(reversed(list(found))) if pattern in ('*/requested-unit.json','*/summary.json') else found
        with patch.object(Path,'glob',reversed_glob):
            result=analyze(ROOT/'manifests/primary-initial-runtime-v1.json',ROOT/'manifests/primary-repeat2-runtime-v1.json',ROOT/'manifests/primary-repeat3-runtime-v1.json')
        self.assertEqual(result,read(ROOT/'manifests/primary-results-v1.json'))
