"""Engineering checks of denominator/abstention behavior; no research samples."""
import copy
import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2] / 'src'))
from mixed_interface.oracle_acquisition import score, normalize_rbctest_status

class ScoringTests(unittest.TestCase):
    def setUp(self):
        self.frame={'methods':['a','b'],'cases':[
            dict(case_id=str(i),project_id='p1' if i<3 else 'p2',workflow_id='w',constraint_id='c',
                 label=label,label_evidence='synthetic unit-test expectation')
            for i,label in enumerate(['violated','violated','satisfied','satisfied','unresolved'])]}
        self.predictions=[dict(method=m,case_id=str(i),verdict=v) for m,values in
            [('a',['violated','unknown','violated','code_error','violated']),
             ('b',['violated','satisfied','satisfied','satisfied','not_run'])]
            for i,v in enumerate(values)]

    def test_baseline_labels_preserve_unknown_and_errors(self):
        self.assertEqual([normalize_rbctest_status(x) for x in ['satisfied','mismatched','unknown','code error']],
                         ['satisfied','violated','unknown','code_error'])
        with self.assertRaises(ValueError): normalize_rbctest_status(None)

    def test_abstention_and_unresolved_are_retained(self):
        r=score(self.frame,self.predictions);a=r['methods']['a']['overall']
        self.assertEqual((a['retained_cases'],a['resolved_cases']),(5,4))
        self.assertEqual(a['precision_on_resolved_alerts'],.5)
        self.assertEqual(a['violation_detection_fraction'],.5)
        self.assertEqual(a['decisive_coverage'],.5)
        self.assertEqual(a['violations_without_decisive_verdict'],1)
        self.assertEqual(a['satisfied_without_decisive_verdict'],1)
        self.assertEqual(a['alerts_on_unresolved_labels'],1)
        self.assertEqual(len(r['paired_verdicts']),5)
        self.assertEqual(r['constraint_clusters'],2)

    def test_dropping_or_duplicating_a_case_rejected(self):
        for rows in [self.predictions[:-1],self.predictions+[self.predictions[0]]]:
            with self.assertRaises(ValueError):score(self.frame,rows)

    def test_all_abstain_does_not_score_perfect(self):
        rows=[dict(p,verdict='unknown') for p in self.predictions]
        a=score(self.frame,rows)['methods']['a']['overall']
        self.assertIsNone(a['precision_on_resolved_alerts'])
        self.assertIsNone(a['accuracy_on_decisive_resolved'])
        self.assertEqual(a['decisive_coverage'],0)
        self.assertEqual(a['violation_detection_fraction'],0)

    def test_missing_label_evidence_rejected(self):
        f=copy.deepcopy(self.frame);f['cases'][0]['label_evidence']=''
        with self.assertRaises(ValueError):score(f,self.predictions)

    def test_invalid_verdict_rejected(self):
        rows=copy.deepcopy(self.predictions);rows[0]['verdict']='pass_by_default'
        with self.assertRaises(ValueError):score(self.frame,rows)

    def test_no_positive_cases_has_undefined_detection_fraction(self):
        f=copy.deepcopy(self.frame)
        for c in f['cases']:c['label']='satisfied'
        a=score(f,self.predictions)['methods']['a']['overall']
        self.assertIsNone(a['violation_detection_fraction'])
        self.assertEqual(a['true_alerts'],0)

if __name__=='__main__':unittest.main()
