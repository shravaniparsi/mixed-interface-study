"""Checkpoint an exclusively owned, stopped SQLite runtime directory.
Caller must own and track every writer process; runtime isolation is a separate gate.
"""
import hashlib,json,pathlib,shutil,stat,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/'development/fresh-session-feasibility-v1'))
from source_check import require
from shlink_sqlite import snapshot,canonical

def inventory(root):
 rows={}
 for p in sorted(root.rglob('*')):
  require(not p.is_symlink(),'no_state_symlinks')
  mode=p.stat().st_mode;require(stat.S_ISREG(mode) or stat.S_ISDIR(mode),'regular_state_entry')
  rows[str(p.relative_to(root))]=dict(mode=stat.S_IMODE(mode),kind='directory' if p.is_dir() else 'file',sha256=None if p.is_dir() else hashlib.sha256(p.read_bytes()).hexdigest())
 return rows
class State:
 def __init__(self,base):
  self.base=pathlib.Path(base);require(not self.base.exists(),'fresh_owned_state_base');self.base.mkdir(mode=0o700)
  self.live=self.base/'live';self.live.mkdir();self.writers=[]
 def track(self,process):
  require(process not in self.writers,'unique_writer');self.writers.append(process)
 def stopped(self):
  require(all(p.poll() is not None for p in self.writers),'all_tracked_writers_stopped')
 def observe(self,root):
  require(not root.is_symlink() and root.is_dir(),'owned_state_directory')
  before=inventory(root);db=snapshot(root/'study.sqlite');require(before==inventory(root),'observation_did_not_change_files')
  return dict(files=before,database_sha256=hashlib.sha256(canonical(db)).hexdigest())
 def checkpoint(self,label="root"):
  require(label in ["root","native","api"],"registered_checkpoint_label")
  self.stopped();dest=self.base/('checkpoint-'+label);require(not dest.exists(),'single_checkpoint')
  before=self.observe(self.live);shutil.copytree(self.live,dest);require(self.observe(dest)==before==self.observe(self.live),'checkpoint_equal')
  (self.base/('checkpoint-'+label+'.json')).write_bytes(canonical(before));return before
 def restore(self,label="root"):
  require(label in ["root","native","api"],"registered_checkpoint_label")
  self.stopped();saved=json.loads((self.base/('checkpoint-'+label+'.json')).read_text());root=self.base/('checkpoint-'+label)
  require(self.observe(root)==saved,'checkpoint_not_tampered')
  pending=self.base/'restore-pending';old=self.base/'previous'
  require(not pending.exists() and not old.exists(),'restore_destinations_unused')
  require(self.live.is_dir() and not self.live.is_symlink(),'live_is_owned_directory')
  shutil.copytree(root,pending);require(self.observe(pending)==saved,'restored_copy_equal')
  self.live.rename(old);pending.rename(self.live)
  require(self.observe(self.live)==saved,'restored_live_equal');shutil.rmtree(old)
  return saved
