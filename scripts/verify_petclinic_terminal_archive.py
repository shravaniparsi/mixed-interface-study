#!/usr/bin/env python3
"""Verify retained PetClinic terminal campaign bytes and independently replay its ledger."""
from pathlib import Path
from petclinic_terminal_campaign import ROOT,read,sha
from validate_petclinic_terminal_campaign import validate

def main():
    q=read(ROOT/'manifests/petclinic-terminal-integration-qualification.json');d=ROOT/q['evidence_directory']
    files={str(p.relative_to(d)):p for p in d.rglob('*') if p.is_file()}
    if set(files)!=set(q['input_sha256']):raise ValueError('Archive inventory differs')
    for name,p in files.items():
        if sha(p)!=q['input_sha256'][name]:raise ValueError('Archive hash differs: '+name)
    if validate(d)!=q['verification']:raise ValueError('Archive ledger differs')
    print('PetClinic terminal archive and twelve-branch engineering ledger verified.')
if __name__=='__main__':main()
