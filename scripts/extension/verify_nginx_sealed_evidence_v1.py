#!/usr/bin/env python3
"""Authenticate retained ciphertext and audit archive members without extraction.

Decrypt only to a new local private directory. No credential/key/content output.
A failed OpenSSL authentication never releases plaintext for subsequent reading.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import subprocess
import tarfile
from seal_nginx_evidence_v1 import sha, MAX_BYTES, MAX_ENTRIES

MAX_ARCHIVE=600*1024*1024


def audit_archive(path):
    # Streaming prevents a malicious oversized tar member from being skipped or
    # decompressed before its declared size is checked. No member is extracted.
    observed={};manifest=None;total=0
    with tarfile.open(path,'r|gz') as archive:
        for member in archive:
            if member.name in observed:raise ValueError('Duplicate archive member')
            if len(observed)>=MAX_ENTRIES+1:raise ValueError('Archive member bound')
            row=dict(mode=member.mode,uid=member.uid,gid=member.gid,mtime_seconds=int(member.mtime))
            if member.name=='_archive-inventory.json':
                if not member.isfile() or not 0<=member.size<=64*1024*1024:raise ValueError('Private inventory missing/oversized')
                manifest=json.load(archive.extractfile(member));row['kind']='inventory'
            elif member.isfile():
                if member.size<0 or total+member.size>MAX_BYTES:raise ValueError('Private uncompressed byte bound')
                total+=member.size;h=hashlib.sha256();stream=archive.extractfile(member)
                for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
                row.update(kind='file',bytes=member.size,sha256=h.hexdigest())
            elif member.isdir():row['kind']='directory'
            elif member.issym():row.update(kind='symlink',target=member.linkname)
            else:raise ValueError('Unsupported archived member kind')
            observed[member.name]=row
    if manifest is None:raise ValueError('Private inventory missing')
    rows=manifest['entries']
    if not isinstance(rows,list) or len(rows)>MAX_ENTRIES:raise ValueError('Private inventory row bound')
    expected={}
    for row in rows:
        relative=row['path']
        if not isinstance(relative,str) or (relative!='.' and (str(PurePosixPath(relative))!=relative or relative.startswith('/') or '..' in PurePosixPath(relative).parts)):
            raise ValueError('Noncanonical private inventory path')
        name='evidence' if relative=='.' else 'evidence/'+relative
        if name in expected:raise ValueError('Duplicate private inventory path')
        expected[name]=row
        actual=observed.get(name)
        if actual is None:raise ValueError('Inventory member missing')
        compared={k:v for k,v in row.items() if k not in ('path','mtime_ns')}
        compared['mtime_seconds']=row['mtime_ns']//1000000000
        if actual!=compared:raise ValueError('Private archive member/metadata/digest differs')
    if set(observed)!=set(expected)|{'_archive-inventory.json'}:raise ValueError('Unregistered archive member')
    if total!=manifest['total_file_bytes']:raise ValueError('Private byte count differs')
    return {'members_verified':len(rows),'private_file_bytes_verified':total,'members_extracted':0}


def recover(ciphertext,report,recipient,key,output):
    ciphertext,report,recipient,key=map(lambda p:Path(p).resolve(strict=True),(ciphertext,report,recipient,key))
    info=json.loads(report.read_text())
    if info['format']!='CMS AuthEnvelopedData DER' or info['content_cipher']!='AES-256-GCM' or info['key_wrap']!='RSA-OAEP-SHA256':raise ValueError('Unexpected sealed format')
    if not 0<info['archive_bytes']<=MAX_ARCHIVE or ciphertext.stat().st_size>MAX_ARCHIVE+32768:raise ValueError('Encrypted/archive byte bound')
    if ciphertext.stat().st_size!=info['ciphertext_bytes'] or sha(ciphertext)!=info['ciphertext_sha256'] or sha(recipient)!=info['recipient_certificate_sha256']:
        raise ValueError('Published ciphertext/recipient identity mismatch')
    output=Path(output).resolve()
    output.mkdir(mode=0o700,exist_ok=False)
    partial=output/'unverified.partial';final=output/'authenticated-evidence.tar.gz'
    try:
        with partial.open('xb') as destination:
            os.chmod(partial,0o600)
            subprocess.run(['openssl','cms','-decrypt','-binary','-inform','DER','-in',str(ciphertext),
                '-recip',str(recipient),'-inkey',str(key)],stdout=destination,stderr=subprocess.PIPE,check=True,timeout=120)
        if partial.stat().st_size!=info['archive_bytes'] or sha(partial)!=info['archive_sha256']:
            raise ValueError('Authenticated archive differs from published identity')
        audit=audit_archive(partial)
        if audit['members_verified']!=info['private_entries'] or audit['private_file_bytes_verified']!=info['private_file_bytes']:
            raise ValueError('Public and private evidence counts differ')
        partial.rename(final)
        result={'status':'encrypted_archive_authenticated_and_members_verified_not_scientific_validation',
            'ciphertext_sha256':info['ciphertext_sha256'],'archive_sha256':info['archive_sha256'],**audit}
        (output/'recovery-verification.json').write_text(json.dumps(result,indent=2)+'\n')
        return result
    except Exception:
        partial.unlink(missing_ok=True)
        raise

if __name__=='__main__':
    parser=argparse.ArgumentParser()
    for name in ('ciphertext','report','recipient','key','output'):parser.add_argument('--'+name,required=True)
    args=parser.parse_args()
    try:print(json.dumps(recover(**vars(args))))
    except Exception:raise SystemExit('Encrypted evidence recovery failed; no plaintext released') from None
