#!/usr/bin/env python3
"""Reopen the retained article creation snapshots and check all recorded measurements."""
from pathlib import Path
from realworld_terminal_campaign import ROOT,read,sha
from validate_realworld_article_database_diagnostic import validate
from mixed_interface.repetition import require
MANIFEST=ROOT/'manifests/realworld-article-database-integration.json'


def verify(manifest=None):
    manifest=read(MANIFEST) if manifest is None else manifest
    root=ROOT/manifest['archive_root']
    require(root.resolve()==(ROOT/'results/realworld-article-database-ci-20261109').resolve(),'Archive root differs')
    require({str(p.relative_to(root)):sha(p) for p in root.rglob('*') if p.is_file()}==manifest['files_sha256'],
            'Archive file inventory or hashes differ')
    value=validate(root/'article-database-diagnostic')
    require(value==manifest['verification'],'Reconstructed database measurements differ')
    require(value['source_commit']==manifest['source_commit']=='e26c23486e7436eb1cb01f23974248f920db80bd','Source commit differs')
    require(manifest['application_run']==42704951705 and manifest['unit_run']==42704839709,'Run identity differs')
    require(manifest['primary_freeze_complete'] is False and manifest['new_primary_samples']==0,'Diagnostic promoted')
    require(len(list(root.rglob('*.sqlite3')))==13,'Snapshot inventory differs')
    require([c['prefix_status'] for c in value['cases']]==[201,201,500],'Observed HTTP statuses differ')
    require(all(c['requested_article_fields_observed'] and c['post_response_selected_state_survives_restart']
                and c['user_preserved'] and c['fixture_articles_preserved'] for c in value['cases']),
            'Observed committed-state measurements differ')
    return value


if __name__=='__main__':
    result=verify();print('Verified three exposed article database diagnostics and thirteen backups; no primary promotion')
