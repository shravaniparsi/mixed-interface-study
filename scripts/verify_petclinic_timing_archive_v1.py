#!/usr/bin/env python3
"""Independently reconstruct the retained PetClinic branch-cost qualification."""
from petclinic_timed_jobs_v4 import ROOT,read,sha
from validate_petclinic_timing_qualification_v1 import validate
from mixed_interface.repetition import require
MANIFEST=ROOT/'manifests/petclinic-timing-runtime-v1.json'

def verify(manifest=None):
    manifest=read(MANIFEST) if manifest is None else manifest;root=ROOT/manifest['archive_root']
    require(root.resolve()==(ROOT/'results/petclinic-timing-ci-20261110').resolve(),'Archive root differs')
    require({str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file()}==manifest['files_sha256'],'Archive inventory or bytes differ')
    value=validate(root/'petclinic-timing-v1')
    require(value==manifest['verification'],'Reconstructed evidence differs')
    require(value['source_commit']==manifest['source_commit']=='34a7e65e8366cfd5440853ed2479d6ef537aa750','Source commit differs')
    require(manifest['application_run']==42766924552 and manifest['unit_run']==42766769615,'Run identity differs')
    require(manifest['new_primary_samples']==0 and manifest['primary_freeze_complete'] is False,'Qualification promoted')
    return value

if __name__=='__main__':
    v=verify();print('Verified PetClinic timing archive:',v['status'])
