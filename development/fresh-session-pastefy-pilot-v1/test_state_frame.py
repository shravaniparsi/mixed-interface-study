import copy,hashlib,unittest
from state_frame import frame,check_intervention,no_probe_effect,typed

def observation(content='text'):
 row=dict(id=1,key='abcdefgh',user_id='study001',title='note',content=content,length=0 if content is None else len(content.encode()),hash=None if content is None else hashlib.sha256(content.encode()).hexdigest(),version=1,indexed_in_elastic=0,created_at='2026-01-01 00:00:00',updated_at='2026-01-01 00:00:00')
 table=dict(columns=[[i,k] for i,k in enumerate(row)],rows=[[typed(v) for v in row.values()]])
 return dict(database=dict(schema=['original'],pragmas={},sequences={'pastefy_pastes':2},tables={'pastefy_pastes':table,'other':{'columns':[],'rows':[]}}),files={'.env':{'sha256':'fixed'}})
def update(ob,**changes):
 out=copy.deepcopy(ob);t=out['database']['tables']['pastefy_pastes'];changes={'version':2,'updated_at':'2026-01-01 00:00:01',**changes}
 for k,v in changes.items():t['rows'][0][next(i for i,c in enumerate(t['columns']) if c[1]==k)]=typed(v)
 return out
class Frames(unittest.TestCase):
 def test_sham_only_original_save_metadata(self):
  before=observation();self.assertTrue(check_intervention(before,update(before),'abcdefgh','study001','title','ordinary','sham')['causal_branch_qualified'])
 def test_null_content_repair_requires_matching_metadata(self):
  before=observation(None);after=update(before,content='ordinary',length=8,hash=hashlib.sha256(b'ordinary').hexdigest())
  self.assertTrue(check_intervention(before,after,'abcdefgh','study001','content','ordinary','repair')['causal_branch_qualified'])
  after=update(before,content='ordinary');self.assertFalse(check_intervention(before,after,'abcdefgh','study001','content','ordinary','repair')['causal_branch_qualified'])
 def test_extra_field_and_other_table_mutations_detected(self):
  before=observation();after=update(before,title='edited',content='unexpected');self.assertEqual(frame(before,after,'abcdefgh','study001',{'title':'edited'})['status'],'unintended_persistent_changes')
  after=update(before,title='edited');after['database']['tables']['other']['rows']=[['changed']]
  self.assertEqual(frame(before,after,'abcdefgh','study001',{'title':'edited'})['status'],'unintended_persistent_changes')
 def test_probe_checks_complete_state(self):
  before=observation();self.assertEqual(no_probe_effect(before,copy.deepcopy(before))['status'],'probe_persistent_state_unchanged')
  changed=copy.deepcopy(before);changed['files']['new']={}
  with self.assertRaisesRegex(ValueError,'prediction_probe_changed'):no_probe_effect(before,changed)
 def test_wrong_owner_rejected(self):
  before=observation()
  with self.assertRaisesRegex(ValueError,'original_owner'):frame(before,update(before),'abcdefgh','different',{})
