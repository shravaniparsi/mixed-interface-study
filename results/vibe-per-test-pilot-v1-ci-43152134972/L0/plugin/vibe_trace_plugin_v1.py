"""Record pytest stages and local HTTP exchanges without changing assertions."""
import hashlib
import json
import os
from pathlib import Path
import time
from urllib.parse import urlsplit
import pytest
import requests

EVENTS = Path(os.environ['VIBE_TRACE_EVENTS'])
NODE = None
ORIGINAL_SEND = requests.Session.send


def emit(row):
    with EVENTS.open('a') as stream:
        stream.write(json.dumps({'monotonic': time.monotonic(), 'nodeid': NODE, **row}, ensure_ascii=False) + '\n')


def body(value):
    if value is None:
        return None
    raw = value if isinstance(value, bytes) else str(value).encode()
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(), 'text': raw[:65536].decode('utf-8', errors='replace'), 'truncated': len(raw) > 65536}


def send(session, request, **kwargs):
    target = urlsplit(request.url)
    if target.hostname not in {'localhost', '127.0.0.1', '::1'} or target.port != 8000 or target.scheme != 'http':
        emit({'kind': 'blocked_external_http', 'method': request.method, 'url': request.url})
        raise RuntimeError('Pilot restricts HTTP traffic to the disposable local API')
    row = {'kind': 'http', 'method': request.method, 'url': request.url, 'request_body': body(request.body)}
    try:
        response = ORIGINAL_SEND(session, request, **kwargs)
        row.update(status=response.status_code, response_body=body(response.content))
        emit(row)
        return response
    except Exception as error:
        row.update(exception=type(error).__name__, message=str(error))
        emit(row)
        raise


def pytest_configure(config):
    requests.Session.send = send
    emit({'kind': 'configure'})


def pytest_collection_finish(session):
    emit({'kind': 'collection', 'nodeids': [item.nodeid for item in session.items]})


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_protocol(item, nextitem):
    global NODE
    NODE = item.nodeid
    yield
    NODE = None


@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    emit({'kind': 'test_report', 'test_nodeid': item.nodeid, 'when': report.when, 'outcome': report.outcome,
          'exception': call.excinfo.typename if call.excinfo else None,
          'longrepr': report.longreprtext if report.failed else '', 'wasxfail': getattr(report, 'wasxfail', None)})


def pytest_sessionfinish(session, exitstatus):
    emit({'kind': 'session_finish', 'exitstatus': int(exitstatus)})


def pytest_unconfigure(config):
    requests.Session.send = ORIGINAL_SEND
