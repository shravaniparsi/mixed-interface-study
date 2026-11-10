#!/usr/bin/env python3
"""Verify the dated freeze against unchanged preparation and complete smoke evidence."""
import datetime
from primary_preflight_v1 import ROOT,PREPARATION,FREEZE,read,sha,sources,units
from verify_primary_collection_v1 import verify
from mixed_interface.repetition import require

def verify_freeze():
    f=read(FREEZE);p=read(PREPARATION);sources(p)
    require(f['primary_freeze_complete'] is True and f['replacement_or_resume_allowed'] is False,'Freeze flags differ')
    require(f['preparation_sha256']==sha(PREPARATION) and f['plan_sha256']==p['plan']['plan_sha256'],'Frozen preparation differs')
    m=ROOT/f['smoke_manifest'];require(sha(m)==f['smoke_manifest_sha256'],'Smoke manifest differs');v=verify(m)
    require(v['all_units_qualified'] and all(r['status']=='completed_observations' and len(r['observations'])==2 and all(o['terminal']['kind']=='clean_observation' for o in r['observations']) for r in v['records'].values()),'Smoke not clean')
    require(read(m)['source_commit']==f['qualified_source_commit'] and read(m)['application_run']==f['smoke_application_run'] and read(m)['unit_run']==f['source_ci_run'],'Qualification identity differs')
    require(f['selected_entries']==[u['target_pair_id'] for u in p['plan']['initial_batches']] and f['initial_units']==75 and f['potential_followup_units']==146,'Frozen inventory differs')
    require(f['environment_acceptance']==p['environment'],'Frozen environment differs')
    require(datetime.datetime.fromisoformat(f['frozen_at_utc']).utcoffset()==datetime.timedelta(0),'Freeze timestamp not UTC')
    require(len(units('initial'))==75,'Frozen dispatch inventory differs')
    return {'verified':True,'primary_freeze_complete':True,'initial_units':75,'frozen_at_utc':f['frozen_at_utc']}
if __name__=='__main__':print(verify_freeze())
