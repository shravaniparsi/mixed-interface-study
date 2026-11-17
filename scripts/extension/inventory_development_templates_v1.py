"""Inventory only the six previously exposed development templates."""
import hashlib,json,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
sys.path.insert(0,str(ROOT/'src'))
from mixed_interface.angular_template_inventory import inventory

def main():
    partition=json.loads((ROOT/'manifests/project-family-partition-v1.json').read_text())
    allowed={r['full_name'] for r in partition['rows'] if r['partition']=='development'}
    sources=json.loads((ROOT/'manifests/development-form-source-screen-v1.json').read_text());rows=[]
    for item in sources['rows']:
        if not item['path'].endswith('.html'):continue
        assert item['full_name'] in allowed and item['status']=='verified'
        raw=Path('/private/tmp/development-form-source-screen-v1/'+str(item['index'])+'.txt').read_bytes()
        assert hashlib.sha256(raw).hexdigest()==item['sha256']
        rows.append(dict(full_name=item['full_name'],path=item['path'],commit=item['commit'],source_index=item['index'],**inventory(raw.decode(),item['full_name']+'/'+item['path'])))
    assert len(rows)==6
    print(json.dumps(dict(kind='exposed_development_template_syntax_inventory',rows=rows,complete_api_rules=0,framework_runtime_executions=0,independent_evaluation_cases=0),indent=2))
if __name__=='__main__':main()
