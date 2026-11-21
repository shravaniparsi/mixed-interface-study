import base64,copy,unittest
from shlink_metadata_cache import metadata,compare,Reader
B=lambda v:base64.b64encode(v).decode()
def entry(entity=b'Shlinkio\\Example'):
 classname=b'Doctrine\\ORM\\Mapping\\ClassMetadata'
 value=b'O:'+str(len(classname)).encode()+b':"'+classname+b'":1:{s:4:"name";s:'+str(len(entity)).encode()+b':"'+entity+b'";}'
 return dict(key=B(b'Shlink:'+entity.replace(b'\\',b'__')+b'__CLASSMETADATA__'),type='string',pttl=-1,value=B(value),dump='private')
def state(*entries):return dict(database=0,entries=list(entries))
class CacheMetadata(unittest.TestCase):
 def test_addition_and_restart_removal_are_explicit(self):
  row=entry();self.assertTrue(metadata(row));empty=state();full=state(row)
  with self.assertRaises(ValueError):compare(empty,full)
  compare(empty,full,'add_metadata');compare(full,empty,'restart_metadata')
  with self.assertRaises(ValueError):compare(full,empty,'add_metadata')
 def test_unknown_mutated_expiring_or_malformed_values_refused(self):
  row=entry()
  for fault in ['namespace','key','ttl','trailing','length','type']:
   bad=copy.deepcopy(row)
   if fault=='namespace':bad['value']=B(base64.b64decode(row['value']).replace(b'Doctrine',b'Unknown!'))
   elif fault=='key':bad['key']=B(b'Shlink:business-record')
   elif fault=='ttl':bad['pttl']=1000
   elif fault=='trailing':bad['value']=B(base64.b64decode(row['value'])+b'junk')
   elif fault=='length':bad['value']=B(base64.b64decode(row['value']).replace(b'O:34:',b'O:99:'))
   else:bad['type']='list'
   with self.subTest(fault=fault):self.assertFalse(metadata(bad))
   with self.subTest(fault=fault),self.assertRaises(ValueError):compare(state(),state(bad),'add_metadata')
  bad=copy.deepcopy(row);bad['value']=B(b'changed')
  with self.assertRaises(ValueError):compare(state(row),state(bad),'restart_metadata')
 def test_php_objects_are_only_parsed_not_executed(self):
  with self.assertRaises(ValueError):Reader(b'O:7:"Exploit":0:{}').value()
if __name__=='__main__':unittest.main()
