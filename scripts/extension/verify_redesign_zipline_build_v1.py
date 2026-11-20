#!/usr/bin/env python3
"""Stream-verify the original build artifact without extracting/executing code."""
import argparse, hashlib, json, pathlib, posixpath, tarfile, zipfile
ROOT=pathlib.Path(__file__).resolve().parents[2]
OUT=ROOT/'results/redesign-zipline-build-v1'
def digest(stream):
    h=hashlib.sha256()
    for chunk in iter(lambda:stream.read(1048576),b''): h.update(chunk)
    return h.hexdigest()
def main():
    ap=argparse.ArgumentParser();ap.add_argument('archive',type=pathlib.Path);a=ap.parse_args()
    with a.archive.open('rb') as f: zip_sha=digest(f)
    assert zip_sha=='07da97081df579cf956e505c488615d54ada2bb1ab90cedd70390ab69d9eecce'
    assert a.archive.stat().st_size==159981865
    with zipfile.ZipFile(a.archive) as z:
        assert len(z.namelist())==len(set(z.namelist()))
        result=json.loads(z.read('result.json'))
        assert result['status']=='build_succeeded' and result['stage']=='complete'
        assert result['application_executed'] is False and result['scientific_cases']==0
        assert result['revision']=='49b81a290dfa59906c4d2a69f729460fc6357134'
        assert z.read('freeze.txt').decode().strip()=='2941bcce188fc516cf7a0523f4e89795e79b6638'
        tree=ROOT/'results/editability-repairability-repository-metadata-v1/02/3.json'
        assert hashlib.sha256(tree.read_bytes()).hexdigest()==result['tree_sha256']
        blobs=[e for e in json.loads(tree.read_text())['tree'] if e['type']=='blob']
        assert len(blobs)==result['verified_files']==737
        assert sum(e['size'] for e in blobs)==result['verified_bytes']==4408628
        assert z.read('node-version.txt').decode().strip()=='v24.11.1'
        assert z.read('pnpm-version.txt').decode().strip().splitlines()[-1]=='11.28.8'
        assert all(c['exit_code']==0 for c in result['commands'])
        assert [c['command'] for c in result['commands']]==[['node','--version'],['corepack','--version'],['corepack','pnpm','--version'],['corepack','pnpm','install','--frozen-lockfile'],['corepack','pnpm','run','build']]
        assert z.getinfo('runtime.tar.gz').file_size==result['runtime_archive_bytes']<=1024**3
        with z.open('runtime.tar.gz') as f: assert digest(f)==result['runtime_archive_sha256']
        expected={e['path']:e for e in result['outputs']};seen=set();total=0
        assert len(expected)==len(result['outputs'])
        with z.open('runtime.tar.gz') as f, tarfile.open(fileobj=f,mode='r|gz') as tf:
            for entry in tf:
                path=pathlib.PurePosixPath(entry.name)
                assert not path.is_absolute() and '..' not in path.parts
                assert entry.name in expected and entry.name not in seen
                row=expected[entry.name]
                if row['type']=='file':
                    assert entry.isfile() and entry.size==row['bytes'] and entry.mode & 0o777==row['mode']
                    assert digest(tf.extractfile(entry))==row['sha256'];total+=entry.size
                elif row['type']=='directory':
                    assert entry.isdir() and entry.mode & 0o777==row['mode']
                else:
                    assert row['type']=='symlink' and entry.issym() and entry.linkname==row['target']
                    assert not pathlib.PurePosixPath(entry.linkname).is_absolute()
                    target=posixpath.normpath(posixpath.join(str(path.parent),entry.linkname))
                    assert target in expected and not target.startswith('../')
                seen.add(entry.name)
        assert seen==set(expected)
        assert expected['build/server/index.js']['type']=='file' and expected['build/client/index.html']['type']=='file'
        assert total==result['output_regular_bytes']<=2*1024**3
        # Save only bounded evidence; keep the large runtime archive outside Git.
        OUT.mkdir(exist_ok=True)
        for name in z.namelist():
            if name=='runtime.tar.gz': continue
            assert pathlib.PurePosixPath(name).name==name and z.getinfo(name).file_size<32*1024**2
            (OUT/name).write_bytes(z.read(name))
    summary={'status':'verified','run_id':44729786431,'artifact_id':14624849143,'artifact_zip_sha256':zip_sha,'artifact_zip_bytes':a.archive.stat().st_size,'verified_output_entries':len(seen),'verified_regular_files':sum(r['type']=='file' for r in expected.values()),'verified_symlinks':sum(r['type']=='symlink' for r in expected.values()),'verified_output_bytes':total,'runtime_archive_sha256':result['runtime_archive_sha256'],'application_executed':False,'scientific_cases':0,'scope':'Artifact file identities, relative link membership, and recorded frozen source provenance; not startup or editability qualification.'}
    (OUT/'verification.json').write_text(json.dumps(summary,indent=2)+'\n');print(json.dumps(summary))
if __name__=='__main__':main()
