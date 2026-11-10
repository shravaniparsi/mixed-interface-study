#!/usr/bin/env python3
"""Qualify the corrected reader using fresh empty and nonempty live controls."""
import argparse
from datetime import datetime,timezone
from pathlib import Path
from quartz_public_qualification_preflight_v1 import ROOT,PREPARATION,FREEZE,read,sha,sources
from verify_quartz_public_qualification_collection_v1 import verify
from mixed_interface.common_execution_v1 import write
from mixed_interface.repetition import require

def freeze(manifest):
    require(not FREEZE.exists(),'Correction qualification already frozen')
    phase=verify(manifest);require(phase['mode']=='smoke' and phase['all_units_qualified'],'Correction smoke failed')
    observations=[o for r in phase['records'].values() for o in r['observations']]
    require(len(observations)==4 and all(o['terminal']['kind']=='clean_observation' for o in observations),'Four clean qualification pairs required')
    root=ROOT/read(manifest)['archive_root'];forms=[]
    for path in root.glob('*/quartz-public-qualification-unit-v1/*nonempty_string*/runtime/run/*/result.json'):
        for form in read(path)['ui_forms']:
            require(form['typed_entries'] and form['values']['jobDataMap']=={'sample':'ordinary value'},'Nonempty live form was not measured correctly')
            forms.append({'raw_result':str(path.relative_to(ROOT)),'sha256':sha(path),'label':form['label']})
    from collections import Counter
    require(Counter(f['label'] for f in forms)=={'consumer_loaded':2,'consumer_before_submit':2,'fresh_final_native_read':4},'Nonempty form stages differ')
    require(len(forms)==8,'Nonempty form coverage differs')
    sources(read(PREPARATION))
    value={'kind':'exposed_quartz_form_correction_qualification_v1','frozen_at_utc':datetime.now(timezone.utc).isoformat(),
        'preparation_sha256':sha(PREPARATION),'qualification_manifest':str(manifest.relative_to(ROOT)),
        'qualification_manifest_sha256':sha(manifest),'nonempty_form_evidence':forms,
        'primary_freeze_complete':True,'scope':'Separate exposed correction cohort; not a replacement or untouched evaluation'}
    write(FREEZE,value);return value

if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('manifest',type=Path);args=p.parse_args()
    print(freeze(args.manifest.resolve())['frozen_at_utc'])
