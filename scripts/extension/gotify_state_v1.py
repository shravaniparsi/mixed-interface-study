"""Read all SQLite tables consistently without editing the study database."""
import json
import sqlite3
import sys
from pathlib import Path


def read_state(path):
    # mode=ro still observes WAL commits. immutable=1 would incorrectly ignore WAL.
    db = sqlite3.connect(Path(path).resolve().as_uri() + '?mode=ro', uri=True)
    try:
        db.execute('BEGIN')
        schema = db.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name").fetchall()
        tables = {}
        for (name,) in db.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name").fetchall():
            quoted = '"' + name.replace('"', '""') + '"'
            cursor = db.execute('SELECT * FROM ' + quoted)
            rows = [[{'sqlite_blob_hex': v.hex()} if isinstance(v, bytes) else v for v in row] for row in cursor]
            rows.sort(key=lambda row: json.dumps(row, ensure_ascii=False, sort_keys=True))
            tables[name] = {'columns': [c[0] for c in cursor.description], 'rows': rows}
        return {'schema': schema, 'tables': tables}
    finally:
        db.close()


if __name__ == '__main__':
    print(json.dumps(read_state(sys.argv[1]), sort_keys=True, ensure_ascii=False))
