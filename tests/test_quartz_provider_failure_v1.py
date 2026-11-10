from pathlib import Path
import sys,unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from retain_quartz_provider_failure_v1 import provider_rejection,MESSAGE

class ProviderFailureTests(unittest.TestCase):
    def fixture(self):return {'id':1,'status':'completed','conclusion':'failure','steps':[],'runner_id':0,'runner_name':''}
    def test_exact_never_started_provider_rejection(self):
        self.assertEqual(provider_rejection(self.fixture(),[{'annotation_level':'failure','message':MESSAGE}])['steps_executed'],0)
    def test_started_job_cannot_be_relabelled_unstarted(self):
        job=self.fixture();job['steps']=[{'name':'checkout'}]
        with self.assertRaisesRegex(ValueError,'started job'):provider_rejection(job,[{'annotation_level':'failure','message':MESSAGE}])
    def test_missing_reason_cannot_authorize_classification(self):
        with self.assertRaisesRegex(ValueError,'annotation'):provider_rejection(self.fixture(),[])
