"""Verify declared packaging transformation on frozen original Dockerfiles, without a build."""
import unittest
from shlink_build import recipe,BASE_IMAGES,ROOT,reviewed_reference
class BuildRecipe(unittest.TestCase):
 def test_original_backend_only_declared_changes(self):
  original=(ROOT/'results/evaluation-source-11-wave1/3.txt').read_text();changed=recipe(original,'shlink')
  self.assertIn('cp composer.json composer.lock /study-build-evidence/',changed)
  self.assertLess(changed.index('cp composer.json composer.lock'),changed.index('rm -r docker composer.*'))
  reconstructed=changed.replace('mkdir -p /study-build-evidence && cp composer.json composer.lock /study-build-evidence/ && ','')
  self.assertIn('--mount=type=secret,id=github_token,required=true',changed)
  reconstructed=reconstructed.replace('RUN --mount=type=secret,id=github_token,required=true ','RUN ').replace('GITHUB_TOKEN="$(cat /run/secrets/github_token)" ','')
  for tag,digest in BASE_IMAGES.items():reconstructed=reconstructed.replace(tag+'@'+digest,tag)
  self.assertEqual(reconstructed,original)
 def test_original_client_only_base_pinning(self):
  original=(ROOT/'results/evaluation-source-11-client-wave1/3.txt').read_text();changed=recipe(original,'shlink-client')
  for tag,digest in BASE_IMAGES.items():changed=changed.replace(tag+'@'+digest,tag)
  self.assertEqual(changed,original)
 def test_ambiguous_or_missing_capture_point_refused(self):
  original=(ROOT/'results/evaluation-source-11-wave1/3.txt').read_text()
  for candidate in [original.replace('    php composer.phar clear-cache && ','    true && '),original+original]:
   with self.assertRaises(ValueError):recipe(candidate,'shlink')
class ComposerIdentity(unittest.TestCase):
 def test_original_declared_abbreviation_and_full_identity(self):
  expected='7e5d108270e8218b139708e2a587605ba55b55c5'
  for observed in [expected,'7e5d108']:reviewed_reference(observed,expected,'dev-main#7e5d108 as 9.1.0')
 def test_mismatch_and_undeclared_or_short_abbreviation_refused(self):
  expected='7e5d108270e8218b139708e2a587605ba55b55c5'
  for observed,constraint in [('7e5d108','^9.1'),('7e5d108','dev-main#1234567'),('7e5','dev-main#7e5'),('7e5d1082','dev-main#7e5d108'),('0'*40,'dev-main#7e5d108')]:
   with self.subTest(observed=observed,constraint=constraint),self.assertRaises(ValueError):reviewed_reference(observed,expected,constraint)
if __name__=='__main__':unittest.main()
