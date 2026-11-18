import copy
import hashlib
import unittest
from verify_seatsurfing_request_budget_v1 import verify_request_budget


class RequestBudget(unittest.TestCase):
    def fixture(self,n=1):
        events=[]
        for index in range(n):
            events.extend([{'kind':'request','id':index,'url':'http://127.0.0.1:8080/user/me'},
                {'kind':'request_headers','id':index,'headers':{'authorization':'Bearer token'}},
                {'kind':'response','id':index,'status':200},{'kind':'finished','id':index}])
        return {'native_trace':{'events':events,'failure':None,'pendingIds':[],'pendingCaptures':0},
            'api_envelopes':[],'token_hash':hashlib.sha256(b'token').hexdigest(),
            'application_environment':{'RATE_LIMIT':'250','RATE_LIMIT_PERIOD':'1-M'}}
    def test_whole_lifetime_ceiling_never_uses_period_resets(self):
        result=verify_request_budget(**self.fixture(200))
        self.assertEqual(result['minimum_margin'],50);self.assertFalse(result['uses_sliding_window_estimate'])
        with self.assertRaisesRegex(ValueError,'ceiling'):verify_request_budget(**self.fixture(201))
    def test_native_and_api_count_together(self):
        x=self.fixture(200);x['api_envelopes']=[{'method':'GET','url':'http://127.0.0.1:8080/user/me','headers':{'authorization':'Bearer token'},'status':200,'dispatchedAt':1,'completedAt':2}]
        with self.assertRaisesRegex(ValueError,'ceiling'):verify_request_budget(**x)
    def test_create_envelope_shape_and_anonymous_requests_retained(self):
        x=self.fixture();x['native_trace']['events'][1]['headers']={}
        x['api_envelopes']=[{'request':{'url':'http://127.0.0.1:8080/location/','headers':{'authorization':'Bearer token'}},'response':{'status':201},'dispatchedAt':1,'completedAt':2}]
        result=verify_request_budget(**x);self.assertEqual(result['whole_process_authenticated_requests'],1);self.assertEqual(result['native']['total_requests'],1)
    def test_any_throttling_prevents_qualification(self):
        x=self.fixture();x['native_trace']['events'][2]['status']=429
        with self.assertRaisesRegex(ValueError,'throttling'):verify_request_budget(**x)
    def test_missing_headers_or_orphan_response_rejected(self):
        x=self.fixture();x['native_trace']['events'].pop(1)
        with self.assertRaisesRegex(ValueError,'Incomplete'):verify_request_budget(**x)
        x=self.fixture();x['native_trace']['events'].append({'kind':'response','id':999,'status':200})
        with self.assertRaisesRegex(ValueError,'Orphan'):verify_request_budget(**x)
    def test_changed_defaults_or_token_rejected(self):
        x=self.fixture();x['application_environment']['RATE_LIMIT']='9999'
        with self.assertRaisesRegex(ValueError,'defaults'):verify_request_budget(**x)
        x=self.fixture();x['token_hash']='wrong'
        with self.assertRaisesRegex(ValueError,'identity'):verify_request_budget(**x)


if __name__=='__main__':unittest.main()
