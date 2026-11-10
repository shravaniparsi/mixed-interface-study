"""Separate, exposed measurement-correction cohort; never replaces the primary run."""
from primary_preflight_v1 import ROOT,read,sha,sources,environment
from mixed_interface.primary_batches_v1 import followups
from mixed_interface.repetition import require
PREPARATION=ROOT/'manifests/quartz-form-correction-preparation-v1.json'
FREEZE=ROOT/'manifests/quartz-form-correction-freeze-v1.json'

def units(mode):
    value=read(PREPARATION);sources(value)
    if mode=='smoke':return value['smoke_units']
    freeze=read(FREEZE)
    require(freeze['primary_freeze_complete'] and freeze['preparation_sha256']==sha(PREPARATION),'Correction qualification absent or differs')
    if mode=='initial':return value['plan']['initial_batches']
    require(mode in ('repeat2','repeat3'),'Unknown correction phase')
    selection=read(ROOT/f'manifests/quartz-correction-execution-{mode}-v1.json')
    require(selection['preparation_sha256']==sha(PREPARATION) and selection['freeze_sha256']==sha(FREEZE),'Correction follow-up context differs')
    expected=followups(value['plan'],selection['initial'],int(mode[-1]),selection.get('previous'))
    require(selection['schedule']==expected,'Correction follow-up selection differs')
    return expected['batches']
