#!/usr/bin/env python3
"""Seal quiescent private evidence for public CI artifact transport.

CMS AuthEnvelopedData: AES-256-GCM; RSA-OAEP with SHA256 recipient key wrap.
Only the public certificate is needed on CI. Never follows evidence symlinks.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import stat
import subprocess
import tarfile
import tempfile

MAX_BYTES=512*1024*1024
MAX_ENTRIES=100000


def sha(path):
    h=hashlib.sha256()
    with Path(path).open('rb') as stream:
        for chunk in iter(lambda:stream.read(1024*1024),b''):h.update(chunk)
    return h.hexdigest()


def inventory(root):
    result=[]; total=0
    def visit(path):
        nonlocal total
        info=path.lstat(); relative=path.relative_to(root).as_posix()
        if relative=='_archive-inventory.json':raise ValueError('Reserved archive member')
        row=dict(path=relative,mode=stat.S_IMODE(info.st_mode),uid=info.st_uid,gid=info.st_gid,mtime_ns=info.st_mtime_ns)
        if path.is_symlink():row.update(kind='symlink',target=os.readlink(path))
        elif stat.S_ISDIR(info.st_mode):row['kind']='directory'
        elif stat.S_ISREG(info.st_mode) and info.st_nlink==1:
            total+=info.st_size
            if total>MAX_BYTES:raise ValueError('Private evidence size bound')
            row.update(kind='file',bytes=info.st_size,sha256=sha(path))
        else:raise ValueError('Unsupported evidence file kind/hardlink')
        result.append(row)
        if len(result)>MAX_ENTRIES:raise ValueError('Private evidence entry bound')
        if row['kind']=='directory':
            for child in sorted(path.iterdir()):visit(child)
    visit(root)
    return result,total


def seal(source,recipient,destination):
    source=Path(source).resolve(strict=True);recipient=Path(recipient).resolve(strict=True)
    destination=Path(destination).resolve()
    if not source.is_dir() or destination==source or source in destination.parents or destination in source.parents:
        raise ValueError('Separate private source and new public output directories required')
    if destination.exists():raise ValueError('Never overwrite an existing sealed evidence output')
    destination.mkdir(mode=0o700)
    ciphertext=destination/'private-evidence.cms'
    try:
        # OpenSSL verifies certificate readability before potentially large archive work.
        subprocess.run(['openssl','x509','-in',str(recipient),'-noout'],check=True,capture_output=True,timeout=15)
        rows,total=inventory(source)
        with tempfile.TemporaryDirectory(prefix='nginx-seal-private-',dir=source.parent) as temporary:
            temporary=Path(temporary);temporary.chmod(0o700)
            archive=temporary/'evidence.tar.gz'
            internal=temporary/'_archive-inventory.json'
            internal.write_text(json.dumps({'entries':rows,'total_file_bytes':total},indent=2)+'\n')
            with tarfile.open(archive,'w:gz',dereference=False,format=tarfile.PAX_FORMAT) as tar:
                for row in rows:
                    relative=row['path'];path=source if relative=='.' else source/relative
                    tar.add(path,arcname='evidence' if relative=='.' else 'evidence/'+relative,recursive=False)
                tar.add(internal,arcname='_archive-inventory.json',recursive=False)
            if inventory(source)!=(rows,total):raise ValueError('Evidence changed while archiving')
            subprocess.run(['openssl','cms','-encrypt','-binary','-aes-256-gcm',
                '-in',str(archive),'-outform','DER','-out',str(ciphertext),'-recip',str(recipient),
                '-keyopt','rsa_padding_mode:oaep','-keyopt','rsa_oaep_md:sha256'],
                check=True,capture_output=True,timeout=120)
            report={'status':'private_evidence_encrypted_not_application_qualification',
                'format':'CMS AuthEnvelopedData DER','content_cipher':'AES-256-GCM','key_wrap':'RSA-OAEP-SHA256',
                'recipient_certificate_sha256':sha(recipient),'ciphertext_sha256':sha(ciphertext),
                'ciphertext_bytes':ciphertext.stat().st_size,'archive_sha256':sha(archive),
                'archive_bytes':archive.stat().st_size,'private_entries':len(rows),'private_file_bytes':total}
        (destination/'sealed-evidence.json').write_text(json.dumps(report,indent=2)+'\n')
        return report
    except Exception:
        ciphertext.unlink(missing_ok=True)
        # No plaintext, exception text, raw filenames or credentials enter public output.
        (destination/'seal-failure.json').write_text('{"status":"private_evidence_sealing_failed"}\n')
        raise


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--source',required=True);parser.add_argument('--recipient',required=True);parser.add_argument('--output',required=True)
    args=parser.parse_args()
    try:seal(args.source,args.recipient,args.output)
    except Exception:raise SystemExit('Private evidence sealing failed; no plaintext uploaded') from None

if __name__=='__main__':main()
