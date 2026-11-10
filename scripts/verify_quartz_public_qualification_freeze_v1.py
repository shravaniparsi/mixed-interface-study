#!/usr/bin/env python3
"""Reconstruct the separately qualified empty/nonempty form-reader controls."""
from datetime import datetime
from quartz_public_qualification_preflight_v1 import ROOT,PREPARATION,FREEZE,read,sha,sources
from verify_quartz_public_qualification_collection_v1 import verify
from mixed_interface.repetition import require

def check():
    frozen=read(FREEZE);manifest=ROOT/frozen['qualification_manifest']
    require(frozen['primary_freeze_complete'] and frozen['preparation_sha256']==sha(PREPARATION),'Correction freeze differs')
    require(sha(manifest)==frozen['qualification_manifest_sha256'],'Qualification manifest differs')
    datetime.fromisoformat(frozen['frozen_at_utc']);sources(read(PREPARATION))
    phase=verify(manifest);require(phase['mode']=='smoke' and phase['all_units_qualified'],'Qualification failed')
    obs=[o for r in phase['records'].values() for o in r['observations']]
    require(len(obs)==4 and all(o['terminal']['kind']=='clean_observation' for o in obs),'Four clean pairs required')
    forms=[]
    for path in (ROOT/read(manifest)['archive_root']).glob('*/quartz-public-qualification-unit-v1/*nonempty_string*/runtime/run/*/result.json'):
        for form in read(path)['ui_forms']:
            require(form['typed_entries'] and form['values']['jobDataMap']=={'sample':'ordinary value'},'Nonempty form differs')
            forms.append({'raw_result':str(path.relative_to(ROOT)),'sha256':sha(path),'label':form['label']})
    from collections import Counter
    require(Counter(f['label'] for f in forms)=={'consumer_loaded':2,'consumer_before_submit':2,'fresh_final_native_read':4},'Nonempty form stages differ')
    require(len(forms)==8 and sorted(forms,key=lambda v:(v['raw_result'],v['label']))==sorted(frozen['nonempty_form_evidence'],key=lambda v:(v['raw_result'],v['label'])),'Qualification form evidence differs')
    return {'qualification_pairs':4,'nonempty_forms_verified':8,'scope':frozen['scope']}

if __name__=='__main__':print(check())
