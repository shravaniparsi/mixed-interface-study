"""Registered-root restart comparison; does not qualify Docker state or actor.

Inputs are private original-driver snapshots and verified runtime observations.
Raw differences remain returned; only source-grounded startup rewrites admitted.
"""
import hashlib
import math
from pathlib import PurePosixPath
from nginx_ordinary_filesystem_delta_v1 import flatten, DB, SIDECARS

PEER = '/etc/nginx/conf.d/production.conf'
PID = '/run/nginx/nginx.pid'


def compare_restart_state(warm, restored, warm_database, restored_database, startup_window):
    if warm_database != restored_database:
        raise ValueError('Complete original-driver restored database differs')
    start,end = startup_window['start_epoch_seconds'],startup_window['end_epoch_seconds']
    if startup_window.get('timezone') != 'UTC' or not all(type(x) in (int,float) and math.isfinite(x) for x in (start,end)) or not 0 <= end-start <= 120:
        raise ValueError('Invalid startup window')
    low,high = math.floor(start*1e9),math.ceil(end*1e9)
    a,b=flatten(warm),flatten(restored)
    for observed in (warm,restored):
        if observed.get('status') != 'runtime_observation_only_not_atomic_or_qualified':
            raise ValueError('Original runtime observation required')
    if warm['environment'] != restored['environment']:
        raise ValueError('Runtime environment differs')
    for name in ('backend','master'):
        def stable(process):
            return {k:v for k,v in process.items() if k not in ('pid','startTicks')}
        if stable(warm[name]) != stable(restored[name]):
            raise ValueError('Original process executable/arguments/ownership differ')
    for observed,inventory in ((warm,a),(restored,b)):
        peer=observed['peer']
        if peer.get('backendSecretMatches') is not True or peer.get('adminPort') != 81 or peer.get('disableIpv6') is not True or peer.get('backendPid') != observed['backend']['pid']:
            raise ValueError('Peer proof does not identify the observed backend')
        if inventory.get(PEER,{}).get('sha256') != peer['configurationSha256']:
            raise ValueError('Peer configuration proof is not bound to inventory')
        pid=observed['master']['pid']
        if type(pid) is not int or pid<=0:
            raise ValueError('Invalid observed master PID')
        raw=(str(pid)+'\n').encode()
        if inventory.get(PID,{}).get('sha256') != hashlib.sha256(raw).hexdigest() or inventory[PID]['bytes']!=len(raw):
            raise ValueError('PID file does not identify observed master')
    if any(warm['peer'][k] != restored['peer'][k] for k in ('templateSha256','normalizedConfigurationSha256')):
        raise ValueError('Original peer template or normalized configuration differs')
    configs={p for p,r in a.items() if r['kind']=='file' and p.endswith('.conf') and
             (p.startswith('/etc/nginx/conf.d/') or p.startswith('/data/nginx/'))}
    # Original prepare/50-ipv6 replaces these files even when bytes are unchanged.
    parent_dirs={str(PurePosixPath(p).parent) for p in configs}
    rotation={p for p,r in a.items() if p.startswith('/var/lib/logrotate/') and r['kind']=='file'}
    mtime_only=configs | parent_dirs | rotation | {'/var/lib/logrotate','/var/log/nginx/error.log','/run/nginx','/data'}
    if DB not in a or DB not in b or a[DB]['kind']!='file' or b[DB]['kind']!='file':
        raise ValueError('Original SQLite file missing')
    changes=[]
    for path in sorted(a.keys()|b.keys()):
        old,new=a.get(path),b.get(path)
        if old==new: continue
        changes.append({'path':path,'warm':old,'restored':new})
        if path in SIDECARS:
            for row in (old,new):
                if row is not None and (row['kind']!='file' or any(row[k]!=a[DB][k] for k in ('uid','gid','mode'))):
                    raise ValueError('Unexpected SQLite sidecar identity')
            continue
        if old is None or new is None:
            raise ValueError('Unregistered startup path added/removed: '+path)
        mutable={'mtimeNs'} if path in mtime_only else set()
        if path in (DB,PID,PEER): mutable |= {'mtimeNs','sha256','bytes'}
        if {k:v for k,v in old.items() if k not in mutable} != {k:v for k,v in new.items() if k not in mutable}:
            raise ValueError('Unexplained startup state change: '+path)
        if path in (DB,PID,PEER) and new['kind']!='file':
            raise ValueError('Unexpected generated file kind')
        if path==PEER and old['bytes']!=new['bytes']:
            raise ValueError('Peer secret substitution changed length')
        if old['mtimeNs'] != new['mtimeNs']:
            raw=new['mtimeNs']
            if not isinstance(raw,str) or str(int(raw))!=raw or not low<=int(raw)<=high:
                raise ValueError('Rewrite timestamp outside startup interval: '+path)
    return {'status':'registered_root_restart_comparison_only_actor_and_docker_state_unqualified',
            'changes':changes,'database_logically_identical':True}
