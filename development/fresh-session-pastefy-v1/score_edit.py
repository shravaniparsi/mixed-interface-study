"""Independent ordinary-edit database frame check; not a complete run scorer."""
import copy,datetime,hashlib,pathlib,sys
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[2]/'development/fresh-session-feasibility-v1'))
from source_check import require
from shlink_sqlite import typed

def values(table,row):return dict(zip((x[1] for x in table['columns']),row))
def timestamp(v):
 require(v['type'] in ['text','integer'],'timestamp_type')
 if v['type']=='integer':return v['value']
 return datetime.datetime.fromisoformat(v['value'].replace('Z','+00:00')).timestamp()
def score_edit(before,after,key,owner,field,replacement):
 require(field in ['title','content'],'ordinary_edit_field');require(before['schema']==after['schema'] and before['pragmas']==after['pragmas'],'schema_and_pragmas_unchanged')
 require(set(before['tables'])==set(after['tables']),'same_tables')
 table='pastefy_pastes';b=before['tables'][table];a=after['tables'][table]
 for name in before['tables']:
  if name!=table:require(before['tables'][name]==after['tables'][name],'unrelated_table_unchanged',table=name)
 require({k:v for k,v in b.items() if k!='rows'}=={k:v for k,v in a.items() if k!='rows'},'paste_metadata_unchanged')
 def partition(t):
  hit=[];rest=[]
  for row in t['rows']:
   d=values(t,row)
   (hit if d['key']==typed(key) else rest).append(d)
  require(len(hit)==1,'one_target_paste');return hit[0],rest
 old,rest=partition(b);new,after_rest=partition(a);require(rest==after_rest,'other_pastes_unchanged');require(old['user_id']==new['user_id']==typed(owner),'same_owner')
 expected=copy.deepcopy(old);expected[field]=typed(replacement)
 content=new['content'];require(content['type']=='text','ordinary_plaintext_content');raw=content['value'].encode()
 expected['length']=typed(len(raw));expected['hash']=typed(hashlib.sha256(raw).hexdigest())
 require(old['version']['type']=='integer','version_type');expected['version']=typed(old['version']['value']+1)
 require(timestamp(new['updated_at'])>=timestamp(old['updated_at']),'timestamp_monotonic');expected['updated_at']=new['updated_at']
 expected['indexed_in_elastic']=typed(0)
 require(new==expected,'exact_expected_paste_delta')
 return dict(status='ordinary_database_edit_verified',field=field,independent_cases=0)
