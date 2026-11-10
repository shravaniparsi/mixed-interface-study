"""A clean-looking attempt cannot override a failed whole-unit acceptance check."""
from pathlib import Path
from unittest.mock import patch
import sys,tempfile,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import test_primary_batches_v1 as fixtures
import prepare_primary_followups_v1 as p

class FollowupAcceptanceTests(unittest.TestCase):
    def test_globally_unqualified_unit_cannot_authorize_a_repeat(self):
        fixtures.PrimaryBatchTests.setUpClass();f=fixtures.PrimaryBatchTests()
        unit=next(u for u in f.plan['initial_batches'] if len(u['jobs'])==2);initial=f.initial(unit['batch_id'])
        collection={'mode':'initial','freeze_sha256':p.sha(p.FREEZE),'records':initial,
                    'verification':{k:{'qualified_observations':k!=unit['batch_id']} for k in initial}}
        with tempfile.TemporaryDirectory() as tmp,patch.object(p,'verify',return_value=collection),patch.object(p,'ROOT',Path(tmp)):
            with self.assertRaisesRegex(ValueError,'globally unqualified initial'):p.prepare(Path(tmp)/'synthetic.json',2)
