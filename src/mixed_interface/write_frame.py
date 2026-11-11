"""Top-level state-frame baseline for explicit partial-edit contracts.

This is a baseline, not an inferred contract. Callers supply intended state
assignments and justified derived-field exceptions independently of observations.
"""
import json


def equal(left, right):
    """Compare JSON values without conflating booleans with numbers."""
    return json.dumps(left, sort_keys=True, allow_nan=False) == json.dumps(
        right, sort_keys=True, allow_nan=False
    )


def evaluate(before, after, assignments, derived=()):
    if not all(isinstance(x, dict) for x in (before, after, assignments)):
        raise TypeError('states and assignments must be objects')
    derived = set(derived)
    if derived.intersection(assignments):
        raise ValueError('requested assignments cannot also be derived exceptions')
    changed = sorted(k for k in before.keys() | after.keys()
                     if k not in before or k not in after or not equal(before[k], after[k]))
    failed = sorted(k for k, value in assignments.items()
                    if k not in after or not equal(value, after[k]))
    return {
        'changed_fields': changed,
        'failed_assignments': failed,
        'frame_violations': sorted(set(changed) - set(assignments) - derived),
    }
