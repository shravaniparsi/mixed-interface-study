import copy,hashlib,unittest
from score_create import score_create,score_files
from shlink_sqlite import typed
class Creation(unittest.TestCase):
 def pair(self):
  row=dict(folder=None,expire_at=None,title='title',content='text',user_id='study001',forked_from=None,encrypted=0,type='PASTE',visibility='UNLISTED',storage_type='DATABASE',version=1,indexed_in_elastic=0,length=4,hash=hashlib.sha256(b'text').hexdigest(),key='abcdefgh',id=1,created_at='2026-01-01 00:00:00',updated_at='2026-01-01 00:00:00')
  b=dict(schema=[],pragmas={},tables={'pastefy_pastes':dict(columns=[[i,k] for i,k in enumerate(row)],rows=[]),'other':dict(rows=[]) });a=copy.deepcopy(b);a['tables']['pastefy_pastes']['rows']=[[typed(v) for v in row.values()]];return b,a,list(row)
 def test_valid_insert_and_wrong_defaults_or_owner(self):
  b,a,c=self.pair();score_create(b,a,'abcdefgh','study001','title','text')
  for col,value in [('user_id','other'),('encrypted',1),('length',5),('version',2),('title','changed')]:
   d=copy.deepcopy(a);d['tables']['pastefy_pastes']['rows'][0][c.index(col)]=typed(value)
   with self.subTest(col=col),self.assertRaises(ValueError):score_create(b,d,'abcdefgh','study001','title','text')
 def test_unrelated_write_refused(self):
  b,a,c=self.pair();a['tables']['other']['rows']=[1]
  with self.assertRaises(ValueError):score_create(b,a,'abcdefgh','study001','title','text')
 def test_file_changes_refused_except_sqlite_physical(self):
  f=dict(kind='file',mode=384,sha256='a');score_files({'study.sqlite':f},{'study.sqlite':dict(f,sha256='b')})
  with self.assertRaises(ValueError):score_files({}, {'unexpected':f})
if __name__=='__main__':unittest.main()
