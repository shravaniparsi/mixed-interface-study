#!/usr/bin/env python3
"""Read-only fixture discovery after native-form login; never persist credentials."""
import argparse
import ast
import http.cookiejar
import hashlib
from html.parser import HTMLParser
import json
from pathlib import Path
import urllib.parse
import urllib.request

ROOT = Path(__file__).resolve().parents[2]

class LoginForm(HTMLParser):
    def __init__(self):
        super().__init__()
        self.csrf = None
    def handle_starttag(self, tag, attrs):
        values = dict(attrs)
        if tag == 'input' and values.get('name') == 'authenticity_token':
            self.csrf = values.get('value')

def benchmark_credentials():
    source_path = 'tests/integration/environments/gitlab/conftest.py'
    records = json.loads((ROOT / 'evidence/benchmark-gitlab-runtime-source-v1.json').read_text())
    expected = next(row['sha256'] for row in records if row['path'] == source_path)
    url = 'https://raw.githubusercontent.com/ServiceNow/webarena-verified/6473f72db5dcefc97b5725b59e734504edc28a21/' + source_path
    with urllib.request.urlopen(url, timeout=30) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != expected:
        raise ValueError('Pinned public benchmark fixture hash changed')
    tree = ast.parse(data.decode())
    function = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'gitlab_credentials')
    return ast.literal_eval(next(n.value for n in function.body if isinstance(n, ast.Return)))

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--base-url', default='http://127.0.0.1:8023')
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    # This instrument may only contact the disposable local benchmark.
    parsed = urllib.parse.urlsplit(args.base_url)
    if parsed.scheme != 'http' or parsed.hostname not in ('127.0.0.1', 'localhost') or parsed.port != 8023 or parsed.path:
        raise ValueError('Only the local disposable GitLab on port 8023 is supported')
    base = args.base_url
    class LocalRedirect(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            target = urllib.parse.urlsplit(newurl)
            if target.scheme != 'http' or target.hostname not in ('127.0.0.1','localhost') or target.port != 8023:
                raise ValueError('Refusing nonlocal redirect')
            return super().redirect_request(req, fp, code, msg, headers, newurl)
    jar = http.cookiejar.CookieJar()
    client = urllib.request.build_opener(LocalRedirect(), urllib.request.HTTPCookieProcessor(jar))
    evidence = {'scientific_cases_executed': 0, 'business_object_writes': 0, 'authenticated': False, 'requests': []}
    args.output.parent.mkdir(parents=True, exist_ok=True)
    def save():
        args.output.write_text(json.dumps(evidence, indent=2)+'\n')
    def get_json(path):
        with client.open(base + path, timeout=30) as response:
            evidence['requests'].append({'method': 'GET', 'path': path, 'status': response.status})
            return json.load(response)
    try:
        with client.open(base+'/users/sign_in', timeout=30) as response:
            form = LoginForm(); form.feed(response.read().decode())
        if not form.csrf:
            raise ValueError('Native login form has no authenticity token')
        credentials = benchmark_credentials()
        data = urllib.parse.urlencode({'authenticity_token':form.csrf, 'user[login]':credentials['username'], 'user[password]':credentials['password'], 'user[remember_me]':'0'}).encode()
        with client.open(urllib.request.Request(base+'/users/sign_in', data=data, headers={'Referer':base+'/users/sign_in'}), timeout=30) as response:
            evidence['login_final_path'] = urllib.parse.urlsplit(response.url).path
        user = get_json('/api/v4/user')
        evidence['actor'] = {k:user.get(k) for k in ('id','username','state')}
        evidence['authenticated'] = user.get('username') == credentials['username']
        if not evidence['authenticated']:
            raise ValueError('Authenticated actor differs from benchmark fixture')
        projects = get_json('/api/v4/projects?membership=true&search=empathy-prompts&per_page=100')
        evidence['issue_project_candidates'] = [{k:p.get(k) for k in ('id','path_with_namespace','default_branch','visibility','permissions')} for p in projects]
        evidence['user_candidates'] = {}
        for name in ('Roshan','primer','convexegg','abishek'):
            users = get_json('/api/v4/users?search='+urllib.parse.quote(name)+'&per_page=100')
            evidence['user_candidates'][name] = [{k:u.get(k) for k in ('id','username','name','state')} for u in users]
        evidence['qualification_scope'] = 'Authentication and candidate discovery only; ambiguity and permissions require review before binding fixtures.'
    except Exception as exc:
        evidence['failure_type'] = type(exc).__name__
        raise
    finally:
        save()

if __name__ == '__main__':
    main()
