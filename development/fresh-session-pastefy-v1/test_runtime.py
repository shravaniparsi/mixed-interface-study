import pathlib,sys,tempfile,unittest
from runtime import Runtime
class Lifecycle(unittest.TestCase):
 def test_live_process_blocks_snapshot_and_stop_reaps_it(self):
  with tempfile.TemporaryDirectory() as tmp:
   jar=pathlib.Path(tmp)/'fake.jar';jar.write_bytes(b'fixture')
   r=Runtime(pathlib.Path(tmp)/'state',jar);r.command=lambda mode:[sys.executable,'-c','import time;time.sleep(30)']
   try:
    r.launch('start')
    with self.assertRaises(ValueError):r.observe()
    r.stop();self.assertIsNotNone(r.process.poll());r.state.stopped()
   finally:r.stop()
 def test_failed_original_migration_does_not_seed_credentials(self):
  with tempfile.TemporaryDirectory() as tmp:
   jar=pathlib.Path(tmp)/'fake.jar';jar.write_bytes(b'fixture')
   r=Runtime(pathlib.Path(tmp)/'state',jar);r.command=lambda mode:[sys.executable,'-c','raise SystemExit(7)']
   r.state.start_database=lambda:None
   with self.assertRaises(ValueError):r.initialize()
   self.assertFalse((r.state.base/'credentials.json').exists());self.assertIsNotNone(r.process.poll())
if __name__=='__main__':unittest.main()
