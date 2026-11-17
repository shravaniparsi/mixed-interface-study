"""Synthetic readiness evidence tests; no application outcomes."""
import copy
import json
import unittest
from test_agentcompany_owncloud_controls_v1 import QualificationTests
from score_agentcompany_owncloud_controls_v2 import qualify


class ReadinessTests(unittest.TestCase):
    def setUp(self):
        fixture = QualificationTests(); fixture.setUp()
        self.runtime, self.results, self.registration = fixture.runtime, fixture.results, fixture.registration
        for branch in ('native_native', 'api_native'):
            r = self.results[branch]
            r['readiness'] = [dict(dir='/Documents', free_space='0', at=3, status=200)] * (2 if branch == 'native_native' else 1)
            r['passive_responses'] = [dict(path='/apps/files/ajax/getstoragestats.php?dir=%2FDocuments', status=200, observedAt=2, body=json.dumps(dict(data=dict(freeSpace=0))))]
            r['ui_events'] = [dict(action='dismiss_welcome', at=1), dict(action='list_page', names=['job_description.md'], at=5)]
            if branch == 'native_native': r['ui_events'].append(dict(action='select_upload', at=4, free_space='0'))

    def test_readiness_does_not_select_positive_space(self):
        # Scorer checks readiness, not favorable capacity. Synthetic v1 pass is intentional.
        self.assertTrue(qualify(self.runtime, self.results, self.registration)['qualified'])

    def test_rejects_missing_or_premature_evidence(self):
        for mutation in ('response', 'ready', 'welcome', 'row', 'timing'):
            with self.subTest(mutation=mutation):
                results = copy.deepcopy(self.results)
                r = results['native_native']
                if mutation == 'response': r['passive_responses'] = []
                if mutation == 'ready': r['readiness'][0]['free_space'] = ''
                if mutation == 'welcome': r['ui_events'] = [e for e in r['ui_events'] if e['action'] != 'dismiss_welcome']
                if mutation == 'row': r['ui_events'] = [e for e in r['ui_events'] if e['action'] != 'list_page']
                if mutation == 'timing': r['ui_events'][-1]['at'] = 0
                self.assertFalse(qualify(self.runtime, results, self.registration)['qualified'])


if __name__ == '__main__': unittest.main()
