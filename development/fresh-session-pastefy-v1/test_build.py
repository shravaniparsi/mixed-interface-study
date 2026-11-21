import json,pathlib,unittest
from build import recipe,PINS,ROOT
class Build(unittest.TestCase):
 def test_only_declared_packaging_changes(self):
  # Original Dockerfile retained as pinned source from the source preflight.
  original=(pathlib.Path(__file__).parent/'fixtures/original.Dockerfile').read_text()
  changed=recipe(original)
  self.assertLess(changed.index('cp /app/package-lock.json'),changed.index('COPY frontend app'))
  for row in json.loads(PINS.read_text()):changed=changed.replace(row['tag']+'@'+row['linux_amd64_digest'],row['tag'])
  changed=changed.replace(' && mkdir /study-dependencies && cp /app/package-lock.json /study-dependencies/resolved-package-lock.json','')
  self.assertEqual(changed,original)
if __name__=='__main__':unittest.main()
