"""Seed disposable identity only after original migrations and process shutdown.
This is fixture initialization, not a reproduction of OAuth account onboarding.
"""
import json,os,pathlib,secrets,sqlite3,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/'development/fresh-session-feasibility-v1'))
from source_check import require
from shlink_sqlite import snapshot

def seed(database,credential_file):
 db=pathlib.Path(database);out=pathlib.Path(credential_file)
 require(db.is_file() and not db.is_symlink(),'existing_migrated_database');require(not out.exists(),'new_private_credential_file')
 before=snapshot(db);tables=before['tables'];required={'pastefy_users':{'id','name','unique_name','email','auth_id','auth_provider','type','created_at','updated_at'},'pastefy_auth_keys':{'key','user_id','type','created_at','updated_at'}}
 for table,columns in required.items():
  require(table in tables,'original_identity_table',table=table)
  require(columns<=set(x[1] for x in tables[table]['columns']),'original_identity_columns',table=table)
  require(not tables[table]['rows'],'empty_identity_fixture',table=table)
 for table,detail in tables.items():
  if table!='sqlite_sequence':require(not detail['rows'],'empty_disposable_database',table=table)
 user='study001';token=secrets.token_urlsafe(45);stamp='2026-01-01 00:00:00'
 con=sqlite3.connect(str(db));con.execute('PRAGMA foreign_keys=ON')
 try:
  con.execute('BEGIN IMMEDIATE')
  for table in required:require(con.execute('SELECT COUNT(*) FROM '+table).fetchone()[0]==0,'identity_still_empty')
  con.execute('INSERT INTO pastefy_users(id,name,unique_name,email,auth_id,auth_provider,type,created_at,updated_at) VALUES(?,?,?,?,?,?,?,?,?)',(user,'Disposable Study User','disposable-study','study@example.invalid','disposable-study','OIDC','USER',stamp,stamp))
  con.execute('INSERT INTO pastefy_auth_keys(key,user_id,type,created_at,updated_at) VALUES(?,?,?,?,?)',(token,user,'API',stamp,stamp))
  require(not con.execute('PRAGMA foreign_key_check').fetchall(),'fixture_foreign_keys')
  fd=os.open(str(out),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600)
  with os.fdopen(fd,'w') as f:json.dump(dict(user_id=user,api_key=token),f)
  con.commit()
 except Exception:
  con.rollback();raise
 finally:con.close()
 after=snapshot(db)
 for table in tables:
  if table not in {*required,'sqlite_sequence'}:require(tables[table]==after['tables'][table],'no_nonidentity_changes',table=table)
 require(before['schema']==after['schema'],'fixture_schema_unchanged')
 return dict(status='identity_seeded_requires_api_and_native_verification',user_id=user,credential_publication='forbidden',application_records_created=0)
if __name__=='__main__':print(json.dumps(seed(sys.argv[1],sys.argv[2])))
