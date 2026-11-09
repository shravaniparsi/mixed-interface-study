"""Read committed synthetic fixture state through independent read-only SQLite connections."""
import hashlib,sqlite3
from contextlib import closing
from pathlib import Path


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()
def quoted(name):return '"'+name.replace('"','""')+'"'
def connect(path):
    db=sqlite3.connect(Path(path).resolve().as_uri()+'?mode=ro',uri=True,timeout=10)
    db.execute('PRAGMA query_only=ON');db.execute('PRAGMA read_uncommitted=OFF');return db


def backup(source,destination):
    destination=Path(destination)
    if destination.exists():raise ValueError('Snapshot already exists')
    with closing(connect(source)) as src,closing(sqlite3.connect(destination)) as dst:src.backup(dst)
    return {'file':destination.name,'sha256':sha(destination),'projection':project(destination)}


def project(path):
    with closing(connect(path)) as db:
        db.row_factory=sqlite3.Row;db.execute('BEGIN')
        tables=[r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")]
        schema={n:[r['name'] for r in db.execute('PRAGMA table_info('+quoted(n)+')')] for n in tables}
        users=[n for n,cols in schema.items() if {'id','username','email','password','bio','image'}<=set(cols)]
        articles=[n for n,cols in schema.items() if {'id','slug','title','description','body','author_id'}<=set(cols)]
        if len(users)!=1 or len(articles)!=1:raise ValueError('Ambiguous fixture tables')
        user_fields=['id','username','email','bio','image'];article_fields=['id','slug','title','description','body','author_id']
        user_rows=[dict(r) for r in db.execute('SELECT '+','.join(map(quoted,user_fields))+' FROM '+quoted(users[0])+' ORDER BY id')]
        rows=[dict(r) for r in db.execute('SELECT '+','.join(map(quoted,article_fields))+' FROM '+quoted(articles[0])+' ORDER BY id')]
        if len(user_rows)!=1 or user_rows[0]['email']!='pilot@example.com' or len(rows)!=3:raise ValueError('Unexpected fixture population')
        if any(r['author_id']!=user_rows[0]['id'] for r in rows):raise ValueError('Article ownership differs')
        return {'scope':'single synthetic user identity and three fixture article identities/bodies/ownership; excludes credentials and unrelated columns',
                'tables':{'user':users[0],'article':articles[0]},'read_uncommitted':db.execute('PRAGMA read_uncommitted').fetchone()[0],
                'query_only':db.execute('PRAGMA query_only').fetchone()[0], 'user':user_rows[0],'articles':rows,
                'foreign_key_violations':[list(r) for r in db.execute('PRAGMA foreign_key_check')]}
