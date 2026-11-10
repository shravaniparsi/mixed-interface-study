import copy,json,unittest
from pathlib import Path
from verify_memos_cases_v1 import rebuild,ROOT
REG={'version':'26.11.0','application_commit':'b40d8a7b573774c52b022c8d6537d6baf2129dc0'}
def fixture(workflow,channel):
    archive='memos-memo-controls-v1-ci-42898310104' if workflow=='memo' else 'memos-preference-controls-v5-ci-42899404684'
    p=next((ROOT/'results'/archive).rglob(channel+'/observation.json'));o=json.loads(p.read_text());o.update(status='observed',workflow=workflow,case_id=workflow+'-valid-1',prefix_status='accepted',producer_status=200)
    if workflow=='memo':
        producer=next(r for r in o['requests'] if r['method']=='POST');o['producer_body']=producer['body']
        for form in o['forms']:form['text_content']=form['content']
    else:
        producer=next(r for r in o['requests'] if r['method']=='PATCH');o['producer_body']=producer['body'];o['initialized']=o['prefix']
        # Finite valid case has initialization followed by an identical producer.
        index=o['requests'].index(producer)+2
        o['requests'][index:index]=copy.deepcopy(o['requests'][index-2:index])
    if channel=='api':o['continuation_status']=200
    else:o['native_requests']=[o['native_request']]
    return o,{'id':o['case_id'],'workflow':workflow,'cohort':'valid_control'}
class Reconstruction(unittest.TestCase):
    def test_qualified_raw_evidence_reconstructs_clean(self):
        for w in ['memo','preferences']:
            for c in ['api','ui']:
                with self.subTest(workflow=w,channel=c):
                    o,spec=fixture(w,c);r=rebuild(o,spec,REG);self.assertEqual(r['outcome'],'clean');self.assertFalse(r['representation_signal']);self.assertFalse(r['contract']);self.assertFalse(r['consistency'])
    def test_full_api_body_tamper_is_rejected(self):
        o,spec=fixture('memo','api');next(r for r in o['requests'] if r['method']=='PATCH')['body']['content']='Tampered'
        with self.assertRaisesRegex(ValueError,'Full API mutation'):rebuild(o,spec,REG)
if __name__=='__main__':unittest.main()
