import json,pathlib,tempfile,unittest
from evidence_log import encode,decode,PREFIX
from export_evidence import export
class EvidenceLog(unittest.TestCase):
 def test_roundtrip_and_incomplete_or_corrupt_refusal(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=pathlib.Path(tmp);(root/'evidence').mkdir();(root/'evidence/result.json').write_text('{"status":"fixture"}')
   export(root);lines=encode(root/'public-evidence');files=decode('\n'.join('timestamp '+line for line in lines.splitlines()))
   self.assertEqual(json.loads(files['evidence--result.json']),{'status':'fixture'})
   for broken in [lines.split(PREFIX+'END')[0],lines.replace(PREFIX+'0 ',PREFIX+'1 ',1),lines+lines,lines.replace('END 1 ','END 2 ')]:
    with self.assertRaises((ValueError,AssertionError)):decode(broken)
 def test_changed_export_refused(self):
  with tempfile.TemporaryDirectory() as tmp:
   root=pathlib.Path(tmp);(root/'evidence').mkdir();(root/'evidence/result.json').write_text('{}');export(root)
   (root/'public-evidence/evidence--result.json').write_text('{"changed":true}')
   with self.assertRaises(ValueError):encode(root/'public-evidence')
if __name__=='__main__':unittest.main()
