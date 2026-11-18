#!/usr/bin/env python3
"""Verify build artifact without extracting or executing the application."""
import argparse, hashlib, json, pathlib, tarfile, zipfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=ROOT/'results/redesign-gomodel-build-v1'
def digest(stream):
    h=hashlib.sha256()
    for chunk in iter(lambda:stream.read(1048576),b''): h.update(chunk)
    return h.hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('archive',type=pathlib.Path);a=ap.parse_args()
    OUT.mkdir(exist_ok=True)
    with zipfile.ZipFile(a.archive) as z:
        result=json.loads(z.read('result.json'))
        assert result['status']=='build_succeeded' and result['application_executed'] is False and result['scientific_cases']==0
        assert result['revision']=='13bfff9c678dfbba25955f917a1ea233ae1e8630'
        assert z.read('freeze.txt').decode().strip()=='6eeac0ea3385d51b296d8666f27c218b001b18e1'
        tree=ROOT/'results/editability-repairability-repository-metadata-v1/01/3.json'
        assert hashlib.sha256(tree.read_bytes()).hexdigest()==result['tree_sha256']
        blobs=[e for e in json.loads(tree.read_text())['tree'] if e['type']=='blob']
        assert len(blobs)==result['verified_files']==3182
        assert sum(e['size'] for e in blobs)==result['verified_bytes']==40947087
        with z.open('executable.tar.gz') as f: assert digest(f)==result['executable_archive_sha256']
        expected={e['path']:e for e in result['outputs']};seen=set()
        with z.open('executable.tar.gz') as f, tarfile.open(fileobj=f,mode='r|gz') as tf:
            for entry in tf:
                assert entry.isfile() and entry.name in expected and entry.name not in seen
                row=expected[entry.name];assert entry.size==row['bytes']
                assert digest(tf.extractfile(entry))==row['sha256'];seen.add(entry.name)
        assert seen==set(expected) and 'bin/gomodel' in seen and 'internal/admin/dashboard/static/dist/index.html' in seen
        assert all(c['exit_code']==0 for c in result['commands'])
        assert any(c['command'][0:2]==['make','build'] for c in result['commands'])
        for name in z.namelist():
            if name=='executable.tar.gz':continue
            assert pathlib.PurePosixPath(name).name==name and z.getinfo(name).file_size<2*1024*1024
            (OUT/name).write_bytes(z.read(name))
    with a.archive.open('rb') as f: zip_sha=digest(f)
    summary={'status':'verified','run_id':44400417320,'artifact_id':14470959785,'artifact_zip_sha256':zip_sha,'artifact_zip_bytes':a.archive.stat().st_size,'verified_output_files':len(seen),'verified_output_bytes':sum(e['bytes'] for e in expected.values()),'application_executed':False,'scientific_cases':0,'binary_sha256':expected['bin/gomodel']['sha256'],'scope':'Artifact output hashes and frozen tree provenance; no runtime correctness or editability claim'}
    (OUT/'verification.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
if __name__=='__main__':main()
