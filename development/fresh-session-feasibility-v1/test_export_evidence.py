import base64,json,pathlib,tempfile,unittest
from export_evidence import export
class PublicExport(unittest.TestCase):
 def test_nested_encoded_and_failed_bootstrap_credentials(self):
  with tempfile.TemporaryDirectory() as tmp:
   base=pathlib.Path(tmp);e=base/'evidence';e.mkdir();credential='synthetic-credential-for-export-test'
   (base/'deployment.json').write_text(json.dumps({'api_key':credential}))
   evidence={'plain':'INITIAL_API_KEY='+credential,'nested':json.dumps({'authorization':credential}),'binary':base64.b64encode(('prefix'+credential).encode()).decode(),'database':{'public.UserSession':{'rows':[{'id':'private-session-id','userId':'actor'}],'row_sha256':['raw-digest']}},'password':False,'api_key_sha256':'public-fingerprint','dump':'opaque-binary-dump'}
   (e/'result.json').write_text(json.dumps(evidence));(e/'runtime.tar.gz').write_bytes(b'private artifact');(e/'redaction-values.json').write_text(json.dumps([credential]))
   report=export(base);self.assertEqual(report['status'],'sanitized');public=(base/'public-evidence/evidence--result.json').read_text()
   self.assertNotIn(credential,public);self.assertNotIn(base64.b64encode(('prefix'+credential).encode()).decode(),public);self.assertNotIn('private-session-id',public);self.assertNotIn('opaque-binary-dump',public)
   parsed=json.loads(public);self.assertFalse(parsed['password']);self.assertEqual(parsed['api_key_sha256'],'public-fingerprint')
   self.assertFalse((base/'public-evidence/evidence--runtime.tar.gz').exists());self.assertFalse((base/'public-evidence/evidence--redaction-values.json').exists())
 def test_symlink_refused_and_failure_marked(self):
  with tempfile.TemporaryDirectory() as tmp:
   base=pathlib.Path(tmp);(base/'evidence').mkdir();(base/'source').write_text('{}');(base/'evidence/leak.json').symlink_to(base/'source')
   with self.assertRaises(ValueError):export(base)
   self.assertTrue((base/'public-evidence/EXPORT_FAILED').exists());self.assertFalse((base/'public-evidence/export.json').exists())
if __name__=='__main__':unittest.main()
