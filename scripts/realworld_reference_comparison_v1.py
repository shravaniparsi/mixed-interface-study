"""Conservative, retrospective reference comparison for article-update/comment.

Never changes raw evidence or the frozen terminal result. This first version
qualifies only individually clean branches; mismatch generalization is deferred.
"""
from copy import deepcopy
from urllib.parse import quote
from realworld_rejection_outcomes import pair_result


def projection(article):
    return {k: article[k] for k in ('slug', 'title', 'description', 'body', 'tagList')} | {
        'author': article['author']['username']}


def command(raw, stage):
    guards = [g for g in raw['integrity']['guards']
              if g['name'] == 'submitted_command' and g['stage'] == stage]
    if len(guards) != 1:
        return None
    g = guards[0]
    return g['observed'] if g['passed'] is True and g['observed'] == g['expected'] else None


def binding(raw, channel):
    """Recompute local identity binding from ordered requests and responses."""
    try:
        state = raw['prefix_state']; slug = state['slug']
        if not isinstance(slug, str) or not slug.strip():
            return False
        prefix = command(raw, 'prefix'); consumer = command(raw, 'continuation')
        path = '/api/articles/' + quote(slug, safe='')
        if prefix is None or consumer is None or consumer['method'] != 'POST' or consumer['path'] != path + '/comments':
            return False
        events = raw['trace']
        sequences = [e['sequence'] for e in events]
        if sequences != sorted(set(sequences)):
            return False

        def exchange(phase, source, method, target, payload=None, before=None):
            matches = [e for e in events if e.get('type') in ('request', 'response') and e['phase'] == phase and
                       e['source'] == source and e['method'] == method and e['path'] == target
                       and (before is None or e['sequence'] < before)]
            req = [e for e in matches if e['type'] == 'request']
            res = [e for e in matches if e['type'] == 'response']
            if len(req) != 1 or len(res) != 1:
                raise ValueError('Ambiguous or missing exchange')
            a, b = req[0], res[0]
            if not (a['sequence'] < b['sequence'] and 200 <= b['status'] < 300):
                raise ValueError('Unsuccessful or unordered exchange')
            if payload is not None and a.get('payload') != payload:
                raise ValueError('Submitted payload differs')
            if source == 'ui' and (not a.get('capture_request_id') or
                                  a['capture_request_id'] != b.get('capture_request_id')):
                raise ValueError('Browser response binding differs')
            return a, b

        _, produced = exchange('prefix', 'api', prefix['method'], prefix['path'], prefix['payload'])
        written_req, _ = exchange('continuation', channel, 'POST', path + '/comments', consumer['payload'])
        loaded_req, loaded = exchange('continuation', channel, 'GET', path, before=written_req['sequence'])
        return (produced['sequence'] < loaded_req['sequence'] < loaded['sequence'] < written_req['sequence']
                and projection(produced['data']['article']) == state
                and projection(loaded['data']['article']) == state)
    except (KeyError, TypeError, ValueError):
        return False


def compare(job, branches, spec, fixture, fixture_sha, cleanup, evidence):
    original = pair_result(job, branches, spec, fixture, fixture_sha, cleanup, evidence)
    gates = deepcopy(original['comparability'])
    eligible = (spec['workflow'] == 'article-update-comment' and set(branches) == {'api', 'ui'}
                and all(b['kind'] == 'clean_observation' for b in original['branches'].values())
                and original['terminal']['kind'] in ('clean_observation', 'incomparable_observation'))
    local = {c: binding(raw, c) for c, (raw, _) in branches.items()} if eligible else {}
    applied = eligible and all(local.values())
    if applied:
        a, u = (branches[c][0] for c in ('api', 'ui'))
        # Remove only the proved reference slot, never recursively replace strings.
        states = [{k: v for k, v in raw['prefix_state'].items() if k != 'slug'} for raw in (a, u)]
        commands = [{k: v for k, v in command(raw, 'continuation').items() if k != 'path'} for raw in (a, u)]
        gates['same_prefix_state'] = states[0] == states[1]
        gates['same_consumer_command'] = commands[0] == commands[1]
    qualified = bool(applied and gates and all(gates.values()))
    return {'comparison_version': 1, 'original_kind': original['terminal']['kind'],
            'derived_kind': 'clean_observation' if qualified else original['terminal']['kind'],
            'reference_comparison_qualified': qualified, 'local_bindings': local,
            'original_gates': original['comparability'], 'derived_gates': gates,
            'new_primary_samples': 0, 'prospective_dispatch_qualified': False}
