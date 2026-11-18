#!/usr/bin/env python3
"""Verify actual disposable container/writer state for checkpoint orchestration.

No start/stop/pause or filesystem mutations are performed. Only an actual Docker
inspect response returned by inspect_container may establish runtime quiescence.
"""
import json
from pathlib import Path
import subprocess

LABEL = 'org.mixed-interface.study'
VALUE = 'nginx-qualification-v1'
DESTINATIONS = {'/data', '/etc/letsencrypt'}

def validate_inspection(info, mode, roots):
    if mode not in {'capture', 'restore'}: raise ValueError('Unknown checkpoint mode')
    if set(roots) != DESTINATIONS: raise ValueError('Exactly the two registered state mounts are required')
    if info.get('Config', {}).get('Labels', {}).get(LABEL) != VALUE:
        raise ValueError('Container is not the registered disposable study instance')
    if info.get('HostConfig', {}).get('RestartPolicy', {}).get('Name') not in {'', 'no'}:
        raise ValueError('Automatic container restart is not admitted')
    state = info.get('State', {})
    if state.get('Dead') or state.get('Restarting'): raise ValueError('Container lifecycle is unstable')
    if mode == 'capture':
        if state.get('Running') is not True or state.get('Paused') is not True:
            raise ValueError('Capture requires authoritatively paused live writers')
        if not isinstance(state.get('Pid'), int) or state['Pid'] <= 0:
            raise ValueError('Paused container process identity missing')
    elif state.get('Running') is not False or state.get('Paused') is not False or state.get('Pid') != 0:
        raise ValueError('Restore requires fully stopped writers')
    for destination, source in roots.items():
        source = Path(source).absolute()
        if source.resolve() != source: raise ValueError('Mount source must be canonical')
        matches = [m for m in info.get('Mounts', []) if m.get('Destination') == destination]
        if len(matches) != 1 or matches[0].get('Type') != 'bind' or matches[0].get('RW') is not True:
            raise ValueError('Registered writable bind mount missing or ambiguous')
        if Path(matches[0]['Source']).absolute() != source:
            raise ValueError('Container mount source differs from requested state root')
    paths = [Path(p).absolute() for p in roots.values()]
    if paths[0] == paths[1] or paths[0] in paths[1].parents or paths[1] in paths[0].parents:
        raise ValueError('State mounts overlap')
    if not info.get('Id') or not state.get('StartedAt'):
        raise ValueError('Container identity missing')
    return {'container_id': info['Id'], 'started_at': state['StartedAt'], 'pid': state['Pid'],
            'mode': mode, 'roots': {k: str(Path(v).absolute()) for k, v in roots.items()}}

def inspect_container(container, mode, roots):
    raw = subprocess.check_output(['docker', 'inspect', '--type', 'container', container], timeout=10)
    if len(raw) > 1024 * 1024: raise ValueError('Container metadata bound')
    rows = json.loads(raw)
    if len(rows) != 1: raise ValueError('Expected exactly one container')
    return validate_inspection(rows[0], mode, roots)

def verify_same_guard(before, after):
    if before != after: raise ValueError('Container lifecycle or mount identity changed during checkpoint')
