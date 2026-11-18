"""Check empty runtime fixtures and both original immediate startup timers.

Caller must provide original-driver state and Docker logs scoped to the current
authoritatively inspected StartedAt. This is not a standalone readiness gate.
"""
import hashlib
import re

MARKERS = (
    ('Logrotate Timer initialized', 'Logrotate completed.'),
    ("Let's Encrypt Renewal Timer initialized", 'Completed SSL cert renew process'),
)


def verify_startup_fixture(database_state, current_startup_logs):
    tables = {row['name']: row for row in database_state['tables']}
    if len(tables) != len(database_state['tables']):
        raise ValueError('Duplicate original database table')
    for name in ('certificate', 'proxy_host'):
        if name not in tables or tables[name]['rows'] != []:
            raise ValueError('Required completely empty fixture table: ' + name)
    if not isinstance(current_startup_logs, bytes) or len(current_startup_logs) > 2 * 1024 * 1024:
        raise ValueError('Startup-log bound/type')
    text = current_startup_logs.decode('utf8')
    text = re.sub(r'\x1b\[[0-9;]*m', '', text)
    for started, completed in MARKERS:
        if text.count(started) != 1 or text.count(completed) != 1:
            raise ValueError('Missing/repeated startup timer or completion evidence')
        if text.index(started) >= text.index(completed):
            raise ValueError('Startup completion precedes initialization')
    return {'empty_certificate_fixture_verified': True, 'empty_proxy_host_fixture_verified': True,
            'initial_certificate_timer_settled': True, 'initial_logrotation_settled': True,
            'startup_log_sha256': hashlib.sha256(current_startup_logs).hexdigest(),
            'status': 'fixture_and_startup_markers_verified_remaining_state_unqualified'}
