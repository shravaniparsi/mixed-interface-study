"""Evaluate explicitly supplied conditional rules. Does not extract or certify them.

No application writes, model calls, inferred defaults or dynamic code execution.
"""
import json
import math

MISSING = object()
UNRESOLVED_PATH = object()


def scalar_equal(left, right):
    if isinstance(left, bool) != isinstance(right, bool):
        return False
    return left == right


def read_path(document, path):
    if not isinstance(path, list) or any(not isinstance(key, str) for key in path):
        raise ValueError('Mappings require an explicit list of object keys')
    value = document
    for key in path:
        if not isinstance(value, dict):
            return UNRESOLVED_PATH
        if key not in value:
            return MISSING
        value = value[key]
    return value


def outcome(verdict, reason, applicable=None):
    return dict(verdict=verdict, reason=reason, applicable=applicable)


def evaluate(rule, observation):
    """Return an explicit verdict; unexpected/malformed instructions are code errors."""
    try:
        return _evaluate(rule, observation)
    except (KeyError, TypeError, ValueError, OverflowError) as error:
        return outcome('code_error', f'{type(error).__name__}: {error}')


def _evaluate(rule, observation):
    if not rule['rule_id'] or not rule['source_evidence']:
        raise ValueError('Rule identity and source evidence are mandatory')
    if rule['conflicting_evidence'] is not False:
        return outcome('unknown', 'unresolved_source_conflict')
    mapping = rule['mapping']
    if mapping['status'] != 'known' or not mapping['evidence']:
        return outcome('unknown', 'mapping_not_established')
    scope = rule['scope']
    if not scope or any(k not in scope for k in ('revision', 'operation', 'actor', 'lifecycle')):
        raise ValueError('Explicit revision/operation/actor/lifecycle scope required')
    context = observation['context']
    for key, expected in scope.items():
        if key not in context:
            return outcome('unknown', 'missing_context:' + key)
        if not scalar_equal(context[key], expected):
            return outcome('unknown', 'outside_scope:' + key, False)
    point = rule['observation_point']
    if observation['point'] != point:
        return outcome('unknown', 'wrong_observation_point')
    if observation['complete'] is not True:
        return outcome('unknown', 'incomplete_observation')
    # Guards are explicit equals tests, with AND semantics. Missing guard is unknown.
    document = observation['document']
    for guard in rule['guards']:
        actual = read_path(document, guard['path'])
        if actual is MISSING or actual is UNRESOLVED_PATH:
            return outcome('unknown', 'missing_guard_value')
        if not scalar_equal(actual, guard['equals']):
            return outcome('unknown', 'guard_false', False)
    value = read_path(document, mapping['path'])
    if value is UNRESOLVED_PATH:
        return outcome('unknown', 'mapping_container_mismatch')
    transform = mapping['transform']
    if transform not in {'identity', 'json_string_decode'}:
        return outcome('unknown', 'unsupported_transformation')
    if transform == 'json_string_decode' and value is not MISSING and value is not None:
        if not isinstance(value, str):
            return outcome('unknown', 'transformation_domain_mismatch')
        try:
            value = json.loads(value)
        except (ValueError, TypeError):
            return outcome('unknown', 'undecodable_mapped_value')
    special = 'missing' if value is MISSING else 'null' if value is None else 'empty' if value == '' else None
    if special:
        policy = rule['value_policy'][special]
        if policy == 'allow':
            return outcome('satisfied', special + '_explicitly_allowed', True)
        if policy == 'reject':
            return outcome('violated', special + '_explicitly_rejected', True)
        if policy == 'unknown':
            return outcome('unknown', special + '_policy_unresolved', True)
        if policy != 'evaluate' or special in {'missing', 'null'}:
            raise ValueError('Missing/null require explicit allow/reject/unknown policy')
    predicate = rule['predicate']
    kind = predicate['kind']
    if kind == 'present_nonnull':
        passed = value is not MISSING and value is not None
    elif kind == 'enum':
        allowed = predicate['values']
        if not isinstance(allowed, list) or any(isinstance(v, (dict,list)) for v in allowed):
            raise ValueError('Only explicit scalar enumerations supported')
        passed = any(scalar_equal(value, v) for v in allowed)
    elif kind == 'length':
        if not isinstance(value, str):
            return outcome('unknown', 'predicate_domain_mismatch', True)
        lower, upper = predicate['minimum'], predicate['maximum']
        if (any(x is not None and (type(x) is not int or x < 0) for x in (lower,upper))
                or (lower is not None and upper is not None and lower > upper)):
            raise ValueError('Length bounds must be ordered nonnegative integers or unbounded')
        units = predicate['units']
        if units == 'unicode_codepoints':
            length = len(value)
        elif units == 'utf16_code_units':
            length = len(value.encode('utf-16-le', errors='surrogatepass')) // 2
        else:
            return outcome('unknown', 'unsupported_length_units', True)
        passed = (lower is None or lower <= length) and (upper is None or length <= upper)
    elif kind == 'numeric_range':
        if isinstance(value, bool) or not isinstance(value, (int,float)) or not math.isfinite(value):
            return outcome('unknown', 'predicate_domain_mismatch', True)
        lower, upper = predicate['minimum'], predicate['maximum']
        if any(isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) for x in (lower,upper)) or lower > upper:
            raise ValueError('Numeric bounds must be finite and ordered')
        passed = lower <= value <= upper
    else:
        return outcome('unknown', 'unsupported_predicate', True)
    return outcome('satisfied' if passed else 'violated', 'predicate_evaluated', True)
