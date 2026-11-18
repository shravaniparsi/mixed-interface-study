#!/usr/bin/env python3
"""Private inventory of exactly the paths reported by Docker diff.

Run inside the original container via python3. Stdin is a bounded JSON path list;
no traversal of directories or symlink targets, no application writes.
"""
import hashlib
import json
import os
from pathlib import PurePosixPath
import stat
import sys


def validate_paths(paths):
    if not isinstance(paths,list) or len(paths)>100000 or len(set(paths))!=len(paths):
        raise ValueError('Root-layer path count/uniqueness')
    for path in paths:
        if not isinstance(path,str) or not path.startswith('/') or str(PurePosixPath(path))!=path or '..' in PurePosixPath(path).parts or '\0' in path:
            raise ValueError('Noncanonical absolute root-layer path')
    return sorted(paths)


def inspect_paths(paths):
    rows=[];total=0
    for path in validate_paths(paths):
        try:before=os.lstat(path)
        except FileNotFoundError:
            rows.append({'path':path,'kind':'absent'});continue
        row=dict(path=path,mode=stat.S_IMODE(before.st_mode),uid=before.st_uid,gid=before.st_gid,mtime_ns=before.st_mtime_ns)
        if os.listxattr(path,follow_symlinks=False):raise ValueError('Unrecorded root-layer extended attributes')
        if stat.S_ISDIR(before.st_mode):row['kind']='directory'
        elif stat.S_ISLNK(before.st_mode):row.update(kind='symlink',target=os.readlink(path))
        elif stat.S_ISREG(before.st_mode):
            total+=before.st_size
            if total>2*1024**3:raise ValueError('Root-layer byte bound')
            h=hashlib.sha256()
            with open(path,'rb') as stream:
                for part in iter(lambda:stream.read(1024**2),b''):h.update(part)
            row.update(kind='file',bytes=before.st_size,sha256=h.hexdigest(),links=before.st_nlink)
        elif stat.S_ISFIFO(before.st_mode):row['kind']='fifo'
        elif stat.S_ISSOCK(before.st_mode):row['kind']='socket'
        else:raise ValueError('Unexpected root-layer device file')
        after=os.lstat(path)
        for field in ('st_dev','st_ino','st_mode','st_uid','st_gid','st_size','st_mtime_ns','st_ctime_ns'):
            if getattr(before,field)!=getattr(after,field):raise ValueError('Root-layer path changed during inspection')
        rows.append(row)
    return {'rows':rows,'file_bytes':total,'extended_attributes_absent':True}

if __name__=='__main__':
    raw=sys.stdin.buffer.read(8*1024*1024+1)
    if len(raw)>8*1024*1024:raise ValueError('Root-layer input bound')
    print(json.dumps(inspect_paths(json.loads(raw))))
