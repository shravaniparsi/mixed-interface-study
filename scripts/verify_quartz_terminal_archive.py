#!/usr/bin/env python3
"""Read-only hash and ledger verification of the terminal integration archive."""
import hashlib
import json
from pathlib import Path
from validate_quartz_terminal_campaign import verify

ROOT = Path(__file__).resolve().parents[1]


def main():
    manifest = json.loads((ROOT/'manifests/quartz-terminal-integration-qualification.json').read_bytes())
    directory = ROOT/manifest['evidence_directory']
    files = {str(p.relative_to(directory)):p for p in directory.rglob('*') if p.is_file()}
    if set(files) != set(manifest['input_sha256']): raise ValueError('Archive inventory differs')
    for name,path in files.items():
        if hashlib.sha256(path.read_bytes()).hexdigest() != manifest['input_sha256'][name]: raise ValueError('Archive hash differs: '+name)
    if verify(directory) != manifest['verification']: raise ValueError('Archive verification differs')
    print('Terminal archive hashes and control ledger verified; primary freeze remains incomplete.')


if __name__ == '__main__': main()
