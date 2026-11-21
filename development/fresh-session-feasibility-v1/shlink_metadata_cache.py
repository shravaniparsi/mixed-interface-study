"""Non-executing PHP metadata reader; never hydrate PHP objects or evaluate code."""
import base64,re
from source_check import require
from shlink_redis import logical
class Reader:
 def __init__(self,data):self.data=data;self.pos=0;self.nodes=0
 def take(self,n):
  require(0<=n<=len(self.data)-self.pos,'serialized_length');v=self.data[self.pos:self.pos+n];self.pos+=n;return v
 def expect(self,s):require(self.take(len(s))==s,'serialized_delimiter')
 def number(self,ending):
  end=self.data.find(ending,self.pos);require(end>=0 and end-self.pos<=30,'serialized_number');v=self.data[self.pos:end];self.pos=end+len(ending);return int(v)
 def string(self):
  length=self.number(b':');self.expect(b'"');s=self.take(length);self.expect(b'"');return s
 def value(self,depth=0):
  self.nodes+=1;require(depth<80 and self.nodes<100000,'serialized_complexity');kind=self.take(1)
  if kind==b'N':self.expect(b';');return None
  self.expect(b':')
  if kind in [b'i',b'b',b'r',b'R']:return self.number(b';')
  if kind==b'd':
   end=self.data.find(b';',self.pos);require(end>=0 and end-self.pos<100,'serialized_float');v=float(self.data[self.pos:end]);self.pos=end+1;return v
  if kind==b's':v=self.string();self.expect(b';');return v
  if kind==b'E':
   v=self.string();self.expect(b';');require(v.startswith(b'Doctrine\\ORM\\') or v in {b'SortDirection:Ascending',b'SortDirection:Descending'},'metadata_enum_namespace');return v
  if kind==b'O':
   name=self.string();require(name.startswith(b'Doctrine\\ORM\\'),'metadata_object_namespace');self.expect(b':');n=self.number(b':');self.expect(b'{');require(0<=n<10000,'metadata_properties');props=[]
   for _ in range(n):props.append((self.value(depth+1),self.value(depth+1)))
   self.expect(b'}');return dict(class_name=name,properties=props)
  if kind==b'a':
   n=self.number(b':');require(0<=n<10000,'metadata_array');self.expect(b'{');v=[]
   for _ in range(n):v.append((self.value(depth+1),self.value(depth+1)))
   self.expect(b'}');return v
  raise ValueError('Unsupported PHP metadata token')
def metadata(entry):
 if entry['type']!='string' or entry['pttl']!=-1:return False
 key=base64.b64decode(entry['key'],validate=True)
 is_query=re.fullmatch(rb'Shlink:[a-f0-9]{32}',key) is not None
 is_class=re.fullmatch(rb'Shlink:Shlinkio__[A-Za-z0-9_]+__CLASSMETADATA__',key) is not None
 if not (is_query or is_class):return False
 try:
  data=base64.b64decode(entry['value'],validate=True);require(len(data)<=4*1024**2,'metadata_size');r=Reader(data);obj=r.value();require(r.pos==len(data),'complete_metadata')
  expected=b'Doctrine\\ORM\\Query\\ParserResult' if is_query else b'Doctrine\\ORM\\Mapping\\ClassMetadata'
  require(isinstance(obj,dict) and obj['class_name']==expected,'metadata_root_class')
  if is_class:
   props=dict(obj['properties']);entity=props[b'name'];require(key==b'Shlink:'+entity.replace(b'\\',b'__')+b'__CLASSMETADATA__','metadata_entity_key')
  return True
 except (ValueError,KeyError,TypeError):return False

def compare(before,after,mode='exact'):
 left={r['key']:r for r in logical(before)['entries']};right={r['key']:r for r in logical(after)['entries']}
 require(mode in {'exact','add_metadata','restart_metadata'},'known_cache_comparison')
 for key in set(left)&set(right):require(left[key]==right[key],'existing_redis_value_unchanged')
 added=set(right)-set(left);removed=set(left)-set(right)
 if mode=='exact':require(not added and not removed,'redis_frame')
 else:
  require(all(metadata(right[k]) for k in added),'only_metadata_cache_additions')
  require(not removed or mode=='restart_metadata' and all(metadata(left[k]) for k in removed),'only_restart_metadata_removal')
 return dict(added_metadata=len(added),removed_metadata=len(removed))
