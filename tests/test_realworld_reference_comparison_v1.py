"""Adversarial checks of local reference proof and immutable archive replay."""
from copy import deepcopy
from pathlib import Path
import sys, unittest
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/'scripts'))
from realworld_reference_comparison_v1 import binding, compare
from replay_realworld_references_v1 import inputs, replay, OUTPUT
from realworld_terminal_campaign import read
ARCHIVE=ROOT/'results/realworld-fresh-legacy-ci-20261109/realworld-legacy-v9'


class ReferenceComparisonTests(unittest.TestCase):
    def setUp(self):
        self.args=inputs(ARCHIVE/'legacy-006')

    def test_live_full_update_qualifies_without_mutating_inputs(self):
        before=deepcopy(self.args); value=compare(*self.args)
        self.assertEqual(value['original_kind'],'incomparable_observation')
        self.assertEqual(value['derived_kind'],'clean_observation')
        self.assertTrue(value['reference_comparison_qualified'])
        self.assertEqual(self.args,before)

    def test_missing_empty_wrong_or_unresolved_reference_never_binds(self):
        for channel in ('api','ui'):
            original=self.args[1][channel][0]
            for variant in ('empty','wrong_path','missing_write','load_404','wrong_content','wrong_payload','wrong_source','duplicate_response','reordered'):
                with self.subTest(channel=channel,variant=variant):
                    raw=deepcopy(original);slug=raw['prefix_state']['slug'];path='/api/articles/'+slug
                    load=next(e for e in raw['trace'] if e['type']=='response' and e['source']==channel and e['method']=='GET' and e['path']==path)
                    write=next(e for e in raw['trace'] if e['type']=='request' and e['source']==channel and e['method']=='POST' and e['path']==path+'/comments')
                    if variant=='empty':raw['prefix_state']['slug']=''
                    elif variant=='wrong_path':write['path']='/api/articles/other/comments'
                    elif variant=='missing_write':raw['trace'].remove(write)
                    elif variant=='load_404':load['status']=404
                    elif variant=='wrong_content':load['data']['article']['body']='other resource'
                    elif variant=='wrong_payload':write['payload']['comment']['body']='other payload'
                    elif variant=='wrong_source':write['source']='state_probe'
                    elif variant=='duplicate_response':raw['trace'].append(deepcopy(load))
                    elif variant=='reordered':write['sequence']=load['sequence']-1
                    self.assertFalse(binding(raw,channel))

    def test_browser_response_requires_matching_capture_id(self):
        raw=deepcopy(self.args[1]['ui'][0])
        for e in raw['trace']:
            if e['type']=='response' and e['source']=='ui':e['capture_request_id']='foreign'
        self.assertFalse(binding(raw,'ui'))

    def test_unrelated_cross_branch_gate_is_not_overridden(self):
        args=deepcopy(self.args);args[1]['ui'][1]['reset_sha256']='different'
        value=compare(*args)
        self.assertFalse(value['reference_comparison_qualified'])
        self.assertNotEqual(value['derived_kind'],'clean_observation')

    def test_content_difference_is_not_removed_with_slug(self):
        args=deepcopy(self.args);raw=args[1]['ui'][0]
        raw['prefix_state']['body']='different article content'
        for event in raw['trace']:
            article=event.get('data',{}).get('article') if isinstance(event.get('data'),dict) else None
            if article and article.get('slug')==raw['prefix_state']['slug']:
                article['body']='different article content'
        self.assertTrue(binding(raw,'ui'))
        value=compare(*args)
        self.assertFalse(value['reference_comparison_qualified'])
        self.assertNotEqual(value['derived_kind'],'clean_observation')

    def test_absent_actions_remain_incomparable(self):
        for job in ('legacy-004','legacy-005'):
            value=compare(*inputs(ARCHIVE/job))
            self.assertEqual(value['derived_kind'],'incomparable_observation')
            self.assertFalse(value['reference_comparison_qualified'])

    def test_replay_matches_manifest_and_preserves_singletons(self):
        value=replay();self.assertEqual(value,read(OUTPUT))
        self.assertEqual(value['new_primary_samples'],0)
        self.assertEqual(sum(v.get('derived_kind')=='incomparable_observation' for v in value['jobs'].values()),2)
        for job in ('legacy-007','legacy-008'):
            self.assertFalse(value['jobs'][job]['paired_comparison_eligible'])
