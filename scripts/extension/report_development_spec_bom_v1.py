#!/usr/bin/env python3
import argparse
import hashlib
import json
from pathlib import Path
import re
import xml.etree.ElementTree as E
ROOT=Path(__file__).resolve().parents[2]
PRIVATE=Path('/private/tmp/development-spec-bom-v1')
OUT=ROOT/'manifests/development-spec-bom-v1.json'

def build():
    raw=(PRIVATE/'collection.json').read_bytes()
    collection=json.loads(raw)
    assert len(collection['rows'])==2
    for row in collection['rows']:
        assert row['status']=='received'
        data=(PRIVATE/row['filename']).read_bytes()
        assert hashlib.sha256(data).hexdigest()==row['sha256'] and len(data)==row['bytes']
    pom=(PRIVATE/'bom.pom').read_bytes()
    checksum=(PRIVATE/'bom.sha1').read_text().strip()
    assert re.fullmatch('[0-9a-f]{40}',checksum)
    assert hashlib.sha1(pom).hexdigest()==checksum
    root=E.fromstring(pom);ns={'m':'http://maven.apache.org/POM/4.0.0'}
    props={e.tag.split('}')[1]:e.text for e in root.find('m:properties',ns)}
    def coords(e):
        return {k:e.findtext('m:'+k,default='',namespaces=ns) for k in ['groupId','artifactId','version','type','scope']}
    selected=[]
    for e in root.findall('./m:dependencyManagement/m:dependencies/m:dependency',ns):
        d=coords(e)
        if d['groupId']=='org.springdoc' or d['scope']=='import':
            m=re.fullmatch(r'\$\{([^}]+)\}',d['version'])
            d['local_property_value']=props.get(m[1]) if m else None
            selected.append(d)
    return dict(kind='development_dependency_bom_metadata',freeze='ec11116',collection=collection,
                collection_sha256=hashlib.sha256(raw).hexdigest(),same_origin_sha1_matches=True,
                parent=coords(root.find('m:parent',ns)),selected_dependencies=selected,
                actual_gradle_resolution=False,independent_evaluation_cases=0)
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');args=p.parse_args()
    text=json.dumps(build(),indent=2)+'\n'
    if args.verify:
        assert OUT.read_text()==text
        print('BOM provenance, checksum and local properties verified')
    else:OUT.write_text(text)
