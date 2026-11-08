import copy
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'scripts'))
from validate_realworld_interruption import fingerprint, compare_repeats


class RepeatTests(unittest.TestCase):
    def setUp(self):
        self.raw = json.loads(next((ROOT/'results/realworld-paired-controls-ci-20261107').glob('*-api-r1.json')).read_bytes())

    def test_clock_and_generated_slug_are_excluded(self):
        other = copy.deepcopy(self.raw)
        other['prefix_state']['slug'] = 'generated-reference'
        other['prefix_state']['createdAt'] = 'another-time'
        self.assertEqual(fingerprint(self.raw), fingerprint(other))

    def test_business_difference_is_retained(self):
        other = copy.deepcopy(self.raw); other['final_state']['body'] = 'different'
        self.assertNotEqual(fingerprint(self.raw), fingerprint(other))

    def test_guard_difference_is_retained(self):
        other = copy.deepcopy(self.raw); other['integrity']['guards'][0]['passed'] = False
        self.assertNotEqual(fingerprint(self.raw), fingerprint(other))

    def test_same_attempt_cannot_count_as_repeat(self):
        with self.assertRaisesRegex(ValueError, 'separate attempt'):
            compare_repeats(ROOT, ROOT)

    def test_real_sigterm_exits_wrapper_and_owned_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp); ready = root/'ready'
            fixture = "import os,time;from pathlib import Path;Path("+repr(str(ready))+").write_text(str(os.getpid()));time.sleep(30)"
            bootstrap = f'''import sys,subprocess
sys.path.insert(0,{str(ROOT/'scripts/ci')!r})
import run_realworld_supervised as m
real=subprocess.Popen
m.subprocess.Popen=lambda command,**kw: real([sys.executable,'-c',{fixture!r}],**kw)
m.main()
'''
            env = {**os.environ, 'CI_ARTIFACT_DIR': tmp, 'STUDY_RUNTIME': tmp}
            proc = subprocess.Popen([sys.executable, '-c', bootstrap], env=env, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            try:
                deadline = time.monotonic()+5
                while not ready.exists() and proc.poll() is None and time.monotonic()<deadline:
                    time.sleep(.02)
                self.assertTrue(ready.exists())
                proc.send_signal(signal.SIGTERM); out, err = proc.communicate(timeout=10)
                self.assertEqual(proc.returncode, 143, err.decode())
                cleanup = json.loads((root/'realworld-owned-process-cleanup.json').read_text())['runner']
                self.assertTrue(cleanup['exit_confirmed']); self.assertEqual(cleanup['errors'], [])
                self.assertIn('SIGTERM', cleanup['signals'])
            finally:
                if proc.poll() is None: proc.kill(); proc.communicate()


if __name__ == '__main__': unittest.main()
