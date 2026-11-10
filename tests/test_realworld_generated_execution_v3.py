"""Independent scheduler reconstruction rejects altered or post-halt observations."""
from copy import deepcopy
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from realworld_generated_mutations_v3 import drive
from validate_realworld_generated_mutations_v3 import reconstruct_schedule
from test_realworld_generated_mutations_v3 import outcome

class ExecutionReconstructionTests(unittest.TestCase):
    def records(self,halt=None):
        observations={}
        def execute(job):
            v=outcome(job,'missing' if job['job_id']==halt else 'expected');observations[job['job_id']]=v;return v
        return observations,drive(execute,lambda _:None)

    def test_complete_early_and_final_halts_reconstruct(self):
        for halt in (None,'generated-002','generated-008'):
            observations,ledger=self.records(halt)
            self.assertEqual(reconstruct_schedule(observations,ledger),ledger)

    def test_extra_missing_and_changed_ledger_rejected(self):
        observations,ledger=self.records('generated-002')
        extra=deepcopy(observations);extra['generated-003']=deepcopy(extra['generated-002'])
        with self.assertRaises(ValueError):reconstruct_schedule(extra,ledger)
        missing=deepcopy(observations);missing.pop('generated-002')
        with self.assertRaises(ValueError):reconstruct_schedule(missing,ledger)
        changed=deepcopy(ledger);changed['status']='completed_bounded_diagnostic'
        with self.assertRaises(ValueError):reconstruct_schedule(observations,changed)
