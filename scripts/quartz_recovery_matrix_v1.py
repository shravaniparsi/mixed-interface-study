#!/usr/bin/env python3
"""Emit only the exact authorized frozen phase or exposed smoke units."""
import argparse,json
from quartz_recovery_preflight_v1 import units
p=argparse.ArgumentParser();p.add_argument('--mode',required=True);p.add_argument('--batch',default='all');a=p.parse_args()
selected=units(a.mode)
if a.batch!='all':
    selected=[u for u in selected if u['batch_id']==a.batch]
    if len(selected)!=1:raise ValueError('Unknown batch')
print(json.dumps({'include':[{'batch':u['batch_id'],'app':u['application'],'node':'24.22.2' if u['application']=='petclinic' else '20.20.2',
                            'java':'17.0.2+8' if u['application']=='petclinic' else '21.0.13+9'} for u in selected]}))
