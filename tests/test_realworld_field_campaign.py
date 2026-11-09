"""Exact job binding and synthetic rejection fixtures for the exposed field cohort."""
from copy import deepcopy
from pathlib import Path
import sys,unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
import realworld_field_campaign as p
import test_realworld_rejection_campaign as fixtures

class FieldCampaignTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.registry=p.read(ROOT/'manifests/realworld-field-controls-v1.json');cls.plan=p.plan_for(cls.registry)
    def test_all_nine_cases_are_exact_existing_specs(self):
        original=p.read(ROOT/'manifests/realworld-boundary-registry-v1.json');by={c['candidate_id']:c for c in original['cases']}
        self.assertEqual(len(self.registry['cases']),9)
        for c in self.registry['cases']:self.assertEqual(c,by[c['candidate_id']])
    def test_same_workflow_positive_references_and_alternating_order(self):
        pairs={c['pair_id']:c for c in self.plan['schedule']['pairs']}
        for i,pair in enumerate(pairs.values()):
            ref=pairs[pair['reference_control']];self.assertEqual(ref['intervention'],'route_only');self.assertEqual(ref['workflow_id'],pair['workflow_id'])
            self.assertEqual(pair['consumer_order'],['api','ui'] if i%2==0 else ['ui','api'])
    def test_payload_change_is_rejected_even_with_same_identifier(self):
        changed=deepcopy(self.registry);changed['cases'][2]['prefix_payload']['body']='changed'
        with self.assertRaises(ValueError):p.plan_for(changed)
    def test_changed_job_order_and_foreign_case_rejected(self):
        j=deepcopy(self.plan['schedule']['initial_jobs'][0]);j['branches'].reverse()
        with self.assertRaises(ValueError):p.validate_job(j,self.registry)
        j=deepcopy(self.plan['schedule']['initial_jobs'][0]);j['pair_id']='profile-username-null'
        with self.assertRaises(ValueError):p.validate_job(j,self.registry)
    def branches(self,spec):
        cid=spec['candidate_id'];original='article-body-omitted' if cid.startswith('article-') else 'comment-body-omitted';envelope='article' if cid.startswith('article-') else 'comment';branches={}
        for channel in ('api','ui'):
            raw,run=fixtures.synthetic_rejection(original,channel)
            raw.update(candidate_id=cid,expectation=deepcopy(spec['expectation']))
            request=next(e for e in raw['trace'] if e['phase']=='prefix' and e['type']=='request');request['payload']={envelope:deepcopy(spec['prefix_payload'])}
            for g in raw['integrity']['guards']:
                if g['name']=='submitted_command' and g['stage']=='prefix':g['expected']=g['observed']={k:deepcopy(request[k]) for k in ('method','path','payload')}
            run.update(case_id=cid+'-'+channel+'-r1',candidate_id=cid,evidence=cid+'-'+channel+'-r1.json')
            branches[channel]=(raw,run)
        return branches
    def result(self,job,branches):
        spec=p.validate_job(job,self.registry)
        return p.pair_result(job,branches,spec,fixtures.FIXTURE,fixtures.SUMMARY['fixture_sha256'],True,{'synthetic':'a'*64})
    def test_four_new_rejection_variants_are_trace_bound(self):
        for job in self.plan['schedule']['initial_jobs'][5:]:
            spec=p.validate_job(job,self.registry);result=self.result(job,self.branches(spec))
            self.assertEqual(result['terminal']['kind'],'matched_rejection',result)
    def test_unreadable_rejection_state_does_not_gain_qualification(self):
        job=self.plan['schedule']['initial_jobs'][5];branches=self.branches(p.validate_job(job,self.registry));branches['ui'][0]['integrity']['rejection']['after']['readable']=False
        self.assertEqual(self.result(job,branches)['terminal']['kind'],'missing_evidence')
    def test_continuation_after_rejection_is_incomplete(self):
        job=self.plan['schedule']['initial_jobs'][6];branches=self.branches(p.validate_job(job,self.registry));branches['api'][0]['observations']['continuation_outcome']='passed'
        self.assertEqual(self.result(job,branches)['terminal']['kind'],'missing_evidence')
    def test_expected_selection_does_not_claim_identity_or_unknown_policy_cases(self):
        for c in self.registry['cases']:
            self.assertIn(c['workflow'],('article-create-edit','comment-create-delete'));self.assertIn(c['expectation']['outcome'],('accept','reject'))

    def test_postrun_selection_loads_the_archived_field_registry(self):
        import tempfile
        from validate_realworld_field_campaign import read_selection
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'sources/manifests').mkdir(parents=True)
            p.write(root/'sources/manifests/realworld-field-controls-v1.json',self.registry)
            self.assertEqual(read_selection(root),self.registry)

    def test_old_registry_filename_cannot_substitute_for_field_selection(self):
        import tempfile
        from validate_realworld_field_campaign import read_selection
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'sources/manifests').mkdir(parents=True)
            p.write(root/'sources/manifests/realworld-rejection-controls-v1.json',self.registry)
            with self.assertRaises(FileNotFoundError):read_selection(root)
