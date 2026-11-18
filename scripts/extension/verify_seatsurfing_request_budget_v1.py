"""Conservative authenticated-request ceiling per original application lifetime."""
import hashlib
from urllib.parse import urlparse

CEILING = 200


def authenticated(headers, token_hash):
    value = headers.get('authorization')
    if value is None: return 0
    if not isinstance(value, str) or not value.startswith('Bearer ') or hashlib.sha256(value[7:].encode()).hexdigest() != token_hash:
        raise ValueError('Unexpected authenticated request identity')
    return 1


def origin(url):
    parsed = urlparse(url)
    if parsed.scheme != 'http' or parsed.netloc != '127.0.0.1:8080':
        raise ValueError('Request outside isolated original origin')


def count_native(trace, token_hash):
    if trace.get('failure') is not None or trace.get('pendingIds') != [] or trace.get('pendingCaptures') != 0:
        raise ValueError('Require final complete native trace')
    events = trace['events']
    if any(e['kind'] in ['request_failed', 'capture_failure'] for e in events): raise ValueError('Failed native observation')
    requests = [e for e in events if e['kind'] == 'request']
    ids = [r['id'] for r in requests]
    if len(set(ids)) != len(ids): raise ValueError('Duplicate native request identity')
    count = 0
    for request in requests:
        origin(request['url'])
        matched = {}
        for kind in ['request_headers', 'response', 'finished']:
            rows = [e for e in events if e['kind'] == kind and e['id'] == request['id']]
            if len(rows) != 1: raise ValueError('Incomplete native request evidence')
            matched[kind] = rows[0]
        if matched['response']['status'] == 429: raise ValueError('Observed throttling is not a validation result')
        count += authenticated(matched['request_headers']['headers'], token_hash)
    # Orphan request metadata could otherwise hide observed traffic.
    for event in events:
        if event['kind'] in ['request_headers', 'response', 'finished'] and event['id'] not in ids:
            raise ValueError('Orphan native request evidence')
    return {'total_requests':len(requests), 'authenticated_requests':count}


def count_api(rows, token_hash):
    count = 0
    for row in rows:
        request = row.get('request', row)
        response = row.get('response', row)
        origin(request['url'])
        if response.get('status') == 429: raise ValueError('Observed throttling is not a validation result')
        if not isinstance(response.get('status'), int): raise ValueError('Missing API response status')
        if not isinstance(row.get('completedAt'), (int, float)) or row['completedAt'] < row['dispatchedAt']:
            raise ValueError('Incomplete API request evidence')
        count += authenticated(request['headers'], token_hash)
    return {'total_requests':len(rows), 'authenticated_requests':count}


def verify_request_budget(*, native_trace, api_envelopes, token_hash, application_environment):
    if application_environment.get('RATE_LIMIT') != '250' or application_environment.get('RATE_LIMIT_PERIOD') != '1-M':
        raise ValueError('Require explicit original limiter defaults')
    native = count_native(native_trace, token_hash)
    api = count_api(api_envelopes, token_hash)
    total = native['authenticated_requests'] + api['authenticated_requests']
    if total > CEILING: raise ValueError('Conservative whole-process request ceiling exceeded')
    return {'status':'observed_requests_below_original_rate_limit', 'native':native, 'api':api,
            'whole_process_authenticated_requests':total, 'ceiling':CEILING,
            'original_limit':250, 'original_period':'1-M', 'minimum_margin':250-total,
            'uses_sliding_window_estimate':False, 'all_clients_accounted_for_by_parent':False,
            'transport_qualified':False, 'runtime_qualified':False}
