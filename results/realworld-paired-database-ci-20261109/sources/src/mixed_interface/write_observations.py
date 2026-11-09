"""Prospective write measurements; no dispatch or defect-adjudication decisions.

Callers must qualify actor, fixture, request identity, snapshot timing and evidence
before use. A projection is a declared committed-state view, not an API response.
"""
from copy import deepcopy


def require(condition, message):
    if not condition:
        raise ValueError(message)


def snapshot(value):
    require(isinstance(value, dict), 'Snapshot must be an object')
    require(value.get('state') in ('observed', 'unreadable', 'missing', 'not_planned'),
            'Unknown snapshot state')
    if value['state'] == 'observed':
        require(set(value) == {'state', 'projection'} and isinstance(value['projection'], dict)
                and bool(value['projection']), 'Observed snapshot needs a nonempty projection')
    else:
        require(set(value) == {'state'}, 'Unavailable snapshot cannot contain a projection')
    return value


def measure(status, before, immediate, restart, intended_patch, readbacks):
    """Describe qualified observations without inferring rollback from HTTP status.

    readbacks is a nonempty endpoint map, with explicit missing/not_planned entries.
    HTTP success is transport evidence only; continuation requires its own adapter.
    """
    require(status is None or (type(status) is int and 100 <= status <= 599),
            'Invalid HTTP status')
    before, immediate, restart = map(snapshot, (before, immediate, restart))
    require(isinstance(intended_patch, dict) and bool(intended_patch), 'Intended patch required')
    state = 'unknown'
    target_observed = None
    if before['state'] == immediate['state'] == 'observed':
        b, a = before['projection'], immediate['projection']
        require(set(b) == set(a) and set(intended_patch) <= set(b), 'Projection scope differs')
        target_observed = all(a[k] == v for k, v in intended_patch.items())
        state = ('unchanged' if a == b else 'requested_patch_observed'
                 if a == {**b, **intended_patch} else 'other_change')
    survives = None
    if immediate['state'] == restart['state'] == 'observed':
        require(set(immediate['projection']) == set(restart['projection']), 'Restart scope differs')
        survives = immediate['projection'] == restart['projection']
    require(isinstance(readbacks, dict) and bool(readbacks), 'Explicit readback plan required')
    for endpoint, observation in readbacks.items():
        require(isinstance(endpoint, str) and bool(endpoint), 'Readback identity required')
        require(isinstance(observation, dict), 'Readback must be an object')
        snapshot_state = observation.get('state')
        require(snapshot_state in ('response', 'unreadable', 'missing', 'not_planned'),
                'Unknown readback state')
        if snapshot_state == 'response':
            code = observation.get('status')
            require(set(observation) == {'state', 'status'} and type(code) is int
                    and 100 <= code <= 599, 'Invalid readback response')
        else:
            require(set(observation) == {'state'}, 'Unavailable readback contains response')
    return deepcopy({
        'schema_version': 1,
        'http': {'state': 'missing' if status is None else 'response', 'status': status},
        'persistence': {'before': before, 'immediate': immediate, 'restart': restart,
                        'selected_change': state, 'intended_values_observed': target_observed,
                        'immediate_projection_survives_restart': survives},
        'readbacks': readbacks,
        'continuation': {'state': 'not_measured'},
    })
