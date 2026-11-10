#!/usr/bin/env python3
"""Reconstruct the retained generated mutation qualification."""
from realworld_generated_execution_v3 import ROOT,read
from realworld_generated_loader_v1 import sha
from validate_realworld_generated_mutations_v3 import validate
from mixed_interface.repetition import require
MANIFEST=ROOT/'manifests/realworld-generated-mutations-integration.json'

def verify(manifest=None):
    manifest=read(MANIFEST) if manifest is None else manifest
    root=ROOT/manifest['archive_root']
    require(root.resolve()==(ROOT/'results/realworld-generated-mutations-ci-20261110').resolve(),'Archive root differs')
    require({str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file()}==manifest['files_sha256'],'Archive inventory or bytes differ')
    value=validate(root/'realworld-generated-v3')
    require(value==manifest['verification'],'Reconstructed runtime evidence differs')
    require(value['source_commit']==manifest['source_commit']=='9cc573fbb1372b37068b3e905bc38e30f4dcdfc9','Source commit differs')
    require(manifest['application_run']==42761024624 and manifest['unit_run']==42760772921,'Run identity differs')
    require(manifest['new_primary_samples']==0 and manifest['primary_freeze_complete'] is False,'Qualification promoted')
    return value

if __name__=='__main__':
    value=verify();print('Verified retained generated mutation attempt; primary freeze remains open')
