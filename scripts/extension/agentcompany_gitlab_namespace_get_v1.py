"""One bounded GET from the invoking network namespace; no redirects or proxies."""
import base64
import json
import os
import sys
import urllib.error
import urllib.request


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, fp, code, msg, headers, newurl):
        return None


def fetch(path, authenticate, limit, opener=None):
    assert path.startswith('/') and not path.startswith('//')
    assert limit in (4096, 2 * 1024**2)
    opener = opener or urllib.request.build_opener(urllib.request.ProxyHandler({}), NoRedirect())
    result = dict(method='GET', path=path, network_namespace=os.readlink('/proc/self/ns/net'))
    request = urllib.request.Request('http://127.0.0.1:8929' + path, method='GET',
                                    headers={'PRIVATE-TOKEN': 'root-token'} if authenticate else {})
    try:
        try:
            response = opener.open(request, timeout=10 if limit == 4096 else 15)
        except urllib.error.HTTPError as error:
            response = error
        with response:
            raw = response.read(limit + 1)
            result.update(status=response.status, final_url=response.geturl(), next_page=response.headers.get('X-Next-Page', ''),
                          body_base64=base64.b64encode(raw[:limit]).decode(), truncated=len(raw) > limit)
    except Exception as error:
        result.update(error_type=type(error).__name__, error=str(error)[:2000])
    return result


if __name__ == '__main__':
    path, authenticate, limit = sys.argv[1:]
    assert authenticate in ('yes', 'no')
    print(json.dumps(fetch(path, authenticate == 'yes', int(limit))))
