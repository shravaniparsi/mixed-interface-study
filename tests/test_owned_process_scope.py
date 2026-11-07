"""Real-process supervisor checks; no application/browser qualification implied."""
import importlib.util
import json
import os
from pathlib import Path
import signal
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

PATH = Path(__file__).resolve().parents[1] / 'scripts/ci/owned_process_scope.py'
spec = importlib.util.spec_from_file_location('owned_scope', PATH)
scope = importlib.util.module_from_spec(spec)
spec.loader.exec_module(scope)


class OwnedProcessTests(unittest.TestCase):
    def child(self, ignore=False, new_session=True):
        code = ('import signal,time; ' +
                ('signal.signal(signal.SIGTERM,signal.SIG_IGN); ' if ignore else '') +
                'print("ready",flush=True); time.sleep(30)')
        child = subprocess.Popen([sys.executable, '-u', '-c', code],
                                 stdout=subprocess.PIPE, text=True, start_new_session=new_session)
        self.addCleanup(self.reap, child)
        self.assertEqual(child.stdout.readline().strip(), 'ready')
        return child

    @staticmethod
    def reap(child):
        if child.poll() is None:
            child.kill()
        child.wait(timeout=3)
        if child.stdout:
            child.stdout.close()

    def test_graceful_child_exit(self):
        record = scope.stop_owned_group(self.child(), grace=.2, kill_wait=1)
        self.assertTrue(record['exit_confirmed'])
        self.assertEqual(record['signals'], ['SIGTERM'])
        self.assertEqual(record['descendant_cleanup'], 'not_established')

    def test_child_ignoring_term_is_killed_and_reaped(self):
        record = scope.stop_owned_group(self.child(ignore=True), grace=.1, kill_wait=1)
        self.assertTrue(record['exit_confirmed'])
        self.assertEqual(record['signals'], ['SIGTERM', 'SIGKILL'])
        self.assertLess(record['elapsed_s'], 3)

    def test_exited_child_is_not_signalled(self):
        child = self.child()
        child.terminate(); child.wait(timeout=2)
        with patch.object(scope.os, 'killpg') as kill:
            record = scope.stop_owned_group(child)
        kill.assert_not_called()
        self.assertTrue(record['exit_confirmed'])

    def test_non_owned_group_is_never_signalled(self):
        child = self.child(new_session=False)
        with patch.object(scope.os, 'killpg') as kill:
            record = scope.stop_owned_group(child)
        kill.assert_not_called()
        self.assertFalse(record['exit_confirmed'])
        self.assertTrue(record['errors'])

    def test_signal_handlers_restored(self):
        before = signal.getsignal(signal.SIGTERM)
        with scope.interruption_as_exception():
            with self.assertRaises(SystemExit) as exc:
                os.kill(os.getpid(), signal.SIGTERM)
            self.assertEqual(exc.exception.code, 143)
        self.assertEqual(signal.getsignal(signal.SIGTERM), before)

    def test_repeated_stop_signal_does_not_interrupt_cleanup(self):
        before = signal.getsignal(signal.SIGTERM)
        with scope.defer_stop_signals():
            os.kill(os.getpid(), signal.SIGTERM)
            os.kill(os.getpid(), signal.SIGINT)
        self.assertEqual(signal.getsignal(signal.SIGTERM), before)

    def test_external_sigterm_runs_finally_and_records_child_exit(self):
        with tempfile.TemporaryDirectory() as directory:
            report = Path(directory)/'cleanup.json'
            code = '''import sys,subprocess,json
from pathlib import Path
sys.path.insert(0,sys.argv[1])
from owned_process_scope import interruption_as_exception,defer_stop_signals,stop_owned_group
child=None
with interruption_as_exception():
 try:
  child=subprocess.Popen([sys.executable,'-c','import time; time.sleep(30)'],start_new_session=True)
  print('ready',flush=True)
  child.wait()
 finally:
  with defer_stop_signals():
   Path(sys.argv[2]).write_text(json.dumps(stop_owned_group(child,grace=.2,kill_wait=1)))
'''
            outer = subprocess.Popen([sys.executable,'-u','-c',code,str(PATH.parent),str(report)],stdout=subprocess.PIPE,text=True)
            self.addCleanup(self.reap,outer)
            self.assertEqual(outer.stdout.readline().strip(),'ready')
            outer.terminate()
            self.assertEqual(outer.wait(timeout=5),143)
            evidence=json.loads(report.read_text())
            self.assertTrue(evidence['exit_confirmed'])
            self.assertEqual(evidence['errors'],[])

    def test_invalid_deadlines_rejected_before_signal(self):
        with self.assertRaises(ValueError):
            scope.stop_owned_group(None, grace=0)

    def test_petclinic_wrapper_external_stop_retains_both_cleanup_records(self):
        # Run the actual wrapper with its application launches replaced by sleeping
        # Python processes. This tests supervisor wiring, not application recovery.
        with tempfile.TemporaryDirectory() as directory:
            out=Path(directory)
            (out/'petclinic-bootstrap.json').write_text('{"jar":"unused"}')
            code = r"""import sys,os,types,json,hashlib,subprocess,runpy,time
from pathlib import Path
root=Path(sys.argv[1]);out=Path(sys.argv[2])
os.environ.update(CI_ARTIFACT_DIR=str(out),STUDY_RUNTIME=str(out),GITHUB_SHA='fixture',JAVA_HOME='unused',PLAYWRIGHT_MODULE_PATH='unused',CHROME_EXECUTABLE='unused')
sys.path.insert(0,str(root/'scripts/ci'))
fake=types.ModuleType('validate_petclinic_integrity')
fake.SOURCES=[]
fake.sha=lambda p: hashlib.sha256(p.read_bytes()).hexdigest() if p.exists() else 'fixture'
fake.read=lambda p: {'cases':[{'id':'fixture'}]} if p.name=='petclinic-integrity-controls-v1.json' else json.loads(p.read_text())
fake.validate_run=lambda *a: {'status':'fixture','branches':[]}
sys.modules['validate_petclinic_integrity']=fake
real_popen=subprocess.Popen
children=[]
def launch(*args,**kwargs):
 child=real_popen([sys.executable,'-c','import time; time.sleep(30)'],start_new_session=True)
 children.append(child)
 if len(children)==2:(out/'ready.json').write_text(json.dumps([c.pid for c in children]))
 return child
subprocess.Popen=launch
import urllib.request
class Response:
 status=200
 def __enter__(self):return self
 def __exit__(self,*args):pass
urllib.request.urlopen=lambda *a,**k:Response()
try:runpy.run_path(str(root/'scripts/ci/run_petclinic_integrity.py'),run_name='__main__')
finally:
 for child in children:
  if child.poll() is None:child.kill()
  child.wait(timeout=2)
"""
            outer=subprocess.Popen([sys.executable,'-u','-c',code,str(PATH.parents[2]),directory])
            self.addCleanup(self.reap,outer)
            deadline=time.monotonic()+5
            while not (out/'ready.json').exists() and outer.poll() is None and time.monotonic()<deadline:
                time.sleep(.01)
            self.assertTrue((out/'ready.json').exists(),'Wrapper did not launch both fixture children')
            outer.terminate()
            self.assertEqual(outer.wait(timeout=5),143)
            evidence=json.loads((out/'petclinic-owned-process-cleanup.json').read_text())
            self.assertEqual(set(evidence),{'runner','frontend'})
            self.assertTrue(all(r['exit_confirmed'] and not r['errors'] for r in evidence.values()))
