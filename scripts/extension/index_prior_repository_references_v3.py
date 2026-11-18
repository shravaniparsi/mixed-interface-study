#!/usr/bin/env python3
"""Index references in bounded tracked text blobs, with complete skip accounting."""
import hashlib
import json
import re
import subprocess
from pathlib import Path

ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'manifests/prior-repository-reference-index-v3.json'
EXTENSIONS={'.json','.md','.txt','.log','.py','.js','.mjs','.cjs','.yml','.yaml','.toml','.ts','.html','.csv','.lock','.sh'}
PATTERNS=[re.compile(r'https?://(?:www\.)?github\.com/([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)',re.I),
          re.compile(r'["\'](?:repository|full_name|repo)["\']\s*:\s*["\']([A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+)["\']')]


def main():
    if OUT.exists():raise ValueError('Reference snapshot already exists')
    head=subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip()
    entries=[]
    for item in subprocess.check_output(['git','ls-tree','-rz','--full-tree',head],cwd=ROOT).split(b'\0'):
        if not item:continue
        metadata,path=item.split(b'\t',1);mode,kind,oid=metadata.decode().split()
        entries.append((path.decode(),mode,kind,oid))
    entries.sort(key=lambda r:r[0].encode())
    # Enumerate only locally available objects; per-OID checks trigger lazy fetches.
    available=subprocess.check_output(['git','cat-file','--batch-all-objects','--batch-check=%(objectname) %(objecttype) %(objectsize)'],cwd=ROOT).decode().splitlines()
    object_info={line.split()[0]:line for line in available}
    sizes=[object_info.get(r[3],r[3]+' missing') for r in entries]
    proc=subprocess.Popen(['git','cat-file','--batch'],cwd=ROOT,stdin=subprocess.PIPE,stdout=subprocess.PIPE)
    rows=[];references={};used=0
    try:
        for (path,mode,kind,oid),info in zip(entries,sizes):
            bits=info.split();row={'path':path,'git_object':oid};rows.append(row)
            if len(bits)!=3 or bits[1]!='blob':row['status']='non_blob_or_missing';continue
            size=int(bits[2]);row['bytes']=size
            if mode not in ('100644','100755'):row['status']='non_regular';continue
            if Path(path).suffix.lower() not in EXTENSIONS:row['status']='nontext_extension';continue
            if size>8*1024*1024:row['status']='oversized';continue
            if used+size>512*1024*1024:row['status']='total_byte_limit';continue
            proc.stdin.write((oid+'\n').encode());proc.stdin.flush()
            header=proc.stdout.readline().decode().split();assert header==[oid,'blob',str(size)]
            raw=proc.stdout.read(size);assert len(raw)==size and proc.stdout.read(1)==b'\n';used+=size
            row['sha256']=hashlib.sha256(raw).hexdigest()
            try:text=raw.decode('utf8')
            except UnicodeDecodeError:row['status']='not_utf8';continue
            if '\0' in text:row['status']='binary_content';continue
            row['status']='scanned'
            found=set()
            for pattern in PATTERNS:
                for match in pattern.finditer(text):
                    name=match[1].rstrip('.').lower()
                    if name.endswith('.git'):name=name[:-4]
                    if name.split('/')[0] not in {'features','topics','orgs','settings','marketplace','search','collections','sponsors'}:found.add(name)
            for name in found:references.setdefault(name,[]).append(path)
    finally:
        proc.stdin.close();proc.wait(timeout=10)
    from collections import Counter
    result={'kind':'bounded_tracked_reference_exposure_index','source_head':head,'tracked_entries':len(entries),'scanned_bytes':used,'status_counts':dict(Counter(r['status'] for r in rows)),
            'files':rows,'references':[{'repository':name,'referring_paths':paths} for name,paths in sorted(references.items())],
            'absence_proves_no_exposure':False,'scope':'Tracked HEAD text plus prior audit artifacts present there; not all history, untracked files, conversation or model training.'}
    OUT.write_text(json.dumps(result,indent=2)+'\n')
    print(json.dumps({k:result[k] for k in ['source_head','tracked_entries','scanned_bytes','status_counts']}));print('repository references',len(references))


if __name__=='__main__':main()
