"""Independent ordinary creation frame, binding API ID to one persisted owner row."""
import hashlib,pathlib,re,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/'development/fresh-session-feasibility-v1'))
from source_check import require
from shlink_sqlite import typed
from score_edit import values,timestamp

def score_create(before,after,key,owner,title,content):
 require(before['schema']==after['schema'] and before['pragmas']==after['pragmas'],'creation_schema_unchanged')
 require(set(before['tables'])==set(after['tables']),'creation_same_tables')
 target='pastefy_pastes';b=before['tables'][target];a=after['tables'][target]
 require({k:v for k,v in b.items() if k!='rows'}=={k:v for k,v in a.items() if k!='rows'},'paste_structure_unchanged')
 old=[values(b,x) for x in b['rows']];new=[values(a,x) for x in a['rows']];hit=[x for x in new if x['key']==typed(key)]
 require(len(hit)==1 and not any(x['key']==typed(key) for x in old),'one_new_key')
 require([x for x in new if x['key']!=typed(key)]==old,'existing_pastes_unchanged');row=hit[0]
 require(re.fullmatch('[A-Za-z0-9]{8}',key) is not None,'original_key_shape')
 require(row['id']['type']=='integer' and row['id']['value']>0,'allocated_integer_id')
 require(timestamp(row['updated_at'])>=timestamp(row['created_at']),'creation_timestamp_order')
 expected={k:typed(v) for k,v in dict(folder=None,expire_at=None,title=title,content=content,user_id=owner,forked_from=None,encrypted=0,type='PASTE',visibility='UNLISTED',storage_type='DATABASE',version=1,indexed_in_elastic=0,length=len(content.encode()),hash=hashlib.sha256(content.encode()).hexdigest(),key=key).items()}
 expected.update(id=row['id'],created_at=row['created_at'],updated_at=row['updated_at']);require(row==expected,'complete_created_row_matches_original_defaults')
 for name in before['tables']:
  if name==target:continue
  if name=='sqlite_sequence':
   left=before['tables'][name];right=after['tables'][name]
   require({k:v for k,v in left.items() if k!='rows'}=={k:v for k,v in right.items() if k!='rows'},'sequence_metadata')
   def split(t):return [values(t,x) for x in t['rows']]
   ls,rs=split(left),split(right);require([x for x in ls if x['name']!=typed(target)]==[x for x in rs if x['name']!=typed(target)],'other_sequences_unchanged')
   seq=[x for x in rs if x['name']==typed(target)];require(len(seq)==1 and seq[0]['seq']==row['id'],'target_sequence_matches_insert')
  else:require(before['tables'][name]==after['tables'][name],'other_creation_tables_unchanged',table=name)
 return dict(status='ordinary_database_creation_verified',key=key,independent_cases=0)

def score_files(before,after):
 # SQLite logical state is scored separately; no other file effects are allowed.
 physical={'study.sqlite','study.sqlite-wal','study.sqlite-shm','study.sqlite-journal'}
 require({k:v for k,v in before.items() if k not in physical}=={k:v for k,v in after.items() if k not in physical},'non_database_files_unchanged')
 for rows in [before,after]:
  for name,value in rows.items():
   if name in physical:require(value['kind']=='file','sqlite_artifact_regular')
 return dict(status='non_database_files_unchanged')
