#!/usr/bin/env python3
"""Build data-only generator bundles with a strict allowlist; no model is run."""
import argparse
import gzip
import hashlib
import io
import json
from pathlib import Path
import tarfile
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/restestbench-generator-inputs-v1'


def blob(raw):return hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()

def packed(files):
    buffer=io.BytesIO()
    with gzip.GzipFile(filename='',mode='wb',fileobj=buffer,mtime=0) as zipped,tarfile.open(fileobj=zipped,mode='w|') as archive:
        for name,raw in sorted(files.items()):
            member=tarfile.TarInfo(name);member.size=len(raw);member.mtime=0;archive.addfile(member,io.BytesIO(raw))
    return buffer.getvalue()


def validate_bundle(raw, expected):
    found={}
    with tarfile.open(fileobj=io.BytesIO(raw)) as archive:
        for member in archive:
            assert member.isfile() and member.name not in found
            assert member.name in expected, member.name
            found[member.name]=archive.extractfile(member).read()
    assert found==expected
    for name,content in found.items():
        value=json.loads(content)
        if name.endswith('/requirements.json'):
            assert all(set(row)=={'id','description'} for row in value)
            assert len({row['id'] for row in value})==len(value)
            assert all(isinstance(row['description'],str) and row['description'].strip() for row in value)
    return {name:hashlib.sha256(raw).hexdigest() for name,raw in sorted(found.items())}


def build():
    inventory=json.loads((ROOT/'manifests/restestbench-source-inventory-v1.json').read_text())
    pins=json.loads((ROOT/'evidence/restestbench-specs-v1/pins.json').read_text());assert pins['commit']==inventory['pin']
    specs={}
    for row in pins['files']:
        raw=(ROOT/row['local_path']).read_bytes();assert blob(raw)==row['git_blob']
        specs[row['path'].split('/')[1]]=raw
    requirements={}
    allowed={r['path']:r['git_blob'] for entries in inventory['services'].values() for r in entries}
    with tarfile.open(ROOT/'results/restestbench-applicability-v1/inputs.tar.gz') as archive:
        for member in archive:
            if member.name in allowed:
                raw=archive.extractfile(member).read();assert blob(raw)==allowed[member.name]
                requirements[member.name]=json.loads(raw)
    assert set(requirements)==set(allowed)
    bundles={};summary={}
    for mode in ['vague','precise']:
        files={}
        for service,entries in sorted(inventory['services'].items()):
            rows=[]
            for entry in entries:
                original=requirements[entry['path']];assert original['service']==service
                rows.append({'id':original['id'],'description':original['requirement_'+mode]})
            files[service+'/requirements.json']=(json.dumps(sorted(rows,key=lambda r:r['id']),indent=2)+'\n').encode()
            files[service+'/spec.json']=specs[service]
        raw=packed(files);hashes=validate_bundle(raw,files);bundles[mode]=raw
        summary[mode]={'files':hashes,'file_count':len(hashes),'requirement_count':sum(len(x) for x in inventory['services'].values()),'archive_sha256':hashlib.sha256(raw).hexdigest()}
    return bundles,{'kind':'restestbench_generator_inputs_v1','upstream_commit':inventory['pin'],'variants':summary,'allowed_requirement_fields':['id','description'],'models_run':0,'runtime_isolation_tested':False,'independent_held_out_dataset_claimed':False,'researcher_exposure':['requirement descriptions','mutation definitions','golden tests','released result records'],'generator_execution_registered':False}


def main():
    p=argparse.ArgumentParser();p.add_argument('--verify',action='store_true');args=p.parse_args()
    bundles,summary=build();manifest=ROOT/'manifests/restestbench-generator-inputs-v1.json'
    if args.verify:
        assert json.loads(manifest.read_text())==summary
        for mode,raw in bundles.items():assert (OUT/(mode+'.tar.gz')).read_bytes()==raw
    else:
        assert not manifest.exists();OUT.mkdir(parents=True,exist_ok=True)
        for mode,raw in bundles.items():
            target=OUT/(mode+'.tar.gz');assert not target.exists();target.write_bytes(raw)
        manifest.write_text(json.dumps(summary,indent=2)+'\n')
    print(json.dumps({mode:{'files':v['file_count'],'requirements':v['requirement_count'],'bytes':len(bundles[mode])} for mode,v in summary['variants'].items()}))

if __name__=='__main__':main()
