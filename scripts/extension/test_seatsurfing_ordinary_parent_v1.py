import subprocess
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock,patch
import qualify_seatsurfing_ordinary_v1 as module

class Parent(unittest.TestCase):
    def test_expired_deadline_prevents_launch(self):
        with patch.object(module.time,'monotonic',return_value=11),patch.object(module.subprocess,'Popen') as launch:
            with self.assertRaises(TimeoutError):module.run_bounded(['unused'],'unused',10,30)
            launch.assert_not_called()
    def test_shared_deadline_caps_stage(self):
        process=Mock(pid=123);process.wait.return_value=0
        with tempfile.TemporaryDirectory() as directory,patch.object(module.time,'monotonic',return_value=7),patch.object(module.subprocess,'Popen',return_value=process):
            module.run_bounded(['synthetic'],Path(directory)/'log',10,90)
            process.wait.assert_called_once_with(timeout=3)
    def test_failed_leader_still_terminates_descendant_group(self):
        process=Mock(pid=123);process.wait.return_value=1
        with tempfile.TemporaryDirectory() as directory,patch.object(module.time,'monotonic',return_value=7),patch.object(module.subprocess,'Popen',return_value=process),patch.object(module.os,'killpg') as kill:
            with self.assertRaises(subprocess.CalledProcessError):module.run_bounded(['synthetic'],Path(directory)/'log',10,90)
            self.assertEqual([c.args for c in kill.call_args_list],[(123,module.signal.SIGTERM),(123,module.signal.SIGKILL)])
    def test_local_application_launch_refused(self):
        with patch.dict(module.os.environ,{},clear=True):
            with self.assertRaisesRegex(ValueError,'hosted CI'):module.verify_registration('nonexistent')

if __name__=='__main__':unittest.main()
