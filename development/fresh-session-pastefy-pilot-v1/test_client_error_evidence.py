import copy,unittest
from client_error_evidence import console_exceptions
class ConsoleEvidence(unittest.TestCase):
 def entry(self):return dict(text="TypeError: Cannot read properties of undefined (reading 'split')",location=dict(url='http://127.0.0.1:1337/assets/index.js'),stage='edit-button')
 def test_original_exception_after_edit_is_evidence(self):
  entry=self.entry();self.assertEqual(console_exceptions({'consoleErrors':[entry]}),[entry])
 def test_network_and_external_and_prior_errors_are_not_evidence(self):
  variants=[]
  for text in ['Failed to load resource: 401','net::ERR_BLOCKED_BY_CLIENT','TimeoutError: locator timeout']:
   e=self.entry();e['text']=text;variants.append(e)
  e=self.entry();e['location']['url']='https://external.invalid/assets/index.js';variants.append(e)
  e=self.entry();e['stage']='authenticate';variants.append(e)
  self.assertEqual(console_exceptions({'consoleErrors':variants}),[])
