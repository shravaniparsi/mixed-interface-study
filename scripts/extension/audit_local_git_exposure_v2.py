"""Scan available precollection Git blobs without lazy fetching or checkout changes."""
import hashlib,json,os,re,subprocess
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
LIMIT=5*1024*1024
EXTENSIONS={'.json','.md','.txt','.py','.js','.cjs','.mjs','.yml','.yaml','.ts'}
def main():
    prior=json.loads((ROOT/'manifests/project-reference-exposure-index-v1.json').read_text())
    revision=prior['source_head'];env=dict(os.environ,GIT_NO_LAZY_FETCH='1',GIT_TERMINAL_PROMPT='0')
    def git(*args):return subprocess.check_output(['git',*args],cwd=ROOT,env=env)
    # --batch-all-objects enumerates local objects, including unreachable ones;
    # only blobs referenced by the frozen precollection tree are inspected below.
    local={}
    for line in git('cat-file','--batch-all-objects','--batch-check=%(objectname) %(objecttype) %(objectsize)').decode().splitlines():
        sha,kind,size=line.split()
        if kind=='blob':local[sha]=int(size)
    entries=[]
    for row in git('ls-tree','-rz',revision).split(b'\0'):
        if not row:continue
        metadata,name=row.split(b'\t',1);mode,kind,sha=metadata.decode().split();entries.append((name.decode(),kind,sha))
    available=[];skipped=[];refs={};bytes_read=0;cache={}
    pattern=re.compile(r'(?:https?://github\.com/|\brepos/)([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)')
    for path,kind,sha in entries:
        reason=None
        if kind!='blob':reason='not_blob'
        elif Path(path).suffix.lower() not in EXTENSIONS:reason='extension'
        elif sha not in local:reason='not_in_local_object_inventory'
        elif local[sha]>LIMIT:reason='over_5MiB'
        if reason:skipped.append(dict(path=path,object=sha,reason=reason));continue
        if sha not in cache:
            if bytes_read+local[sha]>128*1024*1024:raise RuntimeError('128MiB aggregate read bound')
            raw=git('cat-file','blob',sha);bytes_read+=len(raw)
            assert len(raw)==local[sha]
            try:text=raw.decode()
            except UnicodeDecodeError:cache[sha]=None;skipped.append(dict(path=path,object=sha,reason='not_utf8'));continue
            cache[sha]=(hashlib.sha256(raw).hexdigest(),sorted(set(m.group(1).removesuffix('.git').lower().rstrip('.') for m in pattern.finditer(text))))
        content=cache[sha]
        if content is None:skipped.append(dict(path=path,object=sha,reason='not_utf8'));continue
        digest,names=content;available.append(dict(path=path,object=sha,bytes=local[sha],sha256=digest))
        for name in names:refs.setdefault(name,[]).append(path)
    frame=json.loads((ROOT/'manifests/independent-project-frame-feasibility-v1.json').read_text())
    rows=[dict(full_name=r['full_name'],reference_paths=refs.get(r['full_name'].lower(),[])) for r in frame['rows']]
    output=dict(kind='available_precollection_git_blob_reference_audit',source_head=revision,prior_index='project-reference-exposure-index-v1.json',network_fetches=0,unique_blob_bytes_read=bytes_read,repositories=refs,available=available,skipped=skipped,frame_matches=rows,scope='Literal references only; absent match is not proof of unexposed or independent origins')
    (ROOT/'manifests/project-reference-exposure-index-v2.json').write_text(json.dumps(output,indent=2)+'\n')
    from collections import Counter
    print(json.dumps(dict(scanned=len(available),skipped=dict(Counter(r['reason'] for r in skipped)),bytes_read=bytes_read,repository_references=len(refs),frame_matches=sum(bool(r['reference_paths']) for r in rows)),indent=2))
if __name__=='__main__':main()
