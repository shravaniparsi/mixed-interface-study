"""Bounded Redis observation; restore only into a new empty disposable instance."""
import base64,socket,time
from source_check import require
B64=lambda value:base64.b64encode(value).decode('ascii')
UNB64=lambda value:base64.b64decode(value,validate=True)
SUPPORTED={b'string',b'list',b'set',b'zset',b'hash'}
class Redis:
 def __init__(self,host='127.0.0.1',port=56379,unix_socket=None):
  if unix_socket:
   self.sock=socket.socket(socket.AF_UNIX,socket.SOCK_STREAM);self.sock.settimeout(3);self.sock.connect(str(unix_socket))
  else:self.sock=socket.create_connection((host,port),timeout=3)
  self.sock.settimeout(3);self.stream=self.sock.makefile('rb')
 def close(self):self.stream.close();self.sock.close()
 def cmd(self,*parts):
  values=[v if isinstance(v,bytes) else str(v).encode() for v in parts]
  self.sock.sendall(b'*'+str(len(values)).encode()+b'\r\n'+b''.join(b'$'+str(len(v)).encode()+b'\r\n'+v+b'\r\n' for v in values));self.remaining=64*1024**2
  return self.read()
 def read(self,depth=0):
  require(depth<16,'resp_depth');line=self.stream.readline(1048577);self.remaining-=len(line)
  require(line.endswith(b'\r\n') and len(line)<=1048576 and self.remaining>=0,'resp_line');kind,value=line[:1],line[1:-2]
  if kind==b'+':return value
  if kind==b'-':raise ValueError('Redis error: '+value.decode(errors='replace'))
  if kind==b':':return int(value)
  if kind==b'$':
   count=int(value)
   if count==-1:return None
   require(0<=count<=32*1024**2 and count<=self.remaining,'resp_bulk_limit');self.remaining-=count
   data=self.stream.read(count);require(len(data)==count and self.stream.read(2)==b'\r\n','resp_bulk_complete');return data
  if kind==b'*':
   count=int(value)
   if count==-1:return None
   require(0<=count<=100000,'resp_array_limit');return [self.read(depth+1) for _ in range(count)]
  raise ValueError('Unsupported RESP type')
def logical_value(client,key,kind):
 if kind==b'string':return B64(client.cmd('GET',key))
 if kind==b'list':return [B64(v) for v in client.cmd('LRANGE',key,0,-1)]
 if kind==b'set':return [B64(v) for v in sorted(client.cmd('SMEMBERS',key))]
 if kind==b'hash':
  flat=client.cmd('HGETALL',key);require(len(flat)%2==0,'hash_pairs');pairs=list(zip(flat[::2],flat[1::2]));require(len({k for k,v in pairs})==len(pairs),'unique_hash_fields')
  return [[B64(k),B64(v)] for k,v in sorted(pairs)]
 if kind==b'zset':
  flat=client.cmd('ZRANGE',key,0,-1,'WITHSCORES');require(len(flat)%2==0,'zset_pairs')
  return [[B64(member),score.decode('ascii')] for member,score in zip(flat[::2],flat[1::2])]
 raise ValueError('Unsupported Redis logical type')
def logical(state):
 require(set(state)=={'database','entries'} and state['database']==0,'redis_state_shape')
 require(len({r['key'] for r in state['entries']})==len(state['entries']),'unique_snapshot_keys')
 return dict(database=0,entries=[{k:r[k] for k in ['key','type','pttl','value']} for r in sorted(state['entries'],key=lambda r:UNB64(r['key']))])
def snapshot(client):
 # Caller must stop all application writers before the checkpoint. No quiet-timer claim.
 deadline=time.monotonic()+10
 info=client.cmd('INFO','keyspace').decode();require(all(not line.startswith('db') or line.startswith('db0:') for line in info.splitlines()),'redis_database_scope')
 require('evicted_keys:0\r\n' in client.cmd('INFO','stats').decode(),'redis_evictions')
 require(client.cmd('PUBSUB','CHANNELS')==[] and client.cmd('PUBSUB','NUMPAT')==0,'redis_pubsub_activity')
 keys=set();cursor=b'0'
 while True:
  require(time.monotonic()<deadline,'redis_snapshot_deadline');cursor,batch=client.cmd('SCAN',cursor,'COUNT',1000);keys.update(batch);require(len(keys)<=10000,'redis_key_limit')
  if cursor==b'0':break
 rows=[]
 for key in sorted(keys):
  require(time.monotonic()<deadline,'redis_snapshot_deadline');kind=client.cmd('TYPE',key);require(kind in SUPPORTED,'redis_key_type')
  require(client.cmd('PTTL',key)==-1,'redis_expiring_or_missing_key')
  dump=client.cmd('DUMP',key);require(isinstance(dump,bytes),'redis_dump');rows.append(dict(key=B64(key),type=kind.decode(),dump=B64(dump),pttl=-1,value=logical_value(client,key,kind)))
 require(client.cmd('DBSIZE')==len(rows),'redis_key_count_changed')
 return dict(database=0,entries=rows)
def restore_empty(client,state):
 require(state['database']==0 and client.cmd('DBSIZE')==0,'empty_owned_restore_target')
 require(len({r['key'] for r in state['entries']})==len(state['entries']),'unique_restore_keys')
 for row in state['entries']:
  require(row['type'].encode() in SUPPORTED and row['pttl']==-1,'supported_restore_entry')
  require(client.cmd('RESTORE',UNB64(row['key']),0,UNB64(row['dump']))==b'OK','redis_restore')
 require(logical(snapshot(client))==logical(state),'redis_restore_equality')
