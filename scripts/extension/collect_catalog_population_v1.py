#!/usr/bin/env python3
"""Collect the registered catalog archive and apply frozen metadata rules."""
import hashlib
import json
import re
import signal
import subprocess
import tarfile
import time
import urllib.request
from pathlib import Path
from urllib.parse import urlsplit

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'results/catalog-population-v1'
REV='114743487b2cfd1a9c68deff3511c11c3b307695'
LICENSES=set('0BSD MIT Apache-2.0 BSD-2-Clause BSD-3-Clause GPL-2.0 GPL-3.0 AGPL-3.0 MPL-2.0 ISC EPL-2.0 LGPL-2.1 LGPL-3.0 Unlicense'.split())
URL_RE=re.compile(r'https?://(?:www\.)?github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)',re.I)

def norm(value):return re.sub('[^a-z0-9]','',value.lower())
def repo_name(url):
    parsed=urlsplit(url)
    if parsed.scheme!='https' or parsed.netloc!='github.com' or parsed.query or parsed.fragment:return None
    path=parsed.path.strip('/')
    if not re.fullmatch(r'[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+',path):return None
    return path.removesuffix('.git').lower()

def evaluate(path,data,prior):
    errors=[];matches=[];repo=None
    if not isinstance(data,dict) or not all(isinstance(data.get(k),str) for k in ['name','source_code_url']) or not all(isinstance(data.get(k),list) and all(isinstance(v,str) for v in data[k]) for k in ['platforms','licenses']):
        return {'failed_checks':['schema'],'prior_matches':[],'repository':None}
    repo=repo_name(data['source_code_url'])
    if not repo:errors.append('github_root_url')
    if 'Docker' not in data['platforms']:errors.append('docker_label')
    if data.get('depends_3rdparty',False) is not False:errors.append('third_party_dependency')
    if not data['licenses'] or any(re.sub(r'-(only|or-later)$','',v) not in LICENSES for v in data['licenses']):errors.append('license_screen')
    aliases={norm(Path(path).stem),norm(data['name'])}
    for old in sorted(prior):
        if (repo and (repo==old or repo.split('/')[0]==old.split('/')[0])) or norm(old.split('/')[-1]) in aliases:matches.append(old)
    if matches:errors.append('prior_overlap')
    if re.search(r'\bfork\b',str(data.get('description','')),re.I) or any(k in data for k in ['fork_of','forked_from']):errors.append('fork_metadata')
    return {'failed_checks':errors,'prior_matches':matches,'repository':repo}

def select(rows):
    eligible={}
    for row in rows:
        if not row['failed_checks']:eligible.setdefault(row['repository'],[]).append(row['path'])
    ranked=[]
    for repo,paths in eligible.items():
        ranked.append({'repository':repo,'catalog_paths':sorted(paths),'representative':sorted(paths)[0],'rank_sha256':hashlib.sha256(('catalog-independent-v1|'+REV+'|'+repo).encode()).hexdigest()})
    ranked.sort(key=lambda r:(r['rank_sha256'],r['repository']))
    owners={};selected=[]
    for row in ranked:
        owner=row['repository'].split('/')[0]
        if owner in owners:row.update(disposition='shared_owner_group',group_representative=owners[owner])
        elif len(selected)<12:
            owners[owner]=row['repository'];row['disposition']='selected';selected.append(row['repository'])
        else:row['disposition']='beyond_twelve_owner_ceiling'
    return ranked,selected

