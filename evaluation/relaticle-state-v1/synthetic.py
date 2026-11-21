"""One bounded SQLite synthetic attempt, no application or secrets."""
import hashlib,json,os,pathlib,sqlite3,tempfile,time,traceback
from sqlite_state import snapshot,backup,restore,canonical
out=pathlib.Path(os.environ['SQLITE_EVIDENCE']);out.mkdir(parents=True,exist_ok=True)
report=dict(status='started',application_executed=False,scientific_cases=0,checks=[],sqlite_version=sqlite3.sqlite_version)
def save():(out/'result.json').write_text(json.dumps(report,indent=2)+'\n')
def check(name,condition):
 assert condition,name
 report['checks'].append(name);save()
def reject(name,fn):
 try:fn()
 except (AssertionError,sqlite3.DatabaseError):check(name,True);return
 raise AssertionError('Expected rejection: '+name)
start=time.monotonic();save()
try:
 with tempfile.TemporaryDirectory() as d:
  root=pathlib.Path(d);db=root/'source.sqlite';saved=root/'saved.sqlite';target=root/'target.sqlite';c=sqlite3.connect(db)
  c.executescript('''PRAGMA foreign_keys=ON; PRAGMA journal_mode=WAL;
CREATE TABLE parent(id INTEGER PRIMARY KEY AUTOINCREMENT, name TEXT UNIQUE NOT NULL);
CREATE TABLE child(id INTEGER PRIMARY KEY, parent_id INTEGER REFERENCES parent(id), txt TEXT, raw BLOB, n INTEGER, r REAL, absent TEXT DEFAULT NULL);
CREATE TABLE audit(msg TEXT);
CREATE TRIGGER changed AFTER UPDATE ON parent BEGIN INSERT INTO audit VALUES('changed'); END;
CREATE INDEX child_text ON child(txt);
CREATE TABLE keyed(k TEXT PRIMARY KEY,v TEXT) WITHOUT ROWID;
INSERT INTO parent(name) VALUES('original'); INSERT INTO keyed VALUES('k','v');''')
  c.execute('INSERT INTO child VALUES(?,?,?,?,?,?,?)',(1,1,'text\x00unicode Ω',b'\x00\xff',9223372036854775806,1.25,None));c.commit()
  original=snapshot(db);(out/'original-state.json').write_bytes(canonical(original));check('all_tables_and_sequence',set(original['tables'])=={'parent','child','audit','keyed','sqlite_sequence'})
  types={v['type'] for row in original['tables']['child']['rows'] for v in row};check('typed_cells',types=={'integer','text','blob','real','null'});check('hidden_rowid_observed',original['tables']['audit']['rowid_alias'] is not None);check('without_rowid_supported',original['tables']['keyed']['rowid_alias'] is None)
  check('foreign_key_definition',bool(original['tables']['child']['foreign_keys']));check('trigger_definition',any(s[0]=='trigger' for s in original['schema']));check('index_definition','child_text' in original['tables']['child']['index_columns'])
  h=backup(db,saved);check('wal_backup_independent',snapshot(saved)==original and h==hashlib.sha256(canonical(original)).hexdigest())
  c.execute("UPDATE parent SET name='changed'");c.execute("INSERT INTO parent(name) VALUES('second')");c.execute('DELETE FROM child');c.commit();mutated=snapshot(db);check('mutation_delete_trigger_sequence_detected',all(mutated['tables'][t]!=original['tables'][t] for t in ['parent','child','audit','sqlite_sequence']));check('backup_unchanged',snapshot(saved)==original)
  c.execute('CREATE INDEX extra ON parent(name)');c.commit();check('schema_mutation_detected',snapshot(db)['schema']!=original['schema'])
  reject('live_wal_restore_refused',lambda:restore(saved,db));c.close()
  restore(saved,db);check('restore_exact',snapshot(db)==original);restore(saved,target);check('fresh_restore_exact',snapshot(target)==original)
  c=sqlite3.connect(target);c.execute('PRAGMA foreign_keys=ON');c.execute("INSERT INTO parent(name) VALUES('next')");c.commit();check('restored_sequence_behavior',c.execute("SELECT id FROM parent WHERE name='next'").fetchone()==(2,));c.execute("UPDATE parent SET name='next-updated' WHERE id=2");c.commit();check('restored_trigger_behavior',c.execute('SELECT msg FROM audit').fetchall()==[('changed',)])
  reject('restored_fk_enforced',lambda:c.execute('INSERT INTO child(id,parent_id) VALUES(2,999)'));c.rollback();c.execute('CREATE VIEW unsupported AS SELECT * FROM parent');c.commit();reject('views_rejected',lambda:snapshot(target));c.close()
  c=sqlite3.connect(root/'virtual.sqlite');c.execute('CREATE VIRTUAL TABLE items USING fts5(body)');c.commit();c.close();reject('virtual_tables_rejected',lambda:snapshot(root/'virtual.sqlite'))
 report['status']='synthetic_passed'
except Exception as e:
 report.update(status='synthetic_failed',error_type=type(e).__name__,error=str(e));(out/'traceback.txt').write_text(traceback.format_exc())
finally:report['elapsed_seconds']=time.monotonic()-start;save()
print(json.dumps(report));raise SystemExit(0 if report['status']=='synthetic_passed' else 1)
