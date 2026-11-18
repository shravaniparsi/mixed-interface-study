"""Read-only, value-free startup probes for the last registered qualification.

No response bodies, environment values, process arguments or raw log lines leave
these helpers. Functions are embedded in docker exec; importing runs no probe.
"""
import hashlib
import json
import re
import urllib.error
import urllib.request
from pathlib import Path

LOG_MARKERS = (
    'Permission denied', 'Connection refused', 'ModuleNotFoundError',
    'ImportError', 'ValidationError', 'SyntaxError', 'OperationalError',
    'No such file or directory', 'Address already in use',
    'Failed to load config.yaml', 'activating safe mode',
    'Database is not ready', 'Traceback (most recent call last)',
    'Out of memory', 'Killed',
)


def summarize_log(raw):
    text = raw.decode(errors='replace')
    return {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
            'marker_counts': {marker: text.count(marker) for marker in LOG_MARKERS}}


def probe():
    try:
        with urllib.request.urlopen('http://127.0.0.1:8888/api/v1/auth/enabled', timeout=2) as response:
            return {'ready': response.status == 200, 'http_status': response.status}
    except urllib.error.HTTPError as error:
        return {'ready': False, 'http_status': error.code, 'error_type': type(error).__name__}
    except urllib.error.URLError as error:
        return {'ready': False, 'error_type': type(error).__name__,
                'reason_type': type(error.reason).__name__, 'errno': getattr(error.reason, 'errno', None)}
    except Exception as error:
        return {'ready': False, 'error_type': type(error).__name__}


def snapshot():
    config = Path('/config/config.yaml')
    result = {'config_exists': config.is_file(), 'listening_ports': {}, 'process_counts': {}}
    if config.is_file():
        raw = config.read_bytes()
        info = config.stat()
        result['config'] = {'bytes': len(raw), 'sha256': hashlib.sha256(raw).hexdigest(),
                            'mode': info.st_mode & 0o7777, 'uid': info.st_uid, 'gid': info.st_gid}
    for family in ['tcp', 'tcp6']:
        path = Path('/proc/net') / family
        if path.exists():
            result['listening_ports'][family] = sorted({int(line.split()[1].split(':')[1], 16)
                for line in path.read_text().splitlines()[1:] if line.split()[3] == '0A'})
    known = {'nginx', 'python3', 'python', 'postgres', 's6-svscan', 's6-supervise', 'go2rtc', 'bash'}
    for path in Path('/proc').glob('[0-9]*/comm'):
        try:
            name = path.read_text().strip()
        except (FileNotFoundError, PermissionError, ProcessLookupError):
            continue
        key = name if name in known else 'other'
        result['process_counts'][key] = result['process_counts'].get(key, 0) + 1
    log = Path('/config/viseron.log')
    if log.is_file():
        result['application_log'] = summarize_log(log.read_bytes())
    return result
