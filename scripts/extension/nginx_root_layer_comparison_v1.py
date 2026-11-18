"""Strict comparison of Docker-reported root-layer state outside mounted roots.

No blanket runtime/cache/configuration exclusions. Unexplained changes fail.
"""
import math
from pathlib import PurePosixPath
from nginx_ordinary_filesystem_delta_v1 import ROOTS
from nginx_root_layer_inventory_v1 import validate_paths

ACCOUNT_FILES={f'/etc/{name}{suffix}' for name in ('passwd','group','shadow','gshadow','subuid','subgid') for suffix in ('','-')}|{'/etc/.pwd.lock'}


def parse_diff(raw):
    if not isinstance(raw,bytes) or len(raw)>8*1024*1024:raise ValueError('Docker diff bound')
    entries={}
    for line in raw.decode('utf8').splitlines():
        if len(line)<4 or line[0] not in 'ACD' or line[1]!=' ':raise ValueError('Malformed Docker diff')
        path=line[2:]
        validate_paths([path])
        if path in entries:raise ValueError('Duplicate Docker diff path')
        entries[path]=line[0]
    return entries


def compare_root_layers(left,right,left_diff,right_diff,phase,window):
    if phase not in ('operation','restart'):raise ValueError('Unregistered comparison phase')
    start,end=window['start_epoch_seconds'],window['end_epoch_seconds']
    if window.get('timezone')!='UTC' or not all(type(x) in (int,float) and math.isfinite(x) for x in (start,end)) or not 0<=end-start<=120:
        raise ValueError('Invalid root-layer time window')
    before_diff,after_diff=parse_diff(left_diff),parse_diff(right_diff)
    if before_diff.keys()!=after_diff.keys():
        raise ValueError('Docker root-layer changed-path membership differs')
    def indexed(value,diff):
        if value.get('extended_attributes_absent') is not True:raise ValueError('Root-layer xattr coverage missing')
        rows={r['path']:r for r in value['rows']}
        if len(rows)!=len(value['rows']) or rows.keys()!=diff.keys():raise ValueError('Root-layer inventory coverage differs')
        return rows
    a,b=indexed(left,before_diff),indexed(right,after_diff)
    changes=[]
    for path in a:
        old,new=a[path],b[path]
        # These paths have separate complete inventory/operation/restart checks.
        covered=any(path==root or path.startswith(root+'/') for root in ROOTS)
        if covered:continue
        if before_diff[path]!=after_diff[path]:raise ValueError('Unexplained Docker layer change kind: '+path)
        if old==new:continue
        changes.append({'path':path,'before':old,'after':new})
        # Only original account/group startup commands justify these rewrites.
        mutable={'mtime_ns'} if phase=='restart' and path in ACCOUNT_FILES else set()
        # Ancestor directory timestamps may reflect the independently checked
        # startup file replacements. Their kind/mode/ownership remain exact.
        ancestors={str(parent) for child in ROOTS|ACCOUNT_FILES for parent in PurePosixPath(child).parents}
        if phase=='restart' and path in ancestors and old['kind']==new['kind']=='directory':mutable={'mtime_ns'}
        if {k:v for k,v in old.items() if k not in mutable}!={k:v for k,v in new.items() if k not in mutable}:
            raise ValueError('Unexplained root-layer state change: '+path)
        if old.get('mtime_ns')!=new.get('mtime_ns'):
            value=new.get('mtime_ns')
            if type(value) is not int or not math.floor(start*1e9)<=value<=math.ceil(end*1e9):
                raise ValueError('Root-layer timestamp outside startup: '+path)
    return {'status':'reported_root_layer_comparison_passed_separate_runtime_gates_required','changes':changes}
