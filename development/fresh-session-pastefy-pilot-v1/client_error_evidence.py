"""Prospective v2 evidence rule for exceptions caught and logged by the original UI.
Network errors, runner exceptions and errors from another origin are not client failures.
"""
import re
from urllib.parse import urlparse
EXCEPTION=re.compile(r'^(?:Uncaught\s+)?(?:TypeError|ReferenceError|RangeError|SyntaxError):\s+\S')
def console_exceptions(record):
 matches=[]
 for entry in record.get('consoleErrors',[]):
  url=urlparse(entry.get('location',{}).get('url',''));stage=entry.get('stage','')
  if url.scheme!='http' or url.netloc!='127.0.0.1:1337' or not url.path.startswith('/assets/'):continue
  if stage!='edit-button' and not stage.startswith(('fill-','submit-','capture-')):continue
  if EXCEPTION.search(entry.get('text','')):matches.append(entry)
 return matches
