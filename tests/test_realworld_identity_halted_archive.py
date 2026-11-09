import json,sys,shutil,tempfile,unittest
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from verify_realworld_identity_halted_archive import reconstruct_halt


class HaltedIdentityArchiveTests(unittest.TestCase):
    def setUp(self):self.archive=ROOT/'results/realworld-identity-halted-ci-20261109'
    def test_halt_reconstructs_without_promoting_unreadable_case(self):
        result=reconstruct_halt(self.archive)
        self.assertTrue(result['verified_halted_ledger']);self.assertFalse(result['campaign_completed'])
        self.assertEqual(result['terminal_sequence'][-1],'missing_evidence')
        self.assertEqual(result['followup_jobs'],0)
        for reads in result['incomplete_case_read_statuses'].values():self.assertEqual(reads['/api/user'],500)
    def test_halted_ledger_cannot_be_relabeled_completed(self):
        with tempfile.TemporaryDirectory() as temp:
            d=Path(temp)/'archive';shutil.copytree(self.archive,d)
            p=d/'campaign.json';state=json.loads(p.read_bytes());state['status']='completed_observations';p.write_text(json.dumps(state))
            with self.assertRaisesRegex(ValueError,'Halted ledger differs'):reconstruct_halt(d)
