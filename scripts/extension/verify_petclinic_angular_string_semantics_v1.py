"""Check source/lock integrity and reconstruct templates; never executes Angular."""
import argparse
import base64
import hashlib
import json
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from mixed_interface.angular_string_lowering import lower

def main(forms_dir,package_dir):
    data=json.loads((ROOT/'manifests/petclinic-angular-string-semantics-v1.json').read_text())
    e=data['framework_evidence']
    for item in e['app_metadata']:
        assert hashlib.sha256((package_dir/item['path']).read_bytes()).hexdigest()==item['sha256']
    lock=json.loads((package_dir/'package-lock.json').read_text())['packages']['node_modules/@angular/forms']
    archive=(package_dir/'forms.tgz').read_bytes()
    assert lock['version']==e['version']=='22.2.3'
    assert lock['integrity']=='sha512-'+base64.b64encode(hashlib.sha512(archive).digest()).decode()
    assert hashlib.sha256(archive).hexdigest()==e['tar_sha256']
    assert hashlib.sha256((package_dir/'signals.mjs').read_bytes()).hexdigest()==e['signals_sha256']
    inv=json.loads((ROOT/'manifests/petclinic-source-rule-inventory-v1.json').read_text());results=[]
    for item in inv['inventories']:
        name=item['source_id'].split('/contents/')[1].split('?')[0].split('/')[-1]
        results.append(dict(schema=item['schema'],**lower((forms_dir/name).read_text(),item,'22.2.3')))
    assert results==data['results'];assert data['application_runs']==data['independent_cases']==0
    print('Verified package integrity and reconstructed 20 string templates; 9 unresolved calls, zero complete API rules.')

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--forms-dir',type=Path,required=True);p.add_argument('--package-dir',type=Path,required=True);a=p.parse_args();main(a.forms_dir,a.package_dir)
