#!/usr/bin/env python3
"""Independent typed logical SQLite snapshot and verified backup, private by default."""
import base64,hashlib,json,pathlib,sqlite3,shutil,os
from urllib.parse import quote

def canonical(v):return json.dumps(v,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()
def typed(v):
 if isinstance(v,bytes):return {'type':'blob','value':base64.b64encode(v).decode()}
 if v is None:return {'type':'null','value':None}
 if isinstance(v,int):return {'type':'integer','value':v}
 if isinstance(v,float):return {'type':'real','value':v.hex()}
 assert isinstance(v,str);return {'type':'text','value':v}
def ident(v):return '"'+v.replace('"','""')+'"'
def snapshot(path):
 con=sqlite3.connect('file:'+quote(str(pathlib.Path(path).resolve()))+'?mode=ro',uri=True,timeout=3)
 try:
  con.execute('PRAGMA query_only=ON');con.execute('BEGIN')
  schema=con.execute('SELECT type,name,tbl_name,sql FROM sqlite_schema ORDER BY type,name').fetchall()
  assert not any(row[0]=='view' for row in schema),'views require explicit scope'
  tables={}
  for kind,name,table,sql in schema:
   if kind!='table':continue
   assert sql is None or 'CREATE VIRTUAL TABLE' not in sql.upper(),'virtual tables unsupported'
   columns=con.execute('PRAGMA table_xinfo('+ident(name)+')').fetchall()
   rowid=None
   if not (sql and 'WITHOUT ROWID' in sql.upper()):
    rowid=next((v for v in ['rowid','_rowid_','oid'] if v.lower() not in {c[1].lower() for c in columns}),None)
    assert rowid is not None,'hidden rowid shadowed'
   projection=(ident(rowid)+',' if rowid else '')+'*'
   rows=[[typed(v) for v in row] for row in con.execute('SELECT '+projection+' FROM '+ident(name))]
   rows.sort(key=canonical)
   indexes=con.execute('PRAGMA index_list('+ident(name)+')').fetchall()
   tables[name]={'rowid_alias':rowid,'columns':con.execute('PRAGMA table_xinfo('+ident(name)+')').fetchall(),'foreign_keys':con.execute('PRAGMA foreign_key_list('+ident(name)+')').fetchall(),'indexes':indexes,'index_columns':{i[1]:con.execute('PRAGMA index_xinfo('+ident(i[1])+')').fetchall() for i in indexes},'rows':rows}
  result={'schema':schema,'tables':tables,'pragmas':{k:con.execute('PRAGMA '+k).fetchone()[0] for k in ['user_version','application_id','encoding','auto_vacuum']}}
  return json.loads(canonical(result))
 finally:con.close()
def backup(source,target):
 target=pathlib.Path(target);assert not target.exists()
 before=snapshot(source)
 src=sqlite3.connect('file:'+quote(str(pathlib.Path(source).resolve()))+'?mode=ro',uri=True,timeout=3);dst=sqlite3.connect(str(target))
 try:src.backup(dst);assert dst.execute('PRAGMA integrity_check').fetchall()==[('ok',)]
 finally:dst.close();src.close()
 assert before==snapshot(source)==snapshot(target),'backup mismatch or concurrent write'
 return hashlib.sha256(canonical(before)).hexdigest()

def restore(source,target):
 """Restore only after caller stops all writers; refuse existing WAL/SHM."""
 source=pathlib.Path(source);target=pathlib.Path(target)
 assert source.resolve()!=target.resolve(),'distinct restore paths required'
 assert not target.is_symlink(),'target symlink unsupported'
 for suffix in ['-wal','-shm','-journal']:
  assert not pathlib.Path(str(target)+suffix).exists(),'live or unclosed SQLite sidecar: '+suffix
 expected=snapshot(source)
 staged=target.with_name(target.name+'.restore-stage')
 assert not staged.exists(),'stale restore stage'
 try:
  backup(source,staged)
  if target.exists():os.chmod(staged,target.stat().st_mode & 0o777)
  os.replace(staged,target)
  assert snapshot(target)==expected,'restore logical mismatch'
 finally:
  if staged.exists():staged.unlink()
 return hashlib.sha256(canonical(expected)).hexdigest()
