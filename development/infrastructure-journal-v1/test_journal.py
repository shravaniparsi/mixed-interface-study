import json,pathlib,sys,tempfile,time,unittest
from journal import run
class JournalTests(unittest.TestCase):
 def setUp(self):self.temp=tempfile.TemporaryDirectory();self.root=pathlib.Path(self.temp.name)
 def tearDown(self):self.temp.cleanup()
 def command(self,label,code,**kw):
  p=self.root/(label+'.json');result=run(label,[sys.executable,'-c',code],p,**kw);self.assertEqual(result,json.loads(p.read_text()));return result
 def test_success(self):self.assertEqual(self.command('ok',"print('done')")['status'],'succeeded')
 def test_failure_diagnostic_survives(self):
  secret='synthetic-credential-123';r=self.command('bootstrap',f"import sys;print('permission denied '+{secret!r});sys.exit(7)",secrets=[secret]);self.assertEqual(r['status'],'failed');self.assertEqual(r['exit_code'],7);self.assertIn('permission denied',r['output']);self.assertNotIn(secret,json.dumps(r));self.assertIn('[REDACTED]',r['output'])
 def test_timeout_keeps_prefix(self):
  t=time.monotonic();r=self.command('timeout',"import time;print('started',flush=True);time.sleep(30)",timeout=.15);self.assertEqual(r['status'],'timeout');self.assertIn('started',r['output']);self.assertLess(time.monotonic()-t,3)
 def test_output_cap(self):
  r=self.command('flood',"import sys;sys.stdout.write('x'*1000000)",output_limit=1024);self.assertEqual(r['status'],'output_limit');self.assertEqual(r['captured_bytes'],1024)
 def test_partial_credential_at_cap(self):
  secret='synthetic-credential-123';r=self.command('cut',f"print('x'*20+{secret!r})",output_limit=30,secrets=[secret]);self.assertEqual(r['status'],'output_limit');self.assertNotIn('synthetic',r['output'])
 def test_missing_executable(self):
  p=self.root/'missing.json';r=run('missing',['/nonexistent/research-command'],p);self.assertEqual(r['status'],'launch_or_observation_error');self.assertIn('No such file',r['error']);self.assertEqual(r,json.loads(p.read_text()))
 def test_started_receipt_precedes_child(self):
  p=self.root/'ordering.json';code="import json;assert json.load(open("+repr(str(p))+"))['status']=='started';print('receipt existed')";self.assertEqual(run('ordering',[sys.executable,'-c',code],p)['status'],'succeeded')
 def test_failed_initial_write_does_not_launch(self):
  blocker=self.root/'file';blocker.write_text('not a directory');marker=self.root/'child-ran'
  with self.assertRaises(OSError):run('cannot-record',[sys.executable,'-c',f"open({str(marker)!r},'w').close()"],blocker/'result.json')
  self.assertFalse(marker.exists())
if __name__=='__main__':unittest.main(verbosity=2)
