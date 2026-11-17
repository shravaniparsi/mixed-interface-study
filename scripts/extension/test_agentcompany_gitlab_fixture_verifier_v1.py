"""Synthetic adverse cases for read-only fixture reconstruction."""
import copy
import unittest
from urllib.parse import urlencode
from verify_agentcompany_gitlab_fixture_v1 import reconstruct_fixture


class FixtureTests(unittest.TestCase):
    def setUp(self):
        self.requests = [dict(method='GET', status=200, path=p, next_page='') for p in ['/api/v4/user', '/api/v4/projects/root%2Frisingwave']]
        self.payloads = [dict(username='root', is_admin=True), dict(id=7, path_with_namespace='root/risingwave')]
        for resource, title in [('milestones','Alpha Release'), ('milestones','Beta Release'), ('issues','Implement stream processing engine'), ('issues','Integrate with Kafka')]:
            self.requests.append(dict(method='GET', status=200, next_page='', path='/api/v4/projects/7/' + resource + '?' + urlencode(dict(per_page=100, search=title))))
            self.payloads.append([])

    def test_missing_prepopulation_is_preserved(self):
        self.assertEqual(reconstruct_fixture(self.requests, self.payloads), dict(alpha=[], beta=[], issue_engine=[], issue_kafka=[]))

    def test_duplicates_are_not_silently_resolved(self):
        self.payloads[2] = [dict(id=i, title='Alpha Release') for i in (3, 4)]
        self.assertEqual([r['id'] for r in reconstruct_fixture(self.requests, self.payloads)['alpha']], [3, 4])

    def test_rejects_incomplete_or_different_comparison(self):
        for change in ('pagination', 'project', 'title', 'write', 'nonadmin'):
            with self.subTest(change=change):
                requests, payloads = copy.deepcopy(self.requests), copy.deepcopy(self.payloads)
                if change == 'pagination': requests[2]['next_page'] = '2'
                if change == 'project': payloads[1]['path_with_namespace'] = 'root/other'
                if change == 'title': requests[2]['path'] = requests[2]['path'].replace('Alpha', 'Other')
                if change == 'write': requests[2]['method'] = 'POST'
                if change == 'nonadmin': payloads[0]['is_admin'] = False
                with self.assertRaises(AssertionError): reconstruct_fixture(requests, payloads)


if __name__ == '__main__': unittest.main()
