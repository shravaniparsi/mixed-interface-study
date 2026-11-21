"""Inventory the owned persistent tree after its application writers have stopped."""
import hashlib,os,pathlib,stat
from source_check import require
DATABASE_FILES={'data/database.sqlite','data/database.sqlite-wal','data/database.sqlite-shm','data/database.sqlite-journal'}
def inventory(root):
 root=pathlib.Path(root);require(root.is_dir() and not root.is_symlink(),'regular_state_root')
 files=[];physical=[];total=0
 for folder,dirs,names in os.walk(root,followlinks=False):
  for name in sorted(dirs+names):
   p=pathlib.Path(folder)/name;relative=p.relative_to(root).as_posix();s=p.lstat()
   require(not stat.S_ISLNK(s.st_mode),'state_symlink',path=relative)
   row=dict(path=relative,mode=stat.S_IMODE(s.st_mode),uid=s.st_uid,gid=s.st_gid,mtime_ns=s.st_mtime_ns)
   if stat.S_ISDIR(s.st_mode):row['type']='directory'
   else:
    require(stat.S_ISREG(s.st_mode),'regular_state_file',path=relative)
    require(s.st_size<=128*1024**2,'state_file_size_cap',path=relative);total+=s.st_size;require(total<=512*1024**2,'state_tree_size_cap')
    h=hashlib.sha256()
    with p.open('rb') as stream:
     for chunk in iter(lambda:stream.read(1048576),b''):h.update(chunk)
    after=p.stat();require((s.st_size,s.st_mtime_ns,s.st_ino)==(after.st_size,after.st_mtime_ns,after.st_ino),'file_changed_during_observation',path=relative)
    row.update(type='file',bytes=s.st_size,sha256=h.hexdigest())
   (physical if relative in DATABASE_FILES else files).append(row)
 require(any(r['path']=='data/database.sqlite' and r['type']=='file' for r in physical),'database_file_present')
 return dict(files=sorted(files,key=lambda r:r['path']),database_physical=sorted(physical,key=lambda r:r['path']))
def compare_non_database(before,after):
 # SQLite byte layout can differ across logically verified backups; those hashes are retained,
 # while the independent SQLite scorer must separately verify the database contents and schema.
 require(set(before)==set(after)=={'files','database_physical'},'file_inventory_sections')
 require(before['files']==after['files'],'non_database_files_changed')
 return True
