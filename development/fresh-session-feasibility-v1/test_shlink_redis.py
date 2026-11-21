"""Real isolated Redis tests. Local server version is recorded separately from study runtime."""
import pathlib,shutil,subprocess,tempfile,time,unittest
from shlink_redis import Redis,snapshot,restore_empty,logical
@unittest.skipUnless(shutil.which('redis-server'),'redis-server unavailable')
class RedisObservation(unittest.TestCase):
 def setUp(self):
  self.tmp=tempfile.TemporaryDirectory(prefix='fsr-',dir='/private/tmp' if pathlib.Path('/private/tmp').is_dir() else None);self.root=pathlib.Path(self.tmp.name);self.processes=[];self.clients=[]
 def tearDown(self):
  for c in self.clients:c.close()
  for p in self.processes:
   p.terminate()
   try:p.wait(timeout=5)
   except subprocess.TimeoutExpired:p.kill();p.wait(timeout=5)
  self.tmp.cleanup()
 def server(self,name):
  sock=self.root/(name+'.sock');p=subprocess.Popen([shutil.which('redis-server'),'--port','0','--unixsocket',str(sock),'--save','','--appendonly','no','--dir',str(self.root)],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL);self.processes.append(p);deadline=time.monotonic()+5
  while not sock.exists():
   if p.poll() is not None:raise RuntimeError('redis-server exited')
   if time.monotonic()>deadline:raise RuntimeError('redis-server startup timeout')
   time.sleep(.02)
  c=Redis(unix_socket=sock);self.clients.append(c);self.assertEqual(c.cmd('PING'),b'PONG');return c
 def test_binary_types_roundtrip_to_new_instance(self):
  a=self.server('a');a.cmd('SET',b'key\x00\xff',b'value\x00\xff');a.cmd('RPUSH','list',b'a',b'b');a.cmd('SADD','set','x','y');a.cmd('HSET','hash','field',b'\xff');a.cmd('ZADD','sorted','1.5','one')
  before=snapshot(a);self.assertEqual(len(before['entries']),5);b=self.server('b');restore_empty(b,before);self.assertEqual(logical(snapshot(b)),logical(before));self.assertEqual(b.cmd('GET',b'key\x00\xff'),b'value\x00\xff');self.assertEqual(set(b.cmd('SMEMBERS','set')),{b'x',b'y'})
  with self.assertRaises(ValueError):restore_empty(b,before)
  b.cmd('SET',b'key\x00\xff',b'changed');self.assertNotEqual(logical(snapshot(b)),logical(before))
 def test_expiring_keys_and_nonzero_databases_refused(self):
  a=self.server('a');a.cmd('SET','expiring','x','PX',60000)
  with self.assertRaises(ValueError):snapshot(a)
  a.cmd('DEL','expiring');a.cmd('SELECT',1);a.cmd('SET','other','x');a.cmd('SELECT',0)
  with self.assertRaises(ValueError):snapshot(a)
 def test_unsupported_stream_refused(self):
  a=self.server('a');a.cmd('XADD','stream','*','field','value')
  with self.assertRaises(ValueError):snapshot(a)
if __name__=='__main__':unittest.main()
