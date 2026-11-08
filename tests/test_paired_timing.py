import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from validate_realworld_paired_controls import timeline

class PairedTimingTests(unittest.TestCase):
    def test_adjacent_spans_cover_total(self):
        timeline([{'start_s':0,'end_s':1},{'start_s':1,'end_s':3}],3)
    def test_overlap_or_gap_is_not_credited(self):
        for start in (.5,1.5):
            with self.assertRaises(ValueError):timeline([{'start_s':0,'end_s':1},{'start_s':start,'end_s':3}],3)
    def test_nonfinite_or_negative_interval_rejected(self):
        for end in (float('nan'),float('inf'),-1):
            with self.assertRaises(ValueError):timeline([{'start_s':0,'end_s':end}],end)
    def test_missing_spans_or_incorrect_total_rejected(self):
        with self.assertRaises(ValueError):timeline([],0)
        with self.assertRaises(ValueError):timeline([{'start_s':0,'end_s':1}],2)
