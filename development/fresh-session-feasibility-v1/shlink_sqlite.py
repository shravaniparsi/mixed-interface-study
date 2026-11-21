#!/usr/bin/env python3
"""Read-only SQLite evidence and verified backups; independent of Shlink application code."""
import base64,hashlib,json,pathlib,sqlite3,time
from urllib.parse import quote
from source_check import require

def canonical(value):return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()
def typed(value):
 if value is None:return dict(type='null',value=None)
 if isinstance(value,bytes):return dict(type='blob',value=base64.b64encode(value).decode())
 if isinstance(value,int):return dict(type='integer',value=value)
 if isinstance(value,float):return dict(type='real',value=value.hex())
 require(isinstance(value,str),'supported_sqlite_type');return dict(type='text',value=value)
def ident(value):return '"'+value.replace('"','""')+'"'
def connect(path):
 path=pathlib.Path(path);require(path.is_file() and not path.is_symlink(),'regular_database')
 return sqlite3.connect('file:'+quote(str(path.resolve()))+'?mode=ro',uri=True,timeout=3)
def snapshot(path):
 con=connect(path)
 try:
  con.execute('PRAGMA query_only=ON');con.execute('BEGIN')
  schema=con.execute('SELECT type,name,tbl_name,sql FROM sqlite_schema ORDER BY type,name').fetchall();tables={}
  for kind,name,_,sql in schema:
   if kind!='table':continue
   require(sql is None or 'CREATE VIRTUAL TABLE' not in sql.upper(),'virtual_table_requires_observer',table=name)
   rows=[[typed(value) for value in row] for row in con.execute('SELECT * FROM '+ident(name))];rows.sort(key=canonical)
   indexes=con.execute('PRAGMA index_list('+ident(name)+')').fetchall()
   tables[name]=dict(columns=con.execute('PRAGMA table_xinfo('+ident(name)+')').fetchall(),foreign_keys=con.execute('PRAGMA foreign_key_list('+ident(name)+')').fetchall(),indexes=indexes,index_columns={i[1]:con.execute('PRAGMA index_xinfo('+ident(i[1])+')').fetchall() for i in indexes},rows=rows)
  require(con.execute('PRAGMA integrity_check').fetchall()==[('ok',)],'sqlite_integrity')
  violations=con.execute('PRAGMA foreign_key_check').fetchall();require(not violations,'foreign_key_violations',rows=violations)
  result=dict(schema=schema,tables=tables,pragmas={k:con.execute('PRAGMA '+k).fetchone()[0] for k in ['user_version','application_id','encoding','auto_vacuum']})
  return json.loads(canonical(result))
 finally:con.close()
def backup(source,target,timeout_seconds=15):
 target=pathlib.Path(target);require(not target.exists() and not target.is_symlink(),'new_backup_destination')
 require(timeout_seconds>0,'positive_backup_timeout')
 before=snapshot(source);src=connect(source);dst=sqlite3.connect(str(target));deadline=time.monotonic()+timeout_seconds
 def progress(status,remaining,total):require(time.monotonic()<=deadline,'backup_deadline')
 try:
  src.backup(dst,pages=128,progress=progress,sleep=0.05);require(dst.execute('PRAGMA integrity_check').fetchall()==[('ok',)],'backup_integrity')
 finally:dst.close();src.close()
 require(before==snapshot(source)==snapshot(target),'backup_logical_equality')
 return dict(status='logical_backup_verified',logical_sha256=hashlib.sha256(canonical(before)).hexdigest())
if __name__=='__main__':
 import sys
 pathlib.Path(sys.argv[2]).write_text(json.dumps(snapshot(sys.argv[1]),indent=2)+'\n')
