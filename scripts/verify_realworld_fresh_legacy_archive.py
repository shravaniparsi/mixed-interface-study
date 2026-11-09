#!/usr/bin/env python3
"""Reconstruct the fresh v9 sweep while retaining its incomparable observations."""
from pathlib import Path
from realworld_terminal_campaign import ROOT,read,sha
from validate_realworld_legacy_campaign_v9 import validate
from mixed_interface.repetition import require
MANIFEST=ROOT/'manifests/realworld-fresh-legacy-integration.json'


def verify(manifest=None):
    manifest=read(MANIFEST) if manifest is None else manifest
    root=ROOT/manifest['archive_root']
    require(root.resolve()==(ROOT/'results/realworld-fresh-legacy-ci-20261109').resolve(),'Archive root differs')
    require({str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file()}==manifest['files_sha256'],
            'Archive file inventory or hashes differ')
    value=validate(root/'realworld-legacy-v9')
    require(value==manifest['verification'],'Reconstructed verification differs')
    require(value['source_commit']==manifest['source_commit']=='bd2f36c447bf95c1416335f3fa192b4a98fe174a','Source commit differs')
    require(manifest['application_run']==42708069641 and manifest['unit_run']==42707887979,'Run identity differs')
    require(manifest['prior_v8_attempt_resumed'] is False and manifest['primary_freeze_complete'] is False
            and manifest['new_primary_samples']==0,'Attempt or study scope promoted')
    require(value['status']=='completed_bounded_diagnostic' and value['completed_jobs']==7 and value['branches']==12,'Observed scope differs')
    require([d['kind'] for d in value['decisions']]==['clean_observation']*2+['incomparable_observation']*3+['clean_observation']*2,
            'Observed terminal classifications differ')
    return value


if __name__=='__main__':
    value=verify();print('Verified fresh v9 sweep: seven jobs, twelve branches; three pairs remain incomparable')
