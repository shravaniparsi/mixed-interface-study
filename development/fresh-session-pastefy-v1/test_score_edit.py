import copy,hashlib,unittest
from score_edit import score_edit
from shlink_sqlite import typed
class EditFrame(unittest.TestCase):
 def evidence(self):
  row=dict(key='abcd',user_id='study001',title='old',content='text',length=4,hash=hashlib.sha256(b'text').hexdigest(),version=1,updated_at='2026-01-01 00:00:00',indexed_in_elastic=0)
  table=dict(columns=[[i,k] for i,k in enumerate(row)],rows=[[typed(v) for v in row.values()]],indexes=[])
  b=dict(schema=[],pragmas={},tables={'pastefy_pastes':table,'other':{'rows':[]}});a=copy.deepcopy(b);cols=list(row)
  for k,v in dict(title='new',version=2,updated_at='2026-01-01 00:00:01').items():a['tables']['pastefy_pastes']['rows'][0][cols.index(k)]=typed(v)
  return b,a,cols
 def test_valid_edit_and_unrelated_change_rejected(self):
  b,a,c=self.evidence();score_edit(b,a,'abcd','study001','title','new');a['tables']['other']['rows']=[1]
  with self.assertRaises(ValueError):score_edit(b,a,'abcd','study001','title','new')
 def test_wrong_owner_hash_version_and_collateral_content_rejected(self):
  for col,value in [('user_id','other'),('hash','bad'),('version',3),('content','unexpected')]:
   b,a,c=self.evidence();a['tables']['pastefy_pastes']['rows'][0][c.index(col)]=typed(value)
   with self.subTest(column=col),self.assertRaises(ValueError):score_edit(b,a,'abcd','study001','title','new')
if __name__=='__main__':unittest.main()
