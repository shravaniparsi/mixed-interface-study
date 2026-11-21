"""Seed only disposable identity in an original MySQL-migrated database."""
import json,os,secrets
from source_check import require

def seed(state,out):
 before=state.snapshot();required={'pastefy_users':{'id','name','unique_name','email','auth_id','auth_provider','type','created_at','updated_at'},'pastefy_auth_keys':{'key','user_id','type','created_at','updated_at'}}
 require(not out.exists(),'new_private_credentials')
 for table,cols in required.items():require(table in before['tables'] and cols<=set(c[1] for c in before['tables'][table]['columns']),'original_identity_columns',table=table)
 require(all(not t['rows'] for t in before['tables'].values()),'empty_disposable_database')
 token=secrets.token_urlsafe(45);user='study001';stamp='2026-01-01 00:00:00';con=state.connection()
 try:
  with con.cursor() as c:
   c.execute('INSERT INTO pastefy_users(id,name,unique_name,email,auth_id,auth_provider,type,created_at,updated_at) VALUES(%s,%s,%s,%s,%s,%s,%s,%s,%s)',(user,'Disposable Study User','disposable-study','study@example.invalid','disposable-study','OIDC','USER',stamp,stamp))
   c.execute('INSERT INTO pastefy_auth_keys(`key`,user_id,type,created_at,updated_at) VALUES(%s,%s,%s,%s,%s)',(token,user,'API',stamp,stamp))
  con.commit()
 except Exception:con.rollback();raise
 finally:con.close()
 after=state.snapshot();require(before['schema']==after['schema'],'fixture_schema_unchanged')
 for name,table in before['tables'].items():
  if name not in required:require(table==after['tables'][name] and before['sequences'][name]==after['sequences'][name],'nonidentity_unchanged',table=name)
 with os.fdopen(os.open(str(out),os.O_WRONLY|os.O_CREAT|os.O_EXCL,0o600),'w') as f:json.dump(dict(user_id=user,api_key=token),f)
 return dict(status='identity_seeded_requires_api_and_native_verification',user_id=user,application_records_created=0,database='mysql')
