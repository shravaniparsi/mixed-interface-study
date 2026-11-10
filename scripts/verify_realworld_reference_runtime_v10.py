#!/usr/bin/env python3
"""Reconstruct the retained prospective reference-comparison qualification."""
from realworld_terminal_campaign import ROOT,read,sha
from validate_realworld_legacy_campaign_v10 import validate
from mixed_interface.repetition import require
MANIFEST=ROOT/'manifests/realworld-reference-runtime-v10.json'


def verify(manifest=None):
    manifest=read(MANIFEST) if manifest is None else manifest
    root=ROOT/manifest['archive_root']
    require(root.resolve()==(ROOT/'results/realworld-reference-runtime-ci-20261110').resolve(),'Archive root differs')
    require({str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file()}==manifest['files_sha256'],
            'Archive file inventory or hashes differ')
    value=validate(root/'realworld-legacy-v10')
    require(value==manifest['verification'],'Reconstructed verification differs')
    require(value['source_commit']==manifest['source_commit']=='dbd73458aa2945ec9de932deee73ec54f716fa2f','Source commit differs')
    require(manifest['application_run']==42764442019 and manifest['unit_run']==42764333787,'Run identity differs')
    require(manifest['prior_attempt_resumed'] is False and manifest['primary_freeze_complete'] is False
            and manifest['new_primary_samples']==0,'Attempt or study scope promoted')
    return value


if __name__=='__main__':
    value=verify();print('Verified reference-comparison runtime archive:',value['status'])
