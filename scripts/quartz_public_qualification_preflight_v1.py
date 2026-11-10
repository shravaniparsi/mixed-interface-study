"""Four control pairs qualify the public host; no research-case execution here."""
from primary_preflight_v1 import ROOT,read,sha,sources,environment
from mixed_interface.repetition import require
PREPARATION=ROOT/'manifests/quartz-public-qualification-preparation-v1.json'
FREEZE=ROOT/'manifests/quartz-public-qualification-freeze-v1.json'

def units(mode):
    require(mode=='smoke','Only public-host qualification is authorized')
    value=read(PREPARATION);sources(value)
    return value['smoke_units']
