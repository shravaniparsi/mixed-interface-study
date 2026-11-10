import copy,json,unittest
from html.parser import HTMLParser
class Inputs(HTMLParser):
 def handle_starttag(self,tag,attrs):
  if tag=='input':self.attributes=dict(attrs)
from pathlib import Path
from vikunja_outcomes_v1 import classify,ordinary_gate
ROOT=Path(__file__).resolve().parents[2]
class Outcomes(unittest.TestCase):
 def observations(self):
  for folder,registry in [('vikunja-controls-v3-ci-42904655242','vikunja-controls-v3.json'),('vikunja-task-controls-v3-ci-42905348274','vikunja-task-controls-v3.json')]:
   reg=json.loads((ROOT/'manifests'/registry).read_text());specs={w['id']:w for w in reg['workflows']}
   for p in (ROOT/'results'/folder).rglob('observation.json'):
    o=json.loads(p.read_text());o.update(status='observed',producer_status=201,continuation_status=200)
    for form in o['forms']:
     if 'color_html' in form:
      parser=Inputs();parser.feed(form['color_html']);form['color_empty']='is-empty' in parser.attributes.get('class','').split()
    yield o,specs[o['workflow']]
 def test_twelve_real_ordinary_branches(self):
  items=list(self.observations());self.assertEqual(len(items),12)
  for o,s in items:self.assertTrue(ordinary_gate(o,s),(o['workflow'],o['channel']))
 def test_additional_field_loss_is_detected(self):
  for o,s in self.observations():
   o['final']['hex_color']='000000';self.assertEqual(classify(o,s)['outcome'],'preservation_or_edit_discrepancy')
 def test_documented_trim_is_separate_and_not_blanket_permission(self):
  o,s=next((o,s) for o,s in self.observations() if o['workflow']=='task' and o['channel']=='ui')
  o['prefix']['title']='Ordinary task ';self.assertEqual(classify(o,s)['outcome'],'documented_normalization')
  o['final']['priority']=5;self.assertEqual(classify(o,s)['outcome'],'preservation_or_edit_discrepancy')
 def test_failure_is_not_a_clean_control(self):
  o,s=next(self.observations());o['status']='incomplete';self.assertFalse(ordinary_gate(o,s));self.assertEqual(classify(o,s)['outcome'],'unresolved')
if __name__=='__main__':unittest.main()
