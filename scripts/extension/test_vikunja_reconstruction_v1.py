import copy,json,unittest
from pathlib import Path
from verify_vikunja_cases_v1 import rebuild,Inputs
ROOT=Path(__file__).resolve().parents[2]
class Reconstruction(unittest.TestCase):
 def inputs(self):
  reg=json.loads((ROOT/'manifests/vikunja-probes-v1.json').read_text())
  for p in (ROOT/'results/vikunja-probes-v1-ci-42905951983').rglob('observation.json'):
   o=json.loads(p.read_text())
   if o['workflow']=='task':continue
   spec=next(s for s in reg['workflows'] if s['id']==o['workflow']);case=dict(id=o['workflow']+'-valid-1',workflow=o['workflow'],cohort='valid_control')
   creates=[r for r in o['requests'] if r['method']=='POST' and r['path']==spec['collection']]
   o.update(status='observed',case_id=case['id'],producer_status=creates[0]['status'],producer_body=creates[0]['body'],continuation_status=200)
   for form in o['forms']:
    parser=Inputs();parser.feed(form['color_html']);form['color_empty']='is-empty' in parser.inputs[0].get('class','').split()
   yield o,case,reg
 def test_four_real_qualified_branches(self):
  items=list(self.inputs());self.assertEqual(len(items),4)
  for o,c,r in items:
   value=rebuild(o,c,r);self.assertEqual(value['outcome'],'clean');self.assertFalse(value['representation_signal']);self.assertEqual(value['contract'],[]);self.assertEqual(value['consistency'],[])
 def test_tampered_semantic_payload_rejected(self):
  o,c,r=next((o,c,r) for o,c,r in self.inputs() if o['channel']=='api')
  write=next(x for x in o['requests'] if x['method']=='PUT');write['body'].pop('hex_color')
  with self.assertRaisesRegex(ValueError,'Full API semantic body'):rebuild(o,c,r)
if __name__=='__main__':unittest.main()
