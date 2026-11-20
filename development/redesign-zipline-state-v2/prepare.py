import hashlib,json,os,pathlib,tarfile,zipfile
root=pathlib.Path(__file__).resolve().parents[2];base=pathlib.Path(os.environ['ORDINARY_BASE']);out=base/'evidence'
archive=base/'build.zip'
def digest(f):
 h=hashlib.sha256()
 for b in iter(lambda:f.read(1048576),b''):h.update(b)
 return h.hexdigest()
with archive.open('rb') as f: assert digest(f)=='07da97081df579cf956e505c488615d54ada2bb1ab90cedd70390ab69d9eecce'
with zipfile.ZipFile(archive) as z:
 with z.open('runtime.tar.gz') as f: assert digest(f)=='dbf090816575df888722ba852a3337b9c1bb98f8a29da56141a34ed4c54a20e8'
 with z.open('runtime.tar.gz') as f,tarfile.open(fileobj=f,mode='r|gz') as t:t.extractall(base/'runtime',filter='data')
entry=root/'results/redesign-development-source-wave17-v1/1.txt';(base/'entrypoint.sh').write_bytes(entry.read_bytes())
(out/'bundle-verification.json').write_text(json.dumps({'status':'verified','artifact_id':14624849143,'runtime_sha256':'dbf090816575df888722ba852a3337b9c1bb98f8a29da56141a34ed4c54a20e8','entrypoint_sha256':hashlib.sha256(entry.read_bytes()).hexdigest()})+'\n')
