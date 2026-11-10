#!/usr/bin/env python3
"""Retention check for the superseded smoke context; not renewed qualification."""
from pathlib import Path
from mixed_interface.common_execution_v1 import read,sha,inventory
from mixed_interface.repetition import require
ROOT=Path(__file__).resolve().parents[1]

def verify():
    m=read(ROOT/'manifests/primary-smoke-attempt1-v1.json');c=m['collection'];root=ROOT/m['archive_root']
    require(inventory(root)==c['files_sha256'],'Historical smoke bytes differ')
    require(c['preparation_sha256']==sha(ROOT/'manifests/primary-execution-preparation-attempt1.json'),'Original preparation differs')
    require(m['application_run']==42777715374 and m['source_commit']=='fabf3a499dad67d5863b972ad489c592083035e5' and c['run_identity']=='42777715374:1','Historical run differs')
    require(c['all_units_qualified'] is False and c['primary_freeze_complete'] is False,'Failed smoke promoted')
    failed=[k for k,v in c['verification'].items() if not v['qualified_observations']]
    require(failed==['smoke-petclinic_v4'],'Failure inventory differs')
    pc=root/'primary-smoke-smoke-petclinic_v4-42777715374-1'
    require('Hosted image differs' in (pc/'application-run.log').read_text() and not (pc/'primary-unit-v1').exists(),'Environment-rejected unit altered')
    require(read(pc/'runtime-versions.json')['runner']['ImageVersion']=='20261101.114.1','Rejected context differs')
    return {'retained':True,'qualified_under_revised_contract':False,'historical_source_commit':m['source_commit']}
if __name__=='__main__':print(verify())
