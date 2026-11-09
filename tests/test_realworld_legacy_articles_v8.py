"""Synthetic registered article scenarios derived from retained control traces.

String substitutions and command changes below construct test evidence only.
They do not relabel the original traces or establish observed application outcomes.
"""
from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
import realworld_legacy_jobs_v8 as jobs
from realworld_terminal_outcomes import classify_branch
from summarize_realworld_oracle_components import project_integrity_snapshot
ARCHIVE = ROOT / 'results/realworld-paired-controls-ci-20261107'
def read(name): return json.loads((ARCHIVE / name).read_bytes())


def replace_strings(value, mapping):
    if isinstance(value, str):
        if value in mapping: return mapping[value]
        # Article paths contain synthetic resource references as segments.
        if value.startswith('/api/articles/'):
            pieces = value.split('/')
            pieces[3] = mapping.get(pieces[3], pieces[3])
            return '/'.join(pieces)
        return value
    if isinstance(value, list): return [replace_strings(v, mapping) for v in value]
    if isinstance(value, dict): return {k: replace_strings(v, mapping) for k, v in value.items()}
    return value


def scenario(cid, channel):
    spec = next(c for c in jobs.selection()['cases'] if c['candidate_id'] == cid)
    original = 'article-valid' if cid.startswith('article-title') else 'article-update-unique-partial'
    run = next(b for b in read('summary.json')['branches'] if b['candidate_id'] == original and b['continuation'] == channel)
    raw = read(run['evidence']); fixture = read('fixture-references.json')
    if original == 'article-valid':
        old = next(c for c in read('registered-candidates.json')['cases'] if c['candidate_id'] == original)
        raw = replace_strings(raw, {old['prefix_payload']['title']: spec['prefix_payload']['title']})
    else:
        base, duplicate = fixture['base'], fixture['duplicate']
        mapping = {}
        for key in ('slug', 'title', 'description', 'body'):
            mapping[base[key]] = duplicate[key]; mapping[duplicate[key]] = base[key]
        raw = replace_strings(raw, mapping)
        transformed = replace_strings(fixture, mapping)
        fixture = {**transformed, 'duplicate': transformed['base'], 'base': transformed['duplicate']}
        # The full-update case sends the registered full command, not the partial command.
        for event in raw['trace']:
            if event.get('phase') == 'prefix' and event.get('type') == 'request':
                event['payload'] = {'article': deepcopy(spec['prefix_payload'])}
        for guard in raw['integrity']['guards']:
            if guard['name'] == 'submitted_command' and guard['stage'] == 'prefix':
                for side in ('expected', 'observed'):
                    guard[side]['payload'] = {'article': deepcopy(spec['prefix_payload'])}
        # Resource renaming changes canonical snapshot ordering.
        before = raw['integrity']['before']
        before['data'] = project_integrity_snapshot(before['reads'])
    raw.update(candidate_id=cid, expectation=deepcopy(spec['expectation']))
    run.update(candidate_id=cid, case_id=cid+'-'+channel+'-r1', evidence=cid+'-'+channel+'-r1.json')
    return raw, run, spec, fixture


def classify(value):
    raw, run, spec, fixture = value
    return classify_branch(raw, run, spec, fixture=fixture, cleanup_confirmed=True)


def failed_reference(cid='article-title-whitespace', empty=False):
    value = scenario(cid, 'api'); raw = value[0]
    prefix = next(e for e in raw['trace'] if e.get('phase') == 'prefix' and e.get('type') == 'response')
    raw['checks'] = [c for c in raw['checks'] if c['name'].startswith('prefix_')]
    raw['integrity']['guards'] = [g for g in raw['integrity']['guards'] if g['stage'] in ('setup', 'prefix')]
    raw.pop('final_state', None)
    obs = raw['observations']; obs.pop('continuation_write_status', None)
    if empty:
        prefix['data']['article']['slug'] = ''
        raw['prefix_state']['slug'] = ''
        obs['prefix_response'] = deepcopy(prefix['data'])
        raw['trace'] = raw['trace'][:prefix['sequence']]
        obs.update(api_continuation_started=False, continuation_outcome='empty_returned_reference')
        obs.pop('consumer_read_status', None)
    else:
        load = next(e for e in raw['trace'] if e.get('phase') == 'continuation' and e.get('type') == 'response' and e.get('method') == 'GET')
        load.update(status=404, data={'detail': 'synthetic missing reference'})
        raw['trace'] = raw['trace'][:load['sequence']]
        obs.update(consumer_read_status=404, continuation_outcome='returned_reference_not_resolvable')
    return value


