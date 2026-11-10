#!/usr/bin/env python3
"""Reconstruct the retained generated reference-control qualification."""
from realworld_generated_runtime_v2 import ROOT,read
from realworld_generated_loader_v1 import sha
from validate_realworld_generated_controls_v2 import validate
from mixed_interface.repetition import require
MANIFEST=ROOT/'manifests/realworld-generated-runtime-integration.json'

def verify(manifest=None):
    manifest=read(MANIFEST) if manifest is None else manifest
    root=ROOT/manifest['archive_root']
    require(root.resolve()==(ROOT/'results/realworld-generated-controls-ci-20261110').resolve(),'Archive root differs')
    require({str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file()}==manifest['files_sha256'],'Archive inventory or bytes differ')
    value=validate(root/'realworld-generated-v2')
    require(value==manifest['verification'],'Reconstructed runtime evidence differs')
    require(value['source_commit']==manifest['source_commit']=='eb2b6656ad1e8e4ce3be7d0fa2b1811ddad6272c','Source commit differs')
    require(manifest['application_run']==42729694261 and manifest['unit_run']==42729529686,'Run identity differs')
    require(manifest['new_primary_samples']==0 and manifest['primary_freeze_complete'] is False,'Qualification promoted')
    return value

if __name__=='__main__':
    value=verify();print('Verified two generated reference pairs, four branches; primary freeze remains open')
