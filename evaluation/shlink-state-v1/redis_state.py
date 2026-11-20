#!/usr/bin/env python3
"""Private binary-safe Redis state snapshots. No application API or credentials."""
import base64,hashlib,json,socket
B64=lambda b:base64.b64encode(b).decode('ascii')
UNB64=lambda s:base64.b64decode(s,validate=True)
SUPPORTED={b'string',b'list',b'set',b'zset',b'hash'}
class Redis:
 def __init__(self,host='127.0.0.1',port=56379):
  self.sock=socket.create_connection((host,port),timeout=3);self.sock.settimeout(3);self.f=self.sock.makefile('rb')
 def close(self):self.f.close();self.sock.close()
 def cmd(self,*parts):
  values=[p if isinstance(p,bytes) else str(p).encode() for p in parts]
  self.sock.sendall(b'*'+str(len(values)).encode()+b'\r\n'+b''.join(b'$'+str(len(p)).encode()+b'\r\n'+p+b'\r\n' for p in values))
  return self.read()
 def read(self):
  line=self.f.readline(1048577);assert line.endswith(b'\r\n') and len(line)<=1048576,'invalid RESP line';kind,value=line[:1],line[1:-2]
  if kind==b'+':return value
  if kind==b'-':raise RuntimeError(value.decode(errors='replace'))
  if kind==b':':return int(value)
  if kind==b'$':
   size=int(value)
   if size==-1:return None
   assert 0<=size<=32*1024**2,'RESP bulk cap'
   data=self.f.read(size);assert len(data)==size and self.f.read(2)==b'\r\n';return data
  if kind==b'*':
   count=int(value)
   if count==-1:return None
   assert 0<=count<=100000,'RESP array cap';return [self.read() for _ in range(count)]
  raise ValueError('unsupported RESP type')
def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()
def digest(x):return hashlib.sha256(canonical(x)).hexdigest()
def snapshot(client):
 keyspace=client.cmd('INFO','keyspace').decode();assert all(not l.startswith('db') or l.startswith('db0:') for l in keyspace.splitlines()),'nonzero Redis database'
 stats=client.cmd('INFO','stats').decode();assert 'evicted_keys:0\r\n' in stats,'evictions detected'
 assert client.cmd('PUBSUB','CHANNELS')==[] and client.cmd('PUBSUB','NUMPAT')==0,'pubsub activity'
 keys=set();cursor=b'0'
 while True:
  cursor,batch=client.cmd('SCAN',cursor,'COUNT',1000);keys.update(batch);assert len(keys)<=100000
  if cursor==b'0':break
 rows=[]
 for key in sorted(keys):
  typ=client.cmd('TYPE',key);assert typ in SUPPORTED,'unsupported key type'
  assert client.cmd('PTTL',key)==-1,'expiring or vanished key'
  value=client.cmd('DUMP',key);assert isinstance(value,bytes)
  rows.append(dict(key=B64(key),type=typ.decode(),dump=B64(value),pttl=-1))
 assert client.cmd('DBSIZE')==len(rows),'key count changed'
 return dict(database=0,entries=rows)
def restore(client,state):
 assert state['database']==0
 # Caller must own this disposable instance and stop all application writers.
 assert client.cmd('FLUSHDB')==b'OK'
 for row in state['entries']:
  assert row['type'].encode() in SUPPORTED and row['pttl']==-1
  assert client.cmd('RESTORE',UNB64(row['key']),0,UNB64(row['dump']))==b'OK'
 assert snapshot(client)==state,'restored Redis logical state differs'
