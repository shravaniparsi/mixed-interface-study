from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from quartz_correction_preflight_v1 import PREPARATION,read,units
from primary_preflight_v1 import PREPARATION as ORIGINAL

class CorrectionPreparationTests(unittest.TestCase):
    def test_all_original_quartz_pairs_preserved_with_fresh_ids(self):
        old=[u for u in read(ORIGINAL)['plan']['initial_batches'] if u['application']=='quartz']
        new=read(PREPARATION)['plan']['initial_batches']
        self.assertEqual(len(new),22)
        self.assertEqual([u['target_pair_id'] for u in new],[u['target_pair_id'] for u in old])
        for before,after in zip(old,new):
            self.assertNotEqual(before['batch_id'],after['batch_id'])
            self.assertEqual([j['runtime']['job'] for j in before['jobs']],[j['runtime']['job'] for j in after['jobs']])
            self.assertTrue(all(j['runtime']['loader']=='quartz_terminal_outcomes_v3' for j in after['jobs']))
    def test_smoke_includes_nonempty_representation_twice(self):
        jobs=units('smoke')[0]['jobs'];self.assertEqual(len(jobs),4)
        self.assertEqual(sum('nonempty_string' in j['attempt_id'] for j in jobs),2)
