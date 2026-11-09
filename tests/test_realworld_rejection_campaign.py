"""Synthetic rejected-response fixtures derived from exposed setup traces, not live results."""
from copy import deepcopy
from pathlib import Path
import sys
import unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import realworld_rejection_campaign as bridge
from realworld_terminal_campaign import pair_result as old_pair
from summarize_realworld_oracle_components import project_integrity_snapshot
from mixed_interface.terminal_outcomes import decision

ARCHIVE=ROOT/'results/realworld-paired-controls-ci-20261107'
REGISTRY=bridge.read(ROOT/'manifests/realworld-rejection-controls-v1.json')
SUMMARY=bridge.read(ARCHIVE/'summary.json')
FIXTURE=bridge.read(ARCHIVE/'fixture-references.json')
PLAN=bridge.plan_for(REGISTRY)


def synthetic_rejection(cid,consumer):
    spec=deepcopy(next(c for c in REGISTRY['cases'] if c['candidate_id']==cid))
    baseline=bridge.VARIATIONS[cid][0]
    run=deepcopy(next(b for b in SUMMARY['branches'] if b['candidate_id']==baseline and b['continuation']=='api'))
    raw=bridge.read(ARCHIVE/run['evidence'])
    request=next(e for e in raw['trace'] if e['phase']=='prefix' and e['type']=='request')
    response=raw['trace'][request['sequence']]
    envelope={'article-create-edit':'article','comment-create-delete':'comment','profile-update-edit':'user'}[spec['workflow']]
    request['payload']={envelope:deepcopy(spec['prefix_payload'])}
    response.update(status=422,data={'detail':'Synthetic rejection fixture'})
    raw['trace']=raw['trace'][:response['sequence']]
    guards=[g for g in raw['integrity']['guards'] if g['stage'] in ('setup','prefix')]
    for g in guards:
        if g['name']=='submitted_command':
            g['expected']=g['observed']={k:deepcopy(request[k]) for k in ('method','path','payload')}
    raw['integrity']['guards']=guards
    before=raw['integrity']['before']
    path='/api/user' if spec['workflow']=='profile-update-edit' else request['path'] if spec['workflow']=='comment-create-delete' else '/api/articles?author=pilotresearch'
    follow=deepcopy(next(r for r in before['reads'] if r['path']==path))
    def event(kind,source,path,**extra):
        raw['trace'].append(dict(sequence=len(raw['trace'])+1,phase='failed_prefix_followup',type=kind,source=source,method='GET',path=path,**extra))
        return len(raw['trace'])
    event('request','api',path);event('response','api',path,status=200,data=deepcopy(follow['data']))
    reads=[]
    for r in before['reads']:
        event('request','state_probe',r['path'])
        seq=event('response','state_probe',r['path'],status=200,data=deepcopy(r['data']))
        reads.append(dict(path=r['path'],status=200,data=deepcopy(r['data']),response_sequence=seq))
    raw['integrity']['rejection']={'status':'unchanged','after':{'readable':True,'reads':reads,'data':project_integrity_snapshot(reads)}}
    raw.update(candidate_id=cid,continuation_interface=consumer,expectation=deepcopy(spec['expectation']),
               checks=[{'name':'failed_prefix_observable_state_unchanged','passed':True}],
               observations={'prefix_status':422,'prefix_response':deepcopy(response['data']),'prefix_outcome':'rejected',
                 'api_continuation_started':False,'ui_continuation_started':False,
                 'continuation_outcome':'not_executed_prefix_unsuccessful',
                 'failed_prefix_api_followup':{'status':200,'data':deepcopy(follow['data'])}})
    raw.pop('prefix_state',None);raw.pop('final_state',None)
    run.update(case_id=cid+'-'+consumer+'-r1',candidate_id=cid,continuation=consumer,evidence=cid+'-'+consumer+'-r1.json',prefix_status=422,status='completed')
    return raw,run


