#!/usr/bin/env python3
"""Read all SQLite tables and fixture files; snapshot with SQLite backup."""
import base64,hashlib,json,pathlib,shutil,sqlite3,sys
work=pathlib.Path(sys.argv[2]).resolve()
def encode(v):
    return {'blob_base64':base64.b64encode(v).decode()} if isinstance(v,bytes) else v
def capture():
    db=work/'data/gomodel.db';con=sqlite3.connect('file:'+str(db)+'?mode=ro',uri=True)
    con.execute('BEGIN')
    schema=con.execute("SELECT type,name,tbl_name,sql FROM sqlite_master ORDER BY type,name").fetchall()
    tables={}
    for typ,name,table,sql in schema:
        if typ!='table':continue
        quoted='"'+name.replace('"','""')+'"'
        cursor=con.execute('SELECT * FROM '+quoted)
        rows=[[encode(v) for v in row] for row in cursor.fetchall()]
        rows.sort(key=lambda row:json.dumps(row,sort_keys=True,separators=(',',':')))
        tables[name]={'columns':[x[0] for x in cursor.description],'rows':rows}
    con.close()
    files={}
    for p in sorted(work.rglob('*')):
        if not p.is_file():continue
        rel=str(p.relative_to(work))
        if rel in ['data/gomodel.db','data/gomodel.db-wal','data/gomodel.db-shm']:continue
        files[rel]={'bytes':p.stat().st_size,'sha256':hashlib.sha256(p.read_bytes()).hexdigest()}
    return {'schema':schema,'tables':tables,'files':files}
mode=sys.argv[1]
if mode=='capture':print(json.dumps(capture(),sort_keys=True))
elif mode=='checkpoint':
    target=pathlib.Path(sys.argv[3]).resolve();assert not target.exists() and target.parent==work.parent
    shutil.copytree(work,target,ignore=shutil.ignore_patterns('gomodel.db','gomodel.db-wal','gomodel.db-shm'))
    src=sqlite3.connect('file:'+str(work/'data/gomodel.db')+'?mode=ro',uri=True)
    dst=sqlite3.connect(str(target/'data/gomodel.db'));src.backup(dst);dst.close();src.close()
elif mode=='restore':
    source=pathlib.Path(sys.argv[3]).resolve();assert work.name=='work' and source.name=='checkpoint' and work.parent==source.parent
    assert (source/'data/gomodel.db').is_file();shutil.rmtree(work);shutil.copytree(source,work)
else:raise ValueError(mode)
