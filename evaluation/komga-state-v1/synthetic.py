"""Registered SQLite-family attempt2; original JDBC, no application server."""
import argparse,hashlib,json,pathlib,sqlite3,time,traceback
from state import Observer,snapshot,canonical

def main():
 ap=argparse.ArgumentParser();ap.add_argument('--classpath',required=True);ap.add_argument('--out',required=True);ap.add_argument('--work',required=True);a=ap.parse_args()
 out=pathlib.Path(a.out);out.mkdir(parents=True,exist_ok=True);work=pathlib.Path(a.work);work.mkdir(parents=True,exist_ok=True)
 observer=Observer(a.classpath,work/'jdbc');checks=[];report={'attempt':2,'family':'sqlite','application_started':False,'checks':checks,'status':'started'};t=time.monotonic();writer=None
 def save():(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
 def check(name,ok):
  checks.append({'name':name,'passed':bool(ok)});save();assert ok,name
 def refuses(name,fn):
  try:fn()
  except (AssertionError,RuntimeError,sqlite3.DatabaseError):check(name,True)
  else:check(name,False)
 try:
  stores={k:work/(k+'.sqlite') for k in ['main','tasks','sessions']}
  fixture=work/'fixture.sql';fixture.write_text('''PRAGMA foreign_keys=ON;
CREATE TABLE parent(id INTEGER PRIMARY KEY AUTOINCREMENT, label TEXT COLLATE COLLATION_UNICODE_1 UNIQUE);
CREATE TABLE child(parent_id INTEGER REFERENCES parent(id), tag TEXT);
CREATE TABLE raw(n, t TEXT, b BLOB, i INTEGER, r REAL);
CREATE TABLE keyed(k TEXT PRIMARY KEY COLLATE COLLATION_UNICODE_3, value TEXT) WITHOUT ROWID;
CREATE TABLE audit(event TEXT);
CREATE TRIGGER parent_audit AFTER INSERT ON parent BEGIN INSERT INTO audit VALUES('inserted'); END;
INSERT INTO parent(label) VALUES('Alpha');
INSERT INTO parent(label) VALUES('Zulu');
INSERT INTO child VALUES(1,'linked');
INSERT INTO raw VALUES(NULL,'text',X'00FF',9223372036854775807,1.25);
INSERT INTO keyed VALUES('K','value');
''')
  for k,p in stores.items():observer.jdbc('fixture',p,fixture)
  initial={k:snapshot(p) for k,p in stores.items()}
  check('three_store_schema_and_rows',all(set(s['tables'])=={'parent','child','raw','keyed','audit','sqlite_sequence'} for s in initial.values()))
  raw=initial['main']['tables']['raw']['rows'][0]
  check('typed_null_text_blob_integer_real',[v['type'] for v in raw]==['integer','null','text','blob','integer','real'])
  check('integer_precision',raw[4]['value']==9223372036854775807)
  check('blob_identity',raw[3]['value']=='AP8=')
  check('without_rowid',initial['main']['tables']['keyed']['rowid_alias'] is None)
  check('original_custom_collation_integrity',all(observer.jdbc('integrity',p).startswith('integrity_ok') for p in stores.values()))
  check('trigger_and_sequence',len(initial['main']['tables']['audit']['rows'])==2 and bool(initial['main']['tables']['sqlite_sequence']['rows']))
  writer=sqlite3.connect(stores['main']);writer.execute('PRAGMA journal_mode=WAL');writer.execute("INSERT INTO raw VALUES(NULL,'wal',X'01',3,2.5)");writer.commit()
  check('wal_present',pathlib.Path(str(stores['main'])+'-wal').exists())
  checkpoint=work/'checkpoint';expected=observer.capture(stores,checkpoint)
  check('coherent_three_store_capture',expected=={k:snapshot(p) for k,p in stores.items()})
  refuses('live_wal_restore_refused',lambda:observer.restore(checkpoint,stores))
  writer.close();writer=None
  with sqlite3.connect(stores['tasks']) as c:c.execute("UPDATE raw SET t='changed'")
  with sqlite3.connect(stores['sessions']) as c:c.execute('DELETE FROM raw')
  with sqlite3.connect(stores['main']) as c:c.execute('ALTER TABLE raw ADD COLUMN extra TEXT')
  check('all_three_store_changes_detected',all(snapshot(stores[k])!=expected[k] for k in stores))
  check('backup_independence',all(snapshot(checkpoint/(k+'.sqlite'))==expected[k] for k in stores))
  restored=observer.restore(checkpoint,stores);check('exact_complete_restore',restored==expected)
  script=work/'after.sql';script.write_text("PRAGMA foreign_keys=ON;\nINSERT INTO parent(label) VALUES('Omega');\n")
  observer.jdbc('fixture',stores['main'],script);after=snapshot(stores['main'])
  check('restored_trigger_and_sequence',len(after['tables']['audit']['rows'])==3 and any(row[1]['value']==3 for row in after['tables']['parent']['rows']))
  bad=work/'bad.sql';bad.write_text("PRAGMA foreign_keys=ON;\nINSERT INTO child VALUES(999,'bad');\n")
  refuses('restored_foreign_key_enforced',lambda:observer.jdbc('fixture',stores['main'],bad))
  old=(checkpoint/'main.sqlite').read_bytes();(checkpoint/'main.sqlite').write_bytes(b'X'+old[1:])
  before={k:snapshot(p) for k,p in stores.items()}
  refuses('corrupt_checkpoint_refused_before_restore',lambda:observer.restore(checkpoint,stores))
  check('corrupt_restore_did_not_mutate_destinations',before=={k:snapshot(p) for k,p in stores.items()})
  (checkpoint/'main.sqlite').write_bytes(old)
  observer.restore(checkpoint,stores)
  check('final_restore_integrity',all(observer.jdbc('integrity',p).startswith('integrity_ok') for p in stores.values()))
  report.update(status='synthetic_passed',logical_sha256={k:hashlib.sha256(canonical(v)).hexdigest() for k,v in expected.items()})
 except Exception as e:
  report.update(status='synthetic_unavailable',error_type=type(e).__name__,error=str(e));(out/'traceback.txt').write_text(traceback.format_exc())
 finally:
  if writer is not None:writer.close()
  report['elapsed_seconds']=time.monotonic()-t;save()
 print(json.dumps({'status':report['status'],'checks':len(checks)}));return 0 if report['status']=='synthetic_passed' else 1
if __name__=='__main__':raise SystemExit(main())
