"""Disposable MySQL process, typed observations and verified logical resets.
Application writers must be stopped. Database storage is outside application files.
"""
import datetime,hashlib,json,os,pathlib,re,shutil,signal,subprocess,time,tempfile
from checkpoint import State,inventory
from shlink_sqlite import canonical,typed
from source_check import require

def ident(name):return '`'+name.replace('`','``')+'`'
def cell(value):
 if isinstance(value,(datetime.datetime,datetime.date)):return typed(value.isoformat(sep=' ') if isinstance(value,datetime.datetime) else value.isoformat())
 return typed(value)
class MySQLState(State):
 def __init__(self,base):
  super().__init__(base);self.db_process=None;self.db_log=None;self.socket=None;self.storage=None
 def connection(self,database=True):
  import pymysql
  return pymysql.connect(unix_socket=self.socket,user='root',database='study' if database else None,charset='utf8mb4',autocommit=False)
 def start_database(self):
  root=pathlib.Path('/var/lib/mysql');root.mkdir(exist_ok=True);self.storage=pathlib.Path(tempfile.mkdtemp(prefix='fresh-study-',dir=root));data=self.storage/'data';self.socket=str(self.storage/'mysql.sock');require(not data.exists(),'fresh_mysql_datadir');self.db_log=(self.base/'mysql.log').open('wb')
  args=['/usr/sbin/mysqld','--no-defaults','--user=root','--datadir='+str(data)]
  p=subprocess.run(args+['--initialize-insecure'],stdout=self.db_log,stderr=subprocess.STDOUT,timeout=90);require(p.returncode==0,'mysql_initialize')
  self.db_process=subprocess.Popen(args+['--socket='+self.socket,'--pid-file='+str(self.storage/'mysql.pid'),'--bind-address=127.0.0.1','--port=3306','--mysqlx=OFF','--skip-log-bin','--innodb-buffer-pool-size=64M'],stdout=self.db_log,stderr=subprocess.STDOUT,start_new_session=True)
  deadline=time.monotonic()+60
  while time.monotonic()<deadline:
   require(self.db_process.poll() is None,'mysql_running')
   try:
    con=self.connection(False)
    with con.cursor() as cur:cur.execute('CREATE DATABASE study CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
    con.close();return
   except OSError:time.sleep(.2)
   except Exception as error:
    if type(error).__name__!='OperationalError':raise
    time.sleep(.2)
  raise ValueError('mysql_start_deadline')
 def close_database(self):
  if self.db_process is not None and self.db_process.poll() is None:
   os.killpg(self.db_process.pid,signal.SIGTERM)
   try:self.db_process.wait(timeout=30)
   except subprocess.TimeoutExpired:os.killpg(self.db_process.pid,signal.SIGKILL);self.db_process.wait(timeout=5)
  if self.db_log:self.db_log.close();self.db_log=None
  if self.storage is not None:
   require(self.storage.parent==pathlib.Path('/var/lib/mysql') and self.storage.name.startswith('fresh-study-'),'owned_mysql_cleanup');shutil.rmtree(self.storage);self.storage=None
 def snapshot(self):
  self.stopped();con=self.connection()
  try:
   with con.cursor() as c:
    c.execute('SET TRANSACTION READ ONLY');c.execute('START TRANSACTION WITH CONSISTENT SNAPSHOT');c.execute('SHOW FULL TABLES');names=c.fetchall();tables={};schema=[];sequences={}
    for name,kind in names:
     require(kind=='BASE TABLE','mysql_base_tables_only')
     c.execute('SHOW CREATE TABLE '+ident(name));ddl=c.fetchone()[1];schema.append([name,re.sub(r' AUTO_INCREMENT=\d+','',ddl)])
     c.execute('SHOW FULL COLUMNS FROM '+ident(name));cols=c.fetchall();columns=[[i,col[0],*col[1:]] for i,col in enumerate(cols)]
     c.execute('SHOW INDEX FROM '+ident(name));indexes=[list(x) for x in c.fetchall()]
     # Cardinality is a query-optimizer estimate, not a schema attribute.
     for row in indexes:row[6]=None
     c.execute('SELECT * FROM '+ident(name));rows=[[cell(v) for v in row] for row in c.fetchall()];rows.sort(key=canonical)
     tables[name]=dict(columns=columns,indexes=indexes,rows=rows)
     c.execute('SELECT AUTO_INCREMENT FROM information_schema.TABLES WHERE TABLE_SCHEMA=%s AND TABLE_NAME=%s',('study',name));sequences[name]=c.fetchone()[0]
    c.execute('SELECT TRIGGER_NAME,ACTION_STATEMENT FROM information_schema.TRIGGERS WHERE TRIGGER_SCHEMA=%s ORDER BY TRIGGER_NAME',('study',));triggers=c.fetchall()
    c.execute('SELECT @@version,@@sql_mode,@@character_set_database,@@collation_database');settings=c.fetchone()
    return json.loads(canonical(dict(schema=sorted(schema),tables=tables,pragmas=dict(engine='mysql',settings=settings,triggers=triggers),sequences=sequences)))
  finally:con.rollback();con.close()
 def observe(self,root):
  require(pathlib.Path(root)==self.live,'mysql_observation_live_only');return dict(files=inventory(self.live),database_sha256=hashlib.sha256(canonical(self.snapshot())).hexdigest())
 def checkpoint(self,label='root'):
  require(label in ['root','native','api'],'registered_checkpoint_label');self.stopped();dest=self.base/('checkpoint-'+label);require(not dest.exists(),'single_checkpoint')
  before=self.observe(self.live);dest.mkdir();shutil.copytree(self.live,dest/'files')
  with (dest/'database.sql').open('wb') as out:
   subprocess.run(['mysqldump','--no-defaults','--socket='+self.socket,'--user=root','--single-transaction','--skip-comments','--skip-dump-date','--set-gtid-purged=OFF','--no-tablespaces','--routines','--events','--triggers','study'],stdout=out,check=True,timeout=30)
  require(before==self.observe(self.live),'checkpoint_source_unchanged');before['dump_sha256']=hashlib.sha256((dest/'database.sql').read_bytes()).hexdigest();(dest/'manifest.json').write_bytes(canonical(before));return before
 def restore(self,label='root'):
  require(label in ['root','native','api'],'registered_checkpoint_label');self.stopped();dest=self.base/('checkpoint-'+label);saved=json.loads((dest/'manifest.json').read_text())
  require(hashlib.sha256((dest/'database.sql').read_bytes()).hexdigest()==saved['dump_sha256'] and inventory(dest/'files')==saved['files'],'checkpoint_not_tampered')
  con=self.connection(False)
  try:
   with con.cursor() as c:c.execute('DROP DATABASE study');c.execute('CREATE DATABASE study CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci')
  finally:con.close()
  with (dest/'database.sql').open('rb') as inp:subprocess.run(['mysql','--no-defaults','--socket='+self.socket,'--user=root','study'],stdin=inp,check=True,timeout=30)
  shutil.rmtree(self.live);shutil.copytree(dest/'files',self.live)
  require(self.observe(self.live)=={k:v for k,v in saved.items() if k!='dump_sha256'},'mysql_restore_exact_logical_state');return saved
