#!/usr/bin/env python3
"""Verify hashes and reconstruct the archived RealWorld field-control ledger."""
import hashlib
import json
from pathlib import Path
from validate_realworld_field_campaign import validate
ROOT=Path(__file__).resolve().parents[1]


def verify_failed_attempt():
    manifest=json.loads((ROOT/'manifests/realworld-field-validator-failure.json').read_bytes())
    directory=ROOT/manifest['evidence_directory']
    files={str(p.relative_to(directory)):p for p in directory.rglob('*') if p.is_file()}
    if set(files)!=set(manifest['input_sha256']):raise ValueError('Failed-attempt inventory differs')
    for name,path in files.items():
        if hashlib.sha256(path.read_bytes()).hexdigest()!=manifest['input_sha256'][name]:raise ValueError('Failed-attempt hash differs: '+name)
    if manifest['qualified'] is not False:raise ValueError('Failed validation cannot qualify an attempt')


def main():
    verify_failed_attempt()
    manifest=json.loads((ROOT/'manifests/realworld-field-integration-qualification.json').read_bytes())
    directory=ROOT/manifest['evidence_directory']
    files={str(p.relative_to(directory)):p for p in directory.rglob('*') if p.is_file()}
    if set(files)!=set(manifest['input_sha256']):raise ValueError('Archive inventory differs')
    for name,path in files.items():
        if hashlib.sha256(path.read_bytes()).hexdigest()!=manifest['input_sha256'][name]:raise ValueError('Archive hash differs: '+name)
    if validate(directory)!=manifest['verification']:raise ValueError('Archive ledger verification differs')
    print('RealWorld field archive and eighteen-branch engineering ledger verified.')


if __name__=='__main__':main()
