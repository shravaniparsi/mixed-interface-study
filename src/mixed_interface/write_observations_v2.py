"""Development-only persistence measurements with type-sensitive JSON equality.

Version 1 remains frozen for historical records. This version does not qualify
UI continuation, actors, snapshots or causality; adapters must establish those.
"""
from .write_observations import measure as measure_v1
from .write_frame import equal


def measure(status, before, immediate, restart, intended_patch, readbacks):
    # Preserve v1 shape validation and detached evidence copies.
    result = measure_v1(status, before, immediate, restart, intended_patch, readbacks)
    persistence = result['persistence']
    if before['state'] == immediate['state'] == 'observed':
        b, a = before['projection'], immediate['projection']
        persistence['intended_values_observed'] = all(
            equal(a[k], value) for k, value in intended_patch.items())
        persistence['selected_change'] = (
            'unchanged' if equal(a, b) else
            'requested_patch_observed' if equal(a, {**b, **intended_patch}) else
            'other_change')
    if immediate['state'] == restart['state'] == 'observed':
        persistence['immediate_projection_survives_restart'] = equal(
            immediate['projection'], restart['projection'])
    result['schema_version'] = 2
    return result
