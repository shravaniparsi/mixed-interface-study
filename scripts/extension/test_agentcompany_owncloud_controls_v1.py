"""Adverse synthetic scorer checks; these are not application outcomes."""
import copy
import unittest
from score_agentcompany_owncloud_controls_v1 import qualify, BRANCHES


class QualificationTests(unittest.TestCase):
    def setUp(self):
        self.registration = dict(payload_sha256='abc', payload_bytes=7, destination='/Documents/job_description.md')
        self.runtime = dict(status='completed', branches=[])
        self.results = {}
        for index, branch in enumerate(BRANCHES):
            self.runtime['branches'].append(dict(branch=branch, containers=dict(owncloud=f'o{index}', collabora=f'c{index}'), ready=True, node_returncode=0, cleanup=dict(owncloud=0, collabora=0, network=0)))
            state = dict(path=self.registration['destination'], sha256='abc', length=7, content_type='text/markdown')
            methods = [] if index == 0 else ['PUT'] if index == 1 else ['PUT', 'POST']
            self.results[branch] = dict(branch=branch, passed=True, stage='completed', producer=state, final_file=copy.deepcopy(state), public_download_sha256='abc', share=dict(path=state['path'], share_type=3, permissions=1, uid_owner='theagentcompany', share_with=None, expiration=None), api_requests=[dict(method=m) for m in methods], native_requests=[dict(method='POST', path='/ocs/v1.php/apps/files_sharing/api/v1/shares', status=200), dict(method='PUT', path='/remote.php/webdav/Documents/job_description.md', status=201)])

    def test_ordinary_triple(self):
        self.assertTrue(qualify(self.runtime, self.results, self.registration)['qualified'])

    def test_adverse_evidence(self):
        def mutate(kind, runtime, results):
            r = results['native_native']
            if kind == 'producer': r['producer']['sha256'] = 'wrong'
            if kind == 'download': r['public_download_sha256'] = 'wrong'
            if kind == 'fallback': r['api_requests'].append(dict(method='PUT'))
            if kind == 'trace': r['native_requests'] = []
            if kind == 'reused': runtime['branches'][1]['containers'] = runtime['branches'][0]['containers']
            if kind == 'missing': del results['api_api']
            if kind == 'cleanup': runtime['branches'][0]['cleanup']['owncloud'] = 1
            if kind == 'permission': r['share']['permissions'] = 3
            if kind == 'mime': results['api_api']['producer']['content_type'] = 'text/plain'
        for kind in ('producer', 'download', 'fallback', 'trace', 'reused', 'missing', 'cleanup', 'permission', 'mime'):
            with self.subTest(kind=kind):
                runtime, results = copy.deepcopy(self.runtime), copy.deepcopy(self.results)
                mutate(kind, runtime, results)
                outcome = qualify(runtime, results, self.registration)
                self.assertFalse(outcome['qualified'])
                self.assertEqual(outcome['confirmed_defects'], 0)


if __name__ == '__main__':
    unittest.main()
