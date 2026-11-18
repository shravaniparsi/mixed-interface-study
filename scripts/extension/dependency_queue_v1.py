"""Offline prospective dependency queue. No network or source execution.

One queue represents one fixed repository/revision. Roots must be complete before
scheduling. Complete a batch and record all discovered edges before sealing it;
only then can a later breadth-first batch be scheduled. Completeness of human
source review is an external obligation, not something this queue can prove.
"""
from copy import deepcopy
from datetime import datetime, timezone
import re


def _sha(value):
    if not isinstance(value, str) or not re.fullmatch(r'[0-9a-f]{40}', value):
        raise ValueError('Expected exact Git SHA1')


def _entry(entry):
    if set(entry) != {'path', 'blob', 'reason'}:
        raise ValueError('Expected path, blob, reason')
    path = entry['path']
    if not isinstance(path, str) or not path or path.startswith('/') or any(
        p in ('', '.', '..') for p in path.split('/')
    ):
        raise ValueError('Invalid repository-relative path')
    _sha(entry['blob'])
    if not isinstance(entry['reason'], str) or not entry['reason'].strip():
        raise ValueError('Discovery reason required')


def new_queue(repository, revision, roots, cap):
    _sha(revision)
    if not repository or type(cap) is not int or cap < 1 or not roots:
        raise ValueError('Repository, roots and positive fixed cap required')
    q = dict(repository=repository, revision=revision, cap=cap,
             nodes={}, batches=[], events=[])
    for entry in roots:
        _add(q, entry, None)
    return q


def _add(q, entry, parent):
    _entry(entry)
    depth = 0 if parent is None else q['nodes'][parent]['depth'] + 1
    existing = q['nodes'].get(entry['path'])
    if existing and existing['blob'] != entry['blob']:
        raise ValueError('Conflicting blob at fixed revision')
    if not existing:
        q['nodes'][entry['path']] = dict(blob=entry['blob'], depth=depth,
                                       status='pending', edges=[])
    node = q['nodes'][entry['path']]
    if depth < node['depth']:
        raise ValueError('Late shorter path: traversal record is inconsistent')
    edge = dict(parent=parent, reason=entry['reason'])
    if edge not in node['edges']:
        node['edges'].append(edge)


def transition(state, action, **args):
    """Return a new state; failed actions never mutate the caller's state."""
    q = deepcopy(state)
    open_batch = next((b for b in q['batches'] if not b['sealed']), None)
    if action == 'schedule':
        if open_batch:
            raise ValueError('Finish and seal current discovery batch first')
        limit = args['limit']
        if type(limit) is not int or limit < 1:
            raise ValueError('Positive batch size required')
        used = sum(len(b['paths']) for b in q['batches'])
        pending = [p for p, n in q['nodes'].items() if n['status'] == 'pending']
        if used >= q['cap'] or not pending:
            raise ValueError('No remaining collection allowance or pending nodes')
        depth = min(q['nodes'][p]['depth'] for p in pending)
        paths = sorted((p for p in pending if q['nodes'][p]['depth'] == depth),
                       key=lambda p: p.encode('utf-8'))[:min(limit, q['cap'] - used)]
        for p in paths:
            q['nodes'][p]['status'] = 'scheduled'
        q['batches'].append(dict(paths=paths, depth=depth, freeze=None, sealed=False))
    elif action == 'publish':
        _sha(args['freeze'])
        if not open_batch or open_batch['freeze'] is not None:
            raise ValueError('Exactly one freeze required for open batch')
        open_batch['freeze'] = args['freeze']
    elif action == 'observe':
        p, outcome = args['path'], args['outcome']
        if not open_batch or not open_batch['freeze'] or p not in open_batch['paths']:
            raise ValueError('Observation requires a frozen scheduled path')
        if q['nodes'][p]['status'] != 'scheduled' or outcome not in ('collected', 'unavailable'):
            raise ValueError('No repeat observations or invalid outcomes')
        if outcome == 'collected' and not re.fullmatch(r'[0-9a-f]{64}', args.get('sha256', '')):
            raise ValueError('Collected content hash required')
        q['nodes'][p].update(status=outcome, evidence=deepcopy(args))
    elif action == 'discover':
        parent = args['parent']
        if not open_batch or parent not in open_batch['paths'] or q['nodes'][parent]['status'] != 'collected':
            raise ValueError('Discover only from collected parents in current batch')
        for entry in args['entries']:
            _add(q, entry, parent)
    elif action == 'seal':
        if not open_batch or any(q['nodes'][p]['status'] == 'scheduled' for p in open_batch['paths']):
            raise ValueError('All observations must be terminal before sealing')
        if args.get('discovery_complete') is not True:
            raise ValueError('Explicit discovery completeness attestation required')
        open_batch['sealed'] = True
    else:
        raise ValueError('Unknown action')
    q['events'].append(dict(action=action, arguments=deepcopy(args),
                            recorded_at=datetime.now(timezone.utc).isoformat()))
    return q
