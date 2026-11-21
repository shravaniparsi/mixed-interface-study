"""Exercise real MySQL observation/reset before attempting application workflows."""
import json,pathlib,sys
from mysql_state import MySQLState
from source_check import require

def main(base):
 state=MySQLState(pathlib.Path(base));report=dict(status='running')
 try:
  state.start_database();con=state.connection()
  try:
   with con.cursor() as c:
    c.execute('CREATE TABLE probe (id INT PRIMARY KEY AUTO_INCREMENT, value TEXT, amount INT, stamp DATETIME, optional TEXT NULL)')
    c.execute("INSERT INTO probe(value,amount,stamp) VALUES (%s,%s,%s)",('ordinary é',7,'2026-01-01 00:00:00'))
   con.commit()
  finally:con.close()
  original=state.snapshot();(state.live/'fixture.txt').write_text('original');state.checkpoint()
  con=state.connection()
  try:
   with con.cursor() as c:c.execute("UPDATE probe SET value='changed'");c.execute("INSERT INTO probe(value) VALUES ('extra')")
   con.commit()
  finally:con.close()
  (state.live/'fixture.txt').write_text('changed');require(state.snapshot()!=original,'smoke_mutation_observed');state.restore();require(state.snapshot()==original and (state.live/'fixture.txt').read_text()=='original','smoke_reset_verified')
  state.restore();require(state.snapshot()==original,'smoke_repeat_reset_verified');report.update(status='mysql_reset_smoke_passed',rows=1,reset_cycles=2,settings=original['pragmas'])
 finally:
  state.close_database();report['database_stopped']=state.db_process is None or state.db_process.poll() is not None;print(json.dumps(report))
if __name__=='__main__':main(sys.argv[1])
