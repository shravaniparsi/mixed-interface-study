"""Source-qualified RealWorld expectations; never rewrite submitted commands.

These rules describe the pinned implementation, not independent defect authority.
Raw observed representations remain available even when membership agrees.
"""
from copy import deepcopy


def exact(left, right):
    if type(left) is not type(right):
        return False
    if isinstance(left, dict):
        return left.keys() == right.keys() and all(exact(left[k], right[k]) for k in left)
    if isinstance(left, list):
        return len(left) == len(right) and all(exact(a, b) for a, b in zip(left, right))
    return left == right


def tag_response(tags):
    if not isinstance(tags, list) or any(type(t) is not str for t in tags):
        raise ValueError('Tags must be an explicit array of strings')
    return sorted(set(tags))


def tag_comparison(expected, observed):
    wanted, actual = tag_response(expected), tag_response(observed)
    return {'expected_raw': deepcopy(expected), 'observed_raw': deepcopy(observed),
            'membership_equal': wanted == actual,
            'expected_response': wanted, 'response_representation_equal': wanted == observed,
            'observed_has_duplicates': len(observed) != len(set(observed)),
            'observed_sorted': observed == sorted(observed)}


def article_create(payload):
    if type(payload) is not dict or set(payload)-{'title','description','body','tagList'}:
        raise ValueError('Unsupported article-create field')
    for field in ('title','description','body'):
        if type(payload.get(field)) is not str or not payload[field]:
            raise ValueError('No accepted-state expectation for invalid create input')
    return {**{k: payload[k] for k in ('title','description','body')},
            'tagList': tag_response(payload.get('tagList', []))}


def article_body_update(before, patch):
    # Title/slug changes and explicit-null updates need their own registered rule.
    if type(patch) is not dict or set(patch)-{'body','description','tagList'}:
        raise ValueError('Unsupported article update scope')
    result = article_create(before)
    for field in ('body','description'):
        if field in patch:
            if type(patch[field]) is not str or not patch[field]:
                raise ValueError('Unsupported null or empty partial article field')
            result[field] = patch[field]
    if 'tagList' in patch:
        result['tagList'] = tag_response(patch['tagList'])
    return result


def profile_update(before, patch):
    fields = {'username','email','bio','image'}
    if type(before) is not dict or set(before) != fields or type(patch) is not dict or set(patch)-fields:
        raise ValueError('Incomplete or unsupported profile scope')
    if any(type(before[k]) is not str for k in ('username','email')):
        raise ValueError('Invalid profile identity')
    if any(before[k] is not None and type(before[k]) is not str for k in ('bio','image')):
        raise ValueError('Invalid nullable profile field')
    result = deepcopy(before)
    for key, value in patch.items():
        if key in {'username','email'}:
            if not exact(value, before[key]):
                raise ValueError('Identity changes require separate normalization rules')
        else:
            if value is not None and type(value) is not str:
                raise ValueError('Unsupported profile value')
            result[key] = None if value is None or value == '' else value
    return result