class LegacyArticleTests(unittest.TestCase):
    def test_all_five_registered_cases_on_both_channels(self):
        for cid in jobs.IDS[2:7]:
            for channel in ('api', 'ui'):
                with self.subTest(cid=cid, channel=channel):
                    result = classify(scenario(cid, channel))
                    self.assertEqual(result['kind'], 'unresolved_policy' if cid.startswith('article-title') else 'clean_observation', result['issues'])

    def test_unknown_titles_do_not_acquire_an_acceptance_requirement(self):
        for cid in jobs.IDS[2:5]:
            result = classify(scenario(cid, 'api'))
            checks = result['components']['components']['immediate_response']['checks']
            self.assertNotIn('declared_acceptance_expectation', [c['id'] for c in checks])

    def test_partial_and_full_commands_remain_distinct(self):
        for cid in jobs.IDS[5:7]:
            value = scenario(cid, 'api')
            command = next(e for e in value[0]['trace'] if e.get('phase') == 'prefix' and e.get('type') == 'request')
            self.assertEqual(command['payload'], {'article': value[2]['prefix_payload']})
            command['payload']['article']['body'] = 'forged'
            self.assertEqual(classify(value)['kind'], 'missing_evidence')

    def test_wrong_duplicate_target_fails_closed(self):
        value = scenario('article-update-duplicate-full', 'api')
        for e in value[0]['trace']:
            if e.get('phase') == 'prefix' and e.get('type') == 'request':
                e['path'] = '/api/articles/wrong-target'
        self.assertEqual(classify(value)['kind'], 'missing_evidence')

    def test_fixture_generation_and_classification_preserve_archives(self):
        value = scenario('article-title-151', 'ui'); before = deepcopy(value)
        classify(value)
        self.assertEqual(value, before)

    def test_registered_pair_results_preserve_unknown_policies(self):
        registry = jobs.selection()
        for cid in jobs.IDS[2:7]:
            values = {channel: scenario(cid, channel) for channel in ('api', 'ui')}
            job = next(j for j in jobs.plan_for(registry)['jobs'] if j['candidate_id'] == cid)
            raw, run, spec, fixture = values['api']
            result = jobs.extract(job, {c: (v[0], v[1]) for c, v in values.items()},
                                  spec, fixture, run['reset_sha256'], True, {'synthetic': 'a' * 64})
            self.assertEqual(result['terminal']['kind'], 'unresolved_policy' if cid.startswith('article-title') else 'clean_observation')
            self.assertFalse(result['terminal']['outcome']['channel_discrepancy'])

    def test_empty_reference_is_a_shared_producer_observation(self):
        result = classify(failed_reference(empty=True))
        self.assertEqual(result['kind'], 'completed_mismatch', result['issues'])
        components = result['components']['components']
        self.assertIn('returned_reference_empty', components['immediate_response']['failed_check_ids'])
        self.assertFalse(components['assigned_api_continuation']['mismatch_observed'])
        self.assertFalse(result['components']['assigned_continuation_reached'])
        self.assertTrue(result['components']['policy_unresolved'])

    def test_404_is_observed_but_missing_response_is_incomplete(self):
        value = failed_reference()
        result = classify(value)
        self.assertEqual(result['kind'], 'completed_mismatch', result['issues'])
        self.assertIn('consumer_read_http_status', result['components']['components']['assigned_api_continuation']['failed_check_ids'])
        value[0]['trace'].pop()
        self.assertEqual(classify(value)['kind'], 'missing_evidence')

    def test_reported_404_without_matching_trace_is_incomplete(self):
        value = failed_reference(); value[0]['trace'][-1]['status'] = 200
        self.assertEqual(classify(value)['kind'], 'missing_evidence')

    def test_shared_empty_reference_never_becomes_channel_exclusive(self):
        cid = 'article-title-whitespace'; value = failed_reference(empty=True)
        raw, run, spec, fixture = value
        ui_raw, ui_run = deepcopy(raw), deepcopy(run)
        ui_raw['continuation_interface'] = 'ui'
        ui_run.update(continuation='ui', case_id=cid+'-ui-r1', evidence=cid+'-ui-r1.json')
        job = next(j for j in jobs.plan_for(jobs.selection())['jobs'] if j['candidate_id'] == cid)
        result = jobs.extract(job, {'api': (raw, run), 'ui': (ui_raw, ui_run)},
                              spec, fixture, run['reset_sha256'], True, {'synthetic': 'a' * 64})
        self.assertEqual(result['terminal']['kind'], 'incomparable_observation')
        self.assertIsNone(result['terminal']['outcome']['channel_discrepancy'])
        self.assertFalse(result['comparability']['same_consumer_command'])
        for branch in result['branches'].values():
            self.assertEqual(branch['kind'], 'completed_mismatch')
            self.assertFalse(branch['components']['assigned_continuation_reached'])
