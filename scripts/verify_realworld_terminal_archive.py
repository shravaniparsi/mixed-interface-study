#!/usr/bin/env python3
"""Verify hashes and reconstruct the archived RealWorld terminal control ledger."""
import hashlib
import json
from pathlib import Path
from validate_realworld_terminal_campaign import validate
ROOT=Path(__file__).resolve().parents[1]


def main():
    manifest=json.loads((ROOT/'manifests/realworld-terminal-integration-qualification.json').read_bytes())
    directory=ROOT/manifest['evidence_directory']
    files={str(p.relative_to(directory)):p for p in directory.rglob('*') if p.is_file()}
    if set(files)!=set(manifest['input_sha256']):raise ValueError('Archive inventory differs')
    for name,path in files.items():
        if hashlib.sha256(path.read_bytes()).hexdigest()!=manifest['input_sha256'][name]:raise ValueError('Archive hash differs: '+name)
    if validate(directory)!=manifest['verification']:raise ValueError('Archive ledger verification differs')
    print('RealWorld terminal archive and eight-branch baseline ledger verified.')


if __name__=='__main__':main()
