"""Replay retained qualified controls and adversarially corrupt evidence."""
import copy,json,sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parent))
from verify_gitea_cases_v1 import reconstruct
from gitea_outcomes_v1 import classify
ROOT=Path(__file__).resolve().parents[2]
class EvidenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.reg=json.loads((ROOT/'manifests/gitea-execution-v1.json').read_text());cls.examples=[]
        for p in (ROOT/'results/gitea-controls-v3-ci-42909599730').rglob('observation.json'):
            o=json.loads(p.read_text());s=next(s for s in cls.reg['workflows'] if s['id']==o['workflow']);c=next(c for c in cls.reg['cases'] if c['id']==o['workflow']+'-valid-1');o.update(status='observed',candidate=c,producer_status=201,continuation_status=200 if o['channel']=='api' else o['native_requests'][0]['status'],native_attempts=[dict(method=n['method'],path=n['path']) for n in o['native_requests']]);cls.examples.append((o,s,c))
    def test_all_eight_real_branches_reconstruct_clean(self):
        self.assertEqual(len(self.examples),8)
        for o,s,c in self.examples:
            got=reconstruct(o,s,c,self.reg);self.assertEqual(got,classify(o,s));self.assertEqual(got['outcome'],'clean');self.assertFalse(got['consistency']);self.assertFalse(got['representation_signal'])
    def test_api_body_omission_is_not_competent_full_body(self):
        o,s,c=copy.deepcopy(next(x for x in self.examples if x[0]['channel']=='api'))
        next(r for r in o['requests'] if r['method']=='PATCH')['body'].pop(s['fields'][0])
        with self.assertRaisesRegex(ValueError,'Full API'):reconstruct(o,s,c,self.reg)
    def test_native_payload_disagrees_with_actual_edit(self):
        o,s,c=copy.deepcopy(next(x for x in self.examples if x[0]['channel']=='ui'));o['native_requests'][0]['body']=o['native_requests'][0]['body'].replace('Edited','Corrupt')
        with self.assertRaisesRegex(ValueError,'Native decoding'):reconstruct(o,s,c,self.reg)
    def test_extra_field_loss_is_not_success(self):
        o,s,c=copy.deepcopy(next(x for x in self.examples if x[0]['workflow']=='label' and x[0]['channel']=='api'));o['final']['exclusive']=False;o['final_business']['exclusive']=False;[r for r in o['requests'] if r['method']=='GET' and r['path'].endswith('/labels/1')][-1]['response']['exclusive']=False
        self.assertEqual(reconstruct(o,s,c,self.reg)['outcome'],'preservation_or_edit_discrepancy')
if __name__=='__main__':unittest.main()
