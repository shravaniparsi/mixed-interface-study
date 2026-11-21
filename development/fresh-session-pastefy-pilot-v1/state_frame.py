"""Independent logical frames for probes, fixed intervention and native continuation."""
import copy,hashlib,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'fresh-session-pastefy-v1'))
from score_edit import values,timestamp
from shlink_sqlite import typed
from source_check import require
TABLE='pastefy_pastes'
def no_probe_effect(before,after):
 require(before==after,'prediction_probe_changed_persistent_state')
 return dict(status='probe_persistent_state_unchanged')
def row_for(database,key):
 require(TABLE in database['tables'],'paste_table_present')
 table=database['tables'][TABLE];rows=[values(table,r) for r in table['rows']]
 matches=[r for r in rows if r.get('key')==typed(key)]
 require(len(matches)==1,'one_persisted_target')
 return matches[0]
def expected_write(before,key,owner,patch):
 require(set(patch)<= {'title','content'},'registered_text_patch')
 row=row_for(before,key);require(row['user_id']==typed(owner),'original_owner')
 expected=copy.deepcopy(row)
 for field,value in patch.items():
  require(isinstance(value,str),'ordinary_nonnull_replacement')
  expected[field]=typed(value)
 if 'content' in patch:
  data=patch['content'].encode();expected['length']=typed(len(data));expected['hash']=typed(hashlib.sha256(data).hexdigest())
 expected['version']=typed(row['version']['value']+1);expected['indexed_in_elastic']=typed(0)
 return row,expected

def frame(before,after,key,owner,patch):
 """Return exact/unintended, preserving evidence rather than relabeling a mismatch as timeout."""
 old,expected=expected_write(before['database'],key,owner,patch)
 actual=row_for(after['database'],key)
 timestamp_ok=timestamp(actual['updated_at'])>=timestamp(old['updated_at'])
 expected['updated_at']=actual['updated_at']
 expected_database=copy.deepcopy(before['database']);t=expected_database['tables'][TABLE]
 for i,row in enumerate(t['rows']):
  if values(t,row)['key']==typed(key):t['rows'][i]=[expected[c[1]] for c in t['columns']]
 # Row ordering is observational, not a database constraint.
 from shlink_sqlite import canonical
 t['rows'].sort(key=canonical)
 differences=[]
 if expected_database!=after['database']:differences.append('database_outside_exact_write_frame')
 if before['files']!=after['files']:differences.append('application_files_changed')
 if not timestamp_ok:differences.append('update_timestamp_regressed')
 return dict(status='exact_expected_write' if not differences else 'unintended_persistent_changes',differences=differences,target_fields_changed=[k for k in old if old[k]!=actual.get(k)],requested_patch=patch)

def check_intervention(before,after,key,owner,target,ordinary_value,arm):
 require(arm in ['sham','repair'],'registered_intervention')
 patch={} if arm=='sham' else {target:ordinary_value}
 result=frame(before,after,key,owner,patch)
 result['target_repair_persisted']=row_for(after['database'],key).get(target)==typed(ordinary_value) if arm=='repair' else None
 result['causal_branch_qualified']=result['status']=='exact_expected_write' and (arm=='sham' or result['target_repair_persisted'])
 return result
