"""Compute original root-tree identity from retained recursive Git entries."""
import hashlib
import re


def root_tree_sha(entries):
    by_directory={'':[]};seen=set()
    for row in entries:
        path=row['path']
        if path in seen or path.startswith('/') or any(part in ('','.','..') for part in path.split('/')):
            raise ValueError('Duplicate or noncanonical Git tree path')
        seen.add(path)
        if not re.fullmatch('[0-9a-f]{40}',row['sha']):raise ValueError('Invalid object identity')
        kind,mode=row['type'],row['mode']
        if (kind,mode) not in {('tree','040000'),('blob','100644'),('blob','100755'),('blob','120000')}:
            raise ValueError('Unsupported original Git tree entry')
        parent,_,name=path.rpartition('/')
        by_directory.setdefault(parent,[]).append((name,row))
        if kind=='tree':by_directory.setdefault(path,[])
    directories={row['path']:row['sha'] for row in entries if row['type']=='tree'}
    if set(by_directory)!={''}|set(directories):raise ValueError('Missing parent tree')
    computed={}
    for directory,rows in by_directory.items():
        # Git compares directory names with a trailing slash for ordering.
        ordered=sorted(rows,key=lambda pair:(pair[0]+('/' if pair[1]['type']=='tree' else '')).encode())
        raw=b''.join(row['mode'].lstrip('0').encode()+b' '+name.encode()+b'\0'+bytes.fromhex(row['sha']) for name,row in ordered)
        computed[directory]=hashlib.sha1(b'tree '+str(len(raw)).encode()+b'\0'+raw).hexdigest()
    for directory,expected in directories.items():
        if computed[directory]!=expected:raise ValueError('Recursive tree identity mismatch')
    return computed['']
