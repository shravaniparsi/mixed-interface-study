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
        articles=[n for n,cols in schema.items() if {'id','slug','title','summary','content','author_id'}<=set(cols)]
        if len(users)!=1 or len(articles)!=1:raise ValueError('Ambiguous fixture tables')
        user_fields=['id','username','email','bio','image'];article_fields=['id','slug','title','description','body','author_id']
        user_rows=[dict(r) for r in db.execute('SELECT '+','.join(map(quoted,user_fields))+' FROM '+quoted(users[0])+' ORDER BY id')]
        article_select=','.join(quoted({'description':'summary','body':'content'}.get(k,k))+' AS '+quoted(k) for k in article_fields)
        rows=[dict(r) for r in db.execute('SELECT '+article_select+' FROM '+quoted(articles[0])+' ORDER BY id')]
        if len(user_rows)!=1 or user_rows[0]['email']!='pilot@example.com':raise ValueError('Unexpected fixture population')
        return {'scope':'single synthetic user and all article identities/title/body/ownership; excludes credentials, tag relations and unrelated columns',
                'tables':{'user':users[0],'article':articles[0]},'article_column_mapping':{'description':'summary','body':'content'},'read_uncommitted':db.execute('PRAGMA read_uncommitted').fetchone()[0],
                'query_only':db.execute('PRAGMA query_only').fetchone()[0], 'user':user_rows[0],'articles':rows,
                'foreign_key_violations':[list(r) for r in db.execute('PRAGMA foreign_key_check')]}


def readback_paths(fixture_slugs, immediate):
    from urllib.parse import quote
    slugs=list(fixture_slugs)
    slugs.extend(sorted({a['slug'] for a in immediate['articles']} - set(slugs)))
    return ['/api/user','/api/articles?author=pilotresearch','/api/articles'] + [
        '/api/articles/'+quote(s,safe="~()*!.'-") for s in slugs]


def summarize_states(states, payload):
    before=states['before'];after=states['immediate']
    original={a['id']:a for a in before['articles']}
    added=[a for a in after['articles'] if a['id'] not in original]
    matching=[a for a in added if all(a[k]==payload[k] for k in ('title','description','body'))
              and a['author_id']==before['user']['id']]
    return {'before_article_count':len(before['articles']),'immediate_article_count':len(after['articles']),
            'new_article_rows':added,'requested_article_fields_observed':len(added)==len(matching)==1,
            'user_preserved':all(s['user']==before['user'] for s in states.values()),
            'fixture_articles_preserved':all({a['id']:a for a in s['articles'] if a['id'] in original}==original for s in states.values()),
            'post_response_selected_state_survives_restart':after==states['after_stop']==states['after_restart'],
            'selected_state_unchanged':all(s==before for s in states.values()),
            'scope':'selected public user and article fields; excludes tag relations and unrelated database state'}


def validate_selection(root, selection):
    import json
    path=Path(root)/'manifests/realworld-boundary-registry-v1.json'
    expected_sha='dee2fee441d71283eddd68e1c5b23396d95d7a8c184d0e24468a1c5f7e1deab2'
    if sha(path)!=expected_sha:raise ValueError('Registry changed')
    registry=json.loads(path.read_bytes());ids=('article-valid','article-title-150','article-title-151')
    expected={'kind':'exposed_article_creation_database_diagnostic','registry_sha256':expected_sha,
              'cases':[next(c for c in registry['cases'] if c['candidate_id']==cid) for cid in ids],
              'repetitions':1,'primary_freeze_complete':False}
    if selection!=expected:raise ValueError('Unregistered article diagnostic selection')
