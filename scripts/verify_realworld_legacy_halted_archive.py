#!/usr/bin/env python3
"""Verify the retained v8 stop without converting it into a complete campaign."""
from pathlib import Path
from realworld_terminal_campaign import ROOT,read,sha
from validate_realworld_legacy_campaign_v8 import validate
from mixed_interface.repetition import require
MANIFEST=ROOT/'manifests/realworld-legacy-halted-integration.json'


def verify(manifest=None):
    manifest=read(MANIFEST) if manifest is None else manifest
    root=ROOT/manifest['archive_root']
    require(root.resolve()==(ROOT/'results/realworld-legacy-halted-ci-20261109').resolve(),'Archive root differs')
    actual={str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file()}
    require(actual==manifest['files_sha256'],'Retained files differ')
    result=validate(root/'realworld-legacy-v8')
    require(result==manifest['verification'],'Reconstructed verification differs')
    require(result['source_commit']==manifest['source_commit']=='8bb1351bb7d42d748f7c72fe015f691c11b93233','Source commit differs')
    require(manifest['application_run']==42702655033 and manifest['unit_run']==42702497159,'Run identity differs')
    require(manifest['primary_freeze_complete'] is False and manifest['new_primary_samples']==0,'Primary promotion')
    require(result['status']=='halted_terminal_outcome' and result['completed_jobs']==4 and result['branches']==8,'Halted scope differs')
    require([d['kind'] for d in result['decisions']]==['clean_observation','clean_observation','unresolved_policy','missing_evidence'],'Observed terminals differ')
    require(manifest['unstarted_jobs']==['legacy-004','legacy-005','legacy-006','legacy-007','legacy-008'],'Unstarted inventory differs')
    return result


if __name__=='__main__':
    result=verify();print('Verified halted v8 archive:',result['completed_jobs'],'jobs,',result['branches'],'branches; five jobs remain unstarted')
