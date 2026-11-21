import hashlib,json,pathlib,sys,tempfile,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'fresh-session-feasibility-v1'))
from export_evidence import export
from evidence_log import encode,decode
class TransportTest(unittest.TestCase):
 def test_sanitized_export_preserves_line_endings_and_hashes(self):
  with tempfile.TemporaryDirectory() as tmp:
   base=pathlib.Path(tmp);(base/'evidence').mkdir()
   secret='disposable-secret-value'
   (base/'redaction-values.json').write_text(json.dumps([secret]))
   (base/'evidence/runtime.log').write_bytes(('progress\rnext\r\n'+secret+'\n').encode())
   report=export(base);files=decode(encode(base/'public-evidence'))
   for row in report['files']:
    data=files[row['file']].encode();self.assertEqual(hashlib.sha256(data).hexdigest(),row['public_sha256'])
    self.assertEqual(data,(base/'public-evidence'/row['file']).read_bytes())
    self.assertNotIn(secret.encode(),data)
   self.assertIn('progress\rnext\r\n',files['evidence--runtime.log'])
 def test_modified_export_is_rejected(self):
  with tempfile.TemporaryDirectory() as tmp:
   base=pathlib.Path(tmp);(base/'evidence').mkdir();(base/'evidence/runtime.log').write_text('original')
   export(base);(base/'public-evidence/evidence--runtime.log').write_text('changed')
   with self.assertRaisesRegex(ValueError,'export_digest'):encode(base/'public-evidence')
