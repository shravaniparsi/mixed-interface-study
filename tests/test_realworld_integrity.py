"""Synthetic adversarial tests of integrity evidence, not application results."""
import copy
import unittest
from test_realworld_oracle_components import reducer


def fixture():
    trace=[]
    def snap():
        values=[('/api/user', {'user':dict(username='pilotresearch',email='pilot@example.com',bio=None,image=None,token='ignored')}),
                ('/api/articles?author=pilotresearch', {'articles':[], 'articlesCount':0}),
                ('/api/tags', {'tags':[]})]
        reads=[]
        for path,data in values:
            trace.append(dict(sequence=len(trace)+1,type='response',source='state_probe',method='GET',path=path,status=200,data=data))
            reads.append(dict(path=path,status=200,data=data,response_sequence=len(trace)))
        return dict(readable=True,reads=reads,data=reducer.project_integrity_snapshot(reads))
    before=snap()
    command=dict(method='POST',path='/api/articles',payload={'article':{'body':''}})
    trace.append(dict(sequence=len(trace)+1,type='request',source='api',phase='prefix',**command))
    after=snap()
    return dict(prefix_interface='api',continuation_interface='ui',workflow='article-create-edit',trace=trace,
                observations=dict(prefix_status=422,continuation_outcome='not_executed_prefix_unsuccessful'),
                integrity=dict(version=1,helper_sha256=reducer.INTEGRITY_HELPER,before=before,
                               rejection=dict(status='unchanged',after=after),guards=[
                    dict(name='pre_state_readable',stage='setup',source='shared_api',expected=True,observed=True,passed=True),
                    dict(name='submitted_command',stage='prefix',source='api',expected=command,observed=copy.deepcopy(command),passed=True)]))


class IntegrityEvidenceTests(unittest.TestCase):
    def test_complete_rejection_evidence(self):
        self.assertEqual(reducer.execution_integrity_issues(fixture(),required=True),[])

    def test_legacy_optional_new_required(self):
        self.assertEqual(reducer.execution_integrity_issues({}),[])
        self.assertEqual(reducer.execution_integrity_issues({},required=True),['missing_execution_integrity'])

    def test_missing_required_guard(self):
        r=fixture(); r['integrity']['guards'].pop()
        self.assertTrue(any(x.startswith('missing_required_execution_guards') for x in reducer.execution_integrity_issues(r)))

    def test_forged_pass_cannot_hide_payload_difference(self):
        r=fixture();r['integrity']['guards'][1]['observed']['payload']={}
        issues=reducer.execution_integrity_issues(r)
        self.assertIn('execution_guard_verdict_mismatch:submitted_command',issues)
        self.assertIn('operation_not_comparable:submitted_command',issues)
        self.assertIn('submitted_command_not_backed_by_trace',issues)

    def test_same_count_tag_change_requires_changed_classification(self):
        r=fixture();after=r['integrity']['rejection']['after']
        after['reads'][2]['data']['tags'].append('orphan')
        after['data']=reducer.project_integrity_snapshot(after['reads'])
        self.assertIn('rejected_state_classification_mismatch',reducer.execution_integrity_issues(r))
        r['integrity']['rejection']['status']='changed'
        self.assertEqual(reducer.execution_integrity_issues(r),[])

    def test_trace_reference_must_match(self):
        r=fixture();r['integrity']['before']['reads'][0]['response_sequence']=999
        self.assertIn('snapshot_probe_not_backed_by_trace:before',reducer.execution_integrity_issues(r))

    def test_snapshot_projection_cannot_be_replaced(self):
        r=fixture();r['integrity']['before']['data']['user']['bio']='invented'
        self.assertIn('snapshot_projection_mismatch:before',reducer.execution_integrity_issues(r))

    def test_unreadable_after_cannot_be_unchanged(self):
        r=fixture();r['integrity']['rejection']['after']['readable']=False
        self.assertIn('rejected_state_classification_mismatch',reducer.execution_integrity_issues(r))
        r['integrity']['rejection']['status']='unreadable'
        self.assertEqual(reducer.execution_integrity_issues(r),[])

    def test_partial_and_duplicate_probes_fail(self):
        reads=fixture()['integrity']['before']['reads']
        for changed in (reads[:-1],reads+[reads[0]]):
            with self.assertRaises(ValueError):reducer.project_integrity_snapshot(changed)
        reads[1]['data']['articlesCount']=1
        with self.assertRaises(ValueError):reducer.project_integrity_snapshot(reads)

    def test_json_booleans_are_not_numeric_counts(self):
        self.assertFalse(reducer.strict_json_equal({'count':True},{'count':1}))
        self.assertFalse(reducer.strict_json_equal([1,2],[2,1]))
        self.assertTrue(reducer.strict_json_equal({'a':1,'b':2},{'b':2,'a':1}))
