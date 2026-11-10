#!/usr/bin/env python3
"""Independently verify the first hosted common-executor qualification archive."""
from petclinic_timed_jobs_v4 import ROOT,read,sha
from validate_common_generated_v1 import validate
from mixed_interface.repetition import require
MANIFEST=ROOT/'manifests/common-generated-runtime-v1.json'

def verify(manifest=None):
    manifest=read(MANIFEST) if manifest is None else manifest;root=ROOT/manifest['archive_root']
    require(root.resolve()==(ROOT/'results/common-generated-ci-42775240013').resolve(),'Archive root differs')
    require({str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file()}==manifest['files_sha256'],'Archive inventory or bytes differ')
    value=validate(root/'common-generated-v1')
    require(value==manifest['verification'],'Reconstructed evidence differs')
    require(value['source_commit']==manifest['source_commit']=='3ad77e2cabad9e4c896026a5cf9aa9cd7151c689','Source commit differs')
    require(manifest['application_run']==42775240013 and manifest['unit_run']==42775120705 and value['run_identity']=='42775240013:1','Run identity differs')
    require(manifest['new_primary_samples']==0 and manifest['primary_freeze_complete'] is False,'Qualification promoted')
    return value

if __name__=='__main__':
    v=verify();print('Verified common executor archive:',v['status'])
