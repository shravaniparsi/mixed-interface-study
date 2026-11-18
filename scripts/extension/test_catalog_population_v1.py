import unittest
from collect_catalog_population_v1 import evaluate, select

class FrozenSelectionTests(unittest.TestCase):
    def entry(self):
        return dict(name='A distinct app',source_code_url='https://github.com/new-owner/new-app',platforms=['Docker'],licenses=['AGPL-3.0-only'])
    def test_overlap_owner_alias_and_dependency_types(self):
        d=self.entry()
        self.assertEqual(evaluate('software/a.yml',d,{'new-owner/old-app'})['failed_checks'],['prior_overlap'])
        d['depends_3rdparty']=0
        self.assertIn('third_party_dependency',evaluate('software/a.yml',d,set())['failed_checks'])
        d.pop('depends_3rdparty');d['name']='Old-App'
        self.assertIn('prior_overlap',evaluate('software/a.yml',d,{'someone/old-app'})['failed_checks'])
    def test_root_url_and_license_rules(self):
        d=self.entry();self.assertFalse(evaluate('software/a.yml',d,set())['failed_checks'])
        d['source_code_url']+='?tab=readme';d['licenses']=['BUSL-1.1']
        self.assertEqual(evaluate('software/a.yml',d,set())['failed_checks'],['github_root_url','license_screen'])
    def test_order_invariance_owner_ceiling_and_duplicates(self):
        rows=[dict(path=f'software/{i}.yml',repository=f'owner{i}/app',failed_checks=[]) for i in range(20)]
        rows += [dict(path='software/duplicate.yml',repository='owner0/app',failed_checks=[]),dict(path='software/sibling.yml',repository='owner0/sibling',failed_checks=[])]
        ranked,chosen=select(rows)
        self.assertEqual(select(list(reversed(rows))),(ranked,chosen))
        self.assertEqual(len(chosen),12)
        self.assertEqual(len({r.split('/')[0] for r in chosen}),12)
        self.assertEqual(len(ranked),21)

if __name__=='__main__':unittest.main()
