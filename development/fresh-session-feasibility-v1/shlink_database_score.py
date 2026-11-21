"""Independent Shlink database-frame checks. Files, caches and requests need separate gates."""
import base64,copy,hashlib
from urllib.parse import quote
from source_check import require
from shlink_sqlite import canonical,typed

def decode(cell):
 require(set(cell)=={'type','value'},'typed_cell_shape');kind,value=cell['type'],cell['value']
 if kind=='null':require(value is None,'null_cell');return None
 if kind=='integer':require(type(value) is int,'integer_cell');return value
 if kind=='text':require(isinstance(value,str),'text_cell');return value
 if kind=='blob':return base64.b64decode(value,validate=True)
 if kind=='real':return float.fromhex(value)
 raise ValueError('unsupported cell type')
def records(db,table):
 t=db['tables'][table];names=[c[1] for c in t['columns']]
 require(len(names)==len(set(names)),'unique_columns')
 out=[]
 for r in t['rows']:
  require(len(r)==len(names),'row_width');out.append(dict(zip(names,map(decode,r))))
 return out

def normalized(db):
 db=copy.deepcopy(db);require(set(db)=={'schema','tables','pragmas'},'database_sections')
 schema_tables={s[1] for s in db['schema'] if s[0]=='table'}
 require(set(db['tables'])==schema_tables,'complete_table_inventory')
 for name,table in db['tables'].items():
  require(set(table)=={'columns','foreign_keys','indexes','index_columns','rows'},'table_sections')
  records(db,name);table['rows'].sort(key=canonical)
 return db

def locate(db,identity):
 matches=[(i,r) for i,r in enumerate(records(db,'short_urls')) if r['id']==identity]
 require(len(matches)==1,'unique_short_url');return matches[0]
def change(db,identity,column,value):
 index,_=locate(db,identity);names=[c[1] for c in db['tables']['short_urls']['columns']]
 db['tables']['short_urls']['rows'][index][names.index(column)]=typed(value)

def ordinary_record(db,identity,actor,body):
 _,r=locate(db,identity)
 require(r['author_api_key_id']==actor,'author_key_identity')
 require(r['domain_id'] is None,'ordinary_default_domain')
 require(r['original_url']==body['longUrl'] and r['title']==body['title'],'ordinary_fields')
 require(r['long_url_hash']==hashlib.sha256(body['longUrl'].encode()).digest(),'derived_url_hash')
 require(r['title_was_auto_resolved']==0 and r['forward_query']==1,'ordinary_flags')
 require(body['tags']==[] and body['forwardQuery'] is True,'ordinary_tags_and_forward_query')
 tags=records(db,'short_urls_in_tags');require(not any(x['short_url_id']==identity for x in tags),'record_has_no_tags')
 return r

def edit(before,after,identity,actor,changes,request):
 expected=normalized(before);actual=normalized(after);_,prior=locate(expected,identity)
 require(prior['author_api_key_id']==actor,'same_actor')
 require(request['method']=='PATCH' and request['path']=='/rest/v3/short-urls/'+quote(prior['short_code'],safe=''),'original_edit_route')
 require(prior['title_was_auto_resolved']==0,'explicit_title_fixture')
 require(set(changes)<= {'/longUrl','/title'} and bool(changes),'selected_fields_only')
 for pointer,value in changes.items():
  require(isinstance(value,str) and value,'ordinary_string')
  require(request['body'][pointer[1:]]==value,'native_request_expected_field')
  if pointer=='/title':change(expected,identity,'title',value)
  else:
   change(expected,identity,'original_url',value);change(expected,identity,'long_url_hash',hashlib.sha256(value.encode()).digest())
 require(normalized(expected)==actual,'edit_database_frame')
 return True

def creation(before,after,identity,actor,body):
 before=normalized(before);after=normalized(after)
 require(not any(r['id']==identity for r in records(before,'short_urls')),'new_record_identity')
 created=ordinary_record(after,identity,actor,body);index,_=locate(after,identity);after['tables']['short_urls']['rows'].pop(index)
 # SQLite's own identity sequence is the only declared insertion side effect besides the row.
 if 'sqlite_sequence' in before['tables']:
  old=records(before,'sqlite_sequence');new=records(after,'sqlite_sequence')
  old_row=[r for r in old if r['name']=='short_urls'];new_row=[r for r in new if r['name']=='short_urls']
  require(len(old_row)<=1 and len(new_row)==1,'short_url_sequence_identity')
  require(type(identity) is int and new_row[0]['seq']==identity,'sequence_matches_inserted_id')
  require(identity==(old_row[0]['seq'] if old_row else 0)+1,'ordinary_sequence_increment')
  names=[c[1] for c in after['tables']['sqlite_sequence']['columns']];name_index=names.index('name')
  after['tables']['sqlite_sequence']['rows']=[r for r in after['tables']['sqlite_sequence']['rows'] if decode(r[name_index])!='short_urls']
  after['tables']['sqlite_sequence']['rows'] += [r for r in before['tables']['sqlite_sequence']['rows'] if decode(r[name_index])=='short_urls']
 require(normalized(after)==before,'creation_database_frame')
 return created
