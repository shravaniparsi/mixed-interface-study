"""Audit fixed package metadata reads and keep ranges distinct from versions."""
import argparse,hashlib,json,re
from collections import Counter
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def main(private):
    schedule=json.loads((ROOT/'manifests/project-package-read-schedule-v1.json').read_text())
    result=json.loads((ROOT/'manifests/project-package-screen-v1.json').read_text())
    assert result['freeze']=='28db71d' and len(schedule['files'])==len(result['rows'])==41
    for index,(expected,row) in enumerate(zip(schedule['files'],result['rows']),1):
        assert all(row[k]==v for k,v in expected.items()) and row['index']==index
        if row['status']=='parsed':
            assert row['observed_blob_sha']==row['blob_sha'] and row['bytes']<=256*1024
        if private and 'sha256' in row:
            raw=(private/(str(index)+'.json')).read_bytes();assert hashlib.sha256(raw).hexdigest()==row['sha256']
            assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==row['blob_sha']
            if row['status']=='parsed':
                parsed=json.loads(raw)
                for group,values in row['framework_declarations'].items():
                    assert all(parsed[group][k]==v for k,v in values.items())
    declarations=[(r['full_name'],v) for r in result['rows'] for v in r.get('angular_core_declarations',[])]
    major_hints=Counter()
    for _,value in declarations:
        match=re.match(r'^[~^]?(\d+)\.',str(value))
        major_hints[match[1] if match else 'unparsed']+=1
    summary=dict(planned_files=41,statuses=dict(Counter(r['status'] for r in result['rows'])),projects_with_package_paths=len({r['full_name'] for r in result['rows']}),projects_with_angular_core_declaration=len({p for p,v in declarations}),angular_core_declaration_entries=len(declarations),declared_major_hints=dict(major_hints),exact_22_2_3_declarations=sum(v=='22.2.3' for _,v in declarations),projects_with_22x_lower_or_exact_declaration=len({p for p,v in declarations if re.match(r'^[~^]?22\.',str(v))}),resolved_versions_established=0,signal_form_usage_established=0,applications_admitted=0)
    print(json.dumps(summary,indent=2))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--private-directory',type=Path);a=p.parse_args();main(a.private_directory)
