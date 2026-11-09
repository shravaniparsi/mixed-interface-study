"""Offline intent tests; synthetic traces never qualify runtime execution."""
from copy import deepcopy
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from realworld_generated_bindings_v1 import plan,case_for,resolve,extract
from prepare_realworld_generated_bindings_v1 import build
from test_realworld_oracle_components import positive


class GeneratedBindingsTests(unittest.TestCase):
    def test_exact_retained_pairs_and_same_producer_controls(self):
        value=build()['plan'];self.assertEqual((value['pairs'],value['branches']),(9,18))
        jobs={j['pair']['pair_id']:j for j in value['jobs']}
        for job in jobs.values():
            reference=jobs[job['reference_pair_id']]
            self.assertEqual(reference['pair']['intervention'],'route_only')
            self.assertEqual(reference['pair']['producer_interface'],job['pair']['producer_interface'])
            self.assertEqual({b['channel'] for b in job['branches']},{'api','ui'})
        self.assertFalse(value['execution_authorized'])

    def test_all_eighteen_intents_preserve_input_and_resolve_returned_fields(self):
        for job in plan()['jobs']:
            for channel in ('api','ui'):
                with self.subTest(job=job['job_id'],channel=channel):
                    spec=case_for(job,channel)
                    returned={'slug':'returned reference','title':'Returned title','description':'Returned description',
                              'body':'Returned body','tagList':['z','z','a'],'author':{'username':'pilotresearch'}}
                    before=deepcopy(returned);value=resolve(job,channel,201,returned)
                    self.assertEqual(value['producer_payload'],spec['operations'][0]['input'])
                    self.assertEqual(value['requirement_policy'],spec['expectation'])
                    self.assertEqual(value['consumer_command']['path'],'/api/articles/returned%20reference')
                    payload=value['consumer_command']['payload']['article']
                    self.assertEqual(payload['title'],returned['title'])
                    self.assertEqual(payload['tagList'],returned['tagList'])
                    self.assertEqual(payload['body'],spec['operations'][1]['input']['article']['body'])
                    self.assertEqual(returned,before)

    def test_omitted_null_empty_and_whitespace_are_distinct(self):
        bodies=[]
        for job in plan()['jobs']:
            payload=resolve(job,'api',422)['producer_payload']['article']
            bodies.append(('body' in payload,payload.get('body')))
        for value in [(False,None),(True,None),(True,''),(True,'   ')]:self.assertIn(value,bodies)

    def test_rejections_and_empty_references_cannot_resolve_continuation(self):
        job=plan()['jobs'][0]
        for status in (200,400,422,500):
            self.assertIsNone(resolve(job,'ui',status)['consumer_command'])
        for slug in ('',' ',None):
            self.assertIsNone(resolve(job,'ui',201,{'slug':slug})['consumer_command'])
        with self.assertRaises(ValueError):resolve(job,'ui',201,{'slug':'valid'})

    def test_changed_job_payload_hash_and_channel_rejected(self):
        for field in ('reference_pair_id','repetition'):
            job=deepcopy(plan()['jobs'][0]);job[field]='changed'
            with self.assertRaises(ValueError):case_for(job,'api')
        job=deepcopy(plan()['jobs'][0]);job['branches'][0]['source_case_sha256']='0'*64
        with self.assertRaises(ValueError):case_for(job,'api')
        with self.assertRaises(ValueError):case_for(plan()['jobs'][0],'other')

    def test_pure_extractor_binds_case_route_and_requires_integrity(self):
        for channel in ('api','ui'):
            raw,run,spec,_=positive(consumer=channel,generated=True)
            job=next(j for j in plan()['jobs'] if spec['case_id'] in j['pair']['case_ids'].values())
            value=extract(job,channel,raw,run)
            self.assertFalse(value['components']['execution_evidence_complete'])
            self.assertTrue(any('integrity' in i or 'capture' in i for i in value['components']['evidence_issues']))
            raw['case_id']='foreign'
            with self.assertRaises(ValueError):extract(job,channel,raw,run)
            raw['case_id']=spec['case_id'];raw['route']=['ui',channel]
            with self.assertRaises(ValueError):extract(job,channel,raw,run)