def main():
    OUT.mkdir(exist_ok=False);start=time.monotonic()
    result={'status':'failed','revision':REV,'rows':[]}
    try:
        assert subprocess.check_output(['ruby','-r','yaml','-e','puts RUBY_VERSION;puts Psych::VERSION'],text=True).split()==['2.6.10','3.1.0']
        def deadline(*args):raise TimeoutError('120-second acquisition deadline')
        signal.signal(signal.SIGALRM,deadline);signal.alarm(120)
        archive=OUT/'catalog.tar.gz';used=0
        with urllib.request.urlopen('https://codeload.github.com/awesome-selfhosted/awesome-selfhosted-data/tar.gz/'+REV,timeout=120) as response,archive.open('wb') as output:
            while True:
                if time.monotonic()-start>120:raise ValueError('Acquisition deadline')
                chunk=response.read(65536)
                if not chunk:break
                used+=len(chunk)
                if used>20*1024*1024:raise ValueError('Compressed byte bound')
                output.write(chunk)
        signal.alarm(0)
        result.update(archive_sha256=hashlib.sha256(archive.read_bytes()).hexdigest(),archive_bytes=used)
        tree=json.loads((ROOT/'results/catalog-frame-metadata-v1/3.json').read_text())['tree']
        expected={r['path']:r for r in tree if r['path'].startswith('software/') and r['type']=='blob'}
        assert len(expected)==1362
        texts={};total=0;members=0;decoded=0
        with tarfile.open(archive,'r:gz') as tf:
            for item in tf:
                members+=1
                if members>3000:raise ValueError('Archive member bound')
                if item.isfile():total+=item.size
                if total>20*1024*1024:raise ValueError('Uncompressed byte bound')
                relative=item.name.split('/',1)[1] if '/' in item.name else ''
                if relative not in expected and relative!='AUTHORS':continue
                assert item.isfile()
                if relative in texts:raise ValueError('Duplicate member')
                if item.size>64*1024:raise ValueError('Entry byte bound')
                raw=tf.extractfile(item).read()
                if relative=='AUTHORS':
                    (OUT/'AUTHORS').write_bytes(raw);continue
                decoded+=len(raw)
                if decoded>2*1024*1024:raise ValueError('Software total byte bound')
                assert len(raw)==expected[relative]['size']
                assert hashlib.sha1(b'blob '+str(len(raw)).encode()+b'\0'+raw).hexdigest()==expected[relative]['sha']
                texts[relative]=raw.decode('utf8')
        assert set(texts)==set(expected)
        assert (OUT/'AUTHORS').is_file()
        (OUT/'LICENSE').write_bytes((ROOT/'results/catalog-frame-metadata-v1/license.txt').read_bytes())
        (OUT/'software-metadata.json').write_text(json.dumps(texts,indent=2)+'\n')
        ruby='x=JSON.parse(STDIN.read); out={}; x.each{|k,v| begin; out[k]={"data"=>YAML.safe_load(v, permitted_classes: [Date,Time], aliases: false)}; rescue => e; out[k]={"error"=>e.class.to_s+": "+e.message}; end}; puts JSON.generate(out)'
        parsed=json.loads(subprocess.check_output(['ruby','-r','yaml','-r','json','-r','date','-e',ruby],input=json.dumps(texts).encode(),timeout=30))
        prior={r['repository'] for r in json.loads((ROOT/'manifests/prior-repository-reference-index-v2.json').read_text())['references']}
        for directory in ['catalog-schema-v1','catalog-entry-template-v1']:
            for path in (ROOT/'results'/directory).glob('*.txt'):
                prior.update(m[1].rstrip('.').removesuffix('.git').lower() for m in URL_RE.finditer(path.read_text()))
        result['prior_repositories']=sorted(prior)
        for path in sorted(texts):
            obj=parsed[path];row={'path':path,'blob_sha':expected[path]['sha']}
            if 'error' in obj:row.update(failed_checks=['yaml_parse'],error=obj['error'],repository=None)
            else:row.update(evaluate(path,obj['data'],prior))
            row['disposition']=row['failed_checks'][0] if row['failed_checks'] else 'eligible_before_grouping'
            result['rows'].append(row)
        ranked,selected=select(result['rows'])
        from collections import Counter
        result.update(status='metadata_sample_selected_no_application_sources',population_entries=len(texts),software_bytes=decoded,ranked=ranked,selected=selected,disposition_counts=dict(Counter(r['disposition'] for r in result['rows'])))
    except Exception as error:result.update(error_type=type(error).__name__,error=str(error))
    signal.alarm(0)
    result['elapsed_seconds']=time.monotonic()-start
    (OUT/'selection.json').write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:v for k,v in result.items() if k not in ['rows','ranked','prior_repositories']},indent=2))

if __name__=='__main__':main()
