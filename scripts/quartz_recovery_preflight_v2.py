"""Explicit additional collection for provider-rejected, never-started cases."""
from primary_preflight_v1 import ROOT,read,sha,sources,environment
from mixed_interface.primary_batches_v1 import followups
from mixed_interface.repetition import require
PREPARATION=ROOT/'manifests/quartz-recovery-preparation-v2.json'
FREEZE=ROOT/'manifests/quartz-recovery-freeze-v2.json'

def units(mode):
    value=read(PREPARATION);sources(value)
    require(mode in ('initial','repeat2','repeat3'),'Unknown recovery phase')
    freeze=read(FREEZE)
    require(freeze['primary_freeze_complete'] and freeze['preparation_sha256']==sha(PREPARATION),'Recovery release absent or differs')
    require(freeze['qualification_sha256']==sha(ROOT/'manifests/quartz-public-qualification-freeze-v1.json'),'Reader qualification differs')
    from verify_quartz_recovery_release_v2 import verify
    verify()
    if mode=='initial':return value['plan']['initial_batches']
    selection=read(ROOT/f'manifests/quartz-recovery-execution-{mode}-v2.json')
    require(selection['preparation_sha256']==sha(PREPARATION) and selection['freeze_sha256']==sha(FREEZE),'Recovery follow-up context differs')
    expected=followups(value['plan'],selection['initial'],int(mode[-1]),selection.get('previous'))
    require(selection['schedule']==expected,'Recovery follow-up selection differs')
    return expected['batches']