class RejectionCampaignTests(unittest.TestCase):
    def setUp(self):
        self.job=deepcopy(PLAN['schedule']['initial_jobs'][3])
        self.spec=bridge.validate_job(self.job,REGISTRY)
        self.branches={c:synthetic_rejection(self.job['pair_id'],c) for c in ('api','ui')}

    def result(self,cleanup=True):
        return bridge.pair_result(self.job,self.branches,self.spec,FIXTURE,SUMMARY['fixture_sha256'],cleanup,{'synthetic':'a'*64})

    def test_all_three_rejection_pairs(self):
        for job in PLAN['schedule']['initial_jobs'][3:]:
            self.job=job;self.spec=bridge.validate_job(job,REGISTRY)
            self.branches={c:synthetic_rejection(job['pair_id'],c) for c in ('api','ui')}
            result=self.result()
            self.assertEqual(result['terminal']['kind'],'matched_rejection',result)
            self.assertFalse(decision(result['terminal'])['repeat'])
            for branch in result['branches'].values():
                self.assertFalse(branch['components']['assigned_continuation_reached'])

    def test_missing_post_rejection_snapshot_halts(self):
        del self.branches['api'][0]['integrity']['rejection']['after']
        self.assertEqual(self.result()['terminal']['kind'],'missing_evidence')

    def test_unreadable_snapshot_is_not_a_matched_rejection(self):
        raw=self.branches['api'][0];rejection=raw['integrity']['rejection'];after=rejection['after']
        after['readable']=False;after['data']=None;rejection['status']='unreadable'
        r=after['reads'][0];r.update(status=503,data={'error':'synthetic read failure'})
        raw['trace'][r['response_sequence']-1].update(status=r['status'],data=deepcopy(r['data']))
        old=old_pair(self.job,self.branches,self.spec,FIXTURE,SUMMARY['fixture_sha256'],True,{'synthetic':'a'*64})
        self.assertEqual(old['terminal']['kind'],'matched_rejection')
        self.assertEqual(self.result()['terminal']['kind'],'missing_evidence')

    def test_same_count_hidden_tag_change_remains_mismatch(self):
        raw=self.branches['api'][0];rejection=raw['integrity']['rejection'];after=rejection['after']
        r=next(r for r in after['reads'] if r['path']=='/api/tags');r['data']['tags'].append('synthetic-orphan')
        raw['trace'][r['response_sequence']-1]['data']=deepcopy(r['data'])
        after['data']=project_integrity_snapshot(after['reads']);rejection['status']='changed'
        result=self.result()['terminal']
        self.assertEqual(result['kind'],'completed_mismatch')
        self.assertFalse(result['outcome']['channel_discrepancy'])
        self.assertTrue(result['outcome']['check_failure'])

    def test_forged_unchanged_verdict_halts(self):
        self.branches['api'][0]['integrity']['rejection']['status']='changed'
        self.assertEqual(self.result()['terminal']['kind'],'missing_evidence')

    def test_trace_continuation_cannot_hide_behind_stop_flags(self):
        raw=self.branches['api'][0]
        raw['trace'].append(dict(sequence=len(raw['trace'])+1,phase='continuation',type='request',source='api',method='GET',path='/api/user'))
        self.assertEqual(self.result()['terminal']['kind'],'missing_evidence')

    def test_missing_explicit_stop_halts(self):
        del self.branches['api'][0]['observations']['continuation_outcome']
        self.assertEqual(self.result()['terminal']['kind'],'missing_evidence')

    def test_cleanup_precedes_rejection_evidence(self):
        self.assertEqual(self.result(False)['terminal']['kind'],'cleanup_unconfirmed')

    def test_server_error_is_not_matched_rejection(self):
        raw,run=self.branches['api'];raw['observations']['prefix_status']=500;run['prefix_status']=500
        next(e for e in raw['trace'] if e['type']=='response' and e['phase']=='prefix')['status']=500
        result=self.result()['terminal']
        self.assertEqual(result['kind'],'incomparable_observation')
        self.assertEqual(result['outcome']['observation_signature']['prefix_http_status']['api'],500)

    def test_unregistered_rejection_not_admitted(self):
        registry=deepcopy(REGISTRY);registry['cases'][-1]['prefix_payload']['username']='different'
        with self.assertRaises(ValueError):bridge.plan_for(registry)

    def test_matching_server_errors_are_mismatches_not_clean_rejections(self):
        for raw,run in self.branches.values():
            raw['observations']['prefix_status']=500;run['prefix_status']=500
            next(e for e in raw['trace'] if e['type']=='response' and e['phase']=='prefix')['status']=500
        self.assertEqual(self.result()['terminal']['kind'],'completed_mismatch')

    def test_baselines_and_rejections_complete_without_followups(self):
        from mixed_interface.campaign_v2 import drive
        def execute(job):
            spec=bridge.validate_job(job,REGISTRY)
            if job['pair_id'] in bridge.VARIATIONS:
                branches={c:synthetic_rejection(job['pair_id'],c) for c in ('api','ui')}
            else:
                branches={b['continuation']:(bridge.read(ARCHIVE/b['evidence']),deepcopy(b)) for b in SUMMARY['branches'] if b['candidate_id']==job['pair_id']}
            return bridge.pair_result(job,branches,spec,FIXTURE,SUMMARY['fixture_sha256'],True,{'synthetic':'a'*64})['terminal']
        state=drive(PLAN,execute,lambda _:None)
        self.assertEqual(state['status'],'completed_observations')
        self.assertEqual([o['kind'] for o in state['initial']],['clean_observation']*3+['matched_rejection']*3)
        self.assertFalse(state['repeated'])
