"""Verify declared packaging transformation on frozen original Dockerfiles, without a build."""
import unittest
from shlink_build import recipe,BASE_IMAGES,ROOT
class BuildRecipe(unittest.TestCase):
 def test_original_backend_only_declared_changes(self):
  original=(ROOT/'results/evaluation-source-11-wave1/3.txt').read_text();changed=recipe(original,'shlink')
  self.assertIn('cp composer.json composer.lock /study-build-evidence/',changed)
  self.assertLess(changed.index('cp composer.json composer.lock'),changed.index('rm -r docker composer.*'))
  reconstructed=changed.replace('mkdir -p /study-build-evidence && cp composer.json composer.lock /study-build-evidence/ && ','')
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
if __name__=='__main__':unittest.main()
