import copy,json,pathlib,tempfile,unittest
import test_score_controls
from score_pilot import score,ROOT
class FullPilotGate(unittest.TestCase):
 def test_all_rejections_remain_in_denominator(self):
  with tempfile.TemporaryDirectory() as tmp:
   p=pathlib.Path(tmp);run=test_score_controls.WholeControlGate().fixture(p);cases=json.loads((ROOT/'manifests/fresh-session-pastefy-pilot-inputs-v1.json').read_text())['cases'];template=run['cases'][0]
   for case in cases[2:]:
    r=copy.deepcopy(template);r.update(id=case['id'],status='producer_not_accepted',branches=[],produced=r['producer_before']);r['producer'].update(request=case['input'],status=400,body={'success':False});r.pop('probe');r.pop('probe_before');r.pop('probe_after');run['cases'].append(r)
   (p/'pilot.json').write_text(json.dumps(run));result=score(p);self.assertEqual(len(result['cases']),6);self.assertEqual([r['H']['outcome'] for r in result['cases'][2:]],['producer_rejected']*4)
   run['cases'].pop();(p/'pilot.json').write_text(json.dumps(run))
   with self.assertRaisesRegex(ValueError,'complete_fixed_pilot_schedule'):score(p)
 def test_accepted_null_title_can_be_observed_without_inventing_normalization(self):
  from outcomes import producer
  from shlink_sqlite import typed
  with tempfile.TemporaryDirectory() as tmp:
   p=pathlib.Path(tmp);r=test_score_controls.WholeControlGate().fixture(p)['cases'][0];case=json.loads((ROOT/'manifests/fresh-session-pastefy-pilot-inputs-v1.json').read_text())['cases'][-1]
   before=json.loads((p/r['producer_before']).read_text());after=json.loads((p/r['produced']).read_text());table=after['database']['tables']['pastefy_pastes'];column=next(i for i,c in enumerate(table['columns']) if c[1]=='title');table['rows'][0][column]=typed(None);r['producer']['request']=case['input'];del r['producer_readback']['body']['title']
   result=producer(case,r,before,after);self.assertTrue(result['qualified']);self.assertFalse(result['target_normalized']);self.assertFalse(result['readback_field_presence']['title'])
