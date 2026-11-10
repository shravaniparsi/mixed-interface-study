"""Independently reconstruct branch-local database checkpoints and their ordering.

Caller must qualify job/source/runtime/reset and the request trace separately.
This validator checks the database side of that same branch, not another run.
"""
from pathlib import Path
from realworld_identity_db_state_v1 import sha, project
from realworld_identity_extract_v1 import require, strict_json_equal


def validate(raw, directory, fixture):
    directory = Path(directory)
    record = raw['database_capture']
    require(record['version'] == 2, 'Capture version differs')
    names = {'capture_identity_database_v2.py', 'realworld_identity_db_state_v1.py'}
    require(set(record['sources']) == names, 'Capture source inventory differs')
    for name in names:
        require(record['sources'][name] == sha(Path(__file__).with_name(name)), 'Capture source differs')
    trace = raw['trace']
    require([e['sequence'] for e in trace] == list(range(1, len(trace) + 1)), 'Noncontiguous trace')
    status = raw['observations']['prefix_status']
    started = raw['observations']['api_continuation_started'] or raw['observations']['ui_continuation_started']
    stages = ['before_prefix', 'after_prefix'] + (['after_continuation'] if started else [])
    require(set(record['snapshots']) == set(stages), 'Checkpoint inventory differs')
    require({p.name for p in directory.iterdir()} == {stage + '.sqlite3' for stage in stages},
            'Snapshot file inventory differs')
    events = [e for e in trace if e['type'].startswith('database_snapshot_')]
    require([(e['type'], e['stage']) for e in events] ==
            [(kind, stage) for stage in stages for kind in ('database_snapshot_started', 'database_snapshot_finished')],
            'Checkpoint event inventory differs')
    projections = {}; bounds = {}
    for i, stage in enumerate(stages):
        value = record['snapshots'][stage]; path = directory / (stage + '.sqlite3')
        require(value['file'] == path.name and not path.is_symlink(), 'Snapshot file binding differs')
        require(sha(path) == value['sha256'], 'Snapshot bytes differ')
        projection = project(path)
        require(strict_json_equal(projection, value['projection']), 'Snapshot projection differs')
        require(projection['foreign_key_violations'] == [], 'Foreign key violation')
        begin, end = events[2*i:2*i+2]
        require(end['sequence'] == begin['sequence'] + 1, 'Network or trace event during checkpoint')
        require(end['file'] == value['file'] and end['sha256'] == value['sha256'], 'Checkpoint trace binding differs')
        bounds[stage] = (begin['sequence'], end['sequence']); projections[stage] = projection
    before = projections['before_prefix']
    require(before['user']['username'] == 'pilotresearch' and before['user']['email'] == 'pilot@example.com', 'Database actor differs')
    articles = {a['slug']: a for a in before['articles']}
    require(set(articles) == {a['slug'] for a in fixture.values()}, 'Database fixture identities differ')
    for article in fixture.values():
        require(all(articles[article['slug']][k] == article[k] for k in ('title', 'description', 'body')),
                'Database fixture content differs')
    def exchange(source, phase):
        matches = [e for e in trace if e.get('source') == source and e.get('request_phase', e.get('phase')) == phase
                   and e.get('method') == 'PUT' and e.get('path') == '/api/user'
                   and e['type'] in ('request', 'response')]
        require(len(matches) == 2 and [e['type'] for e in matches] == ['request', 'response'], 'Write exchange differs')
        return matches
    prefix_request, prefix_response = exchange('api', 'prefix')
    require(type(status) is int and status == prefix_response['status'], 'Prefix response differs')
    require(bounds['before_prefix'][1] + 1 == prefix_request['sequence'], 'Write not immediately after baseline backup')
    require(prefix_response['sequence'] + 1 == bounds['after_prefix'][0], 'Backup not immediately after producer response')
    followups = [e for e in trace if e.get('source') == 'state_probe'
                 and e.get('phase') in ('prefix_readback', 'failed_prefix_followup') and e['type'] == 'request']
    require(followups and bounds['after_prefix'][1] < min(e['sequence'] for e in followups), 'Producer backup follows readback')
    if started:
        require(status == 200, 'Continuation after unsuccessful prefix')
        _, response = exchange(raw['continuation_interface'], 'continuation')
        require(response['sequence'] < bounds['after_continuation'][0], 'Continuation backup precedes response capture')
        reads = [e for e in trace if e.get('source') in ('api', 'state_probe')
                 and e.get('phase') == 'shared_readback' and e['type'] == 'request']
        require(reads and bounds['after_continuation'][1] < min(e['sequence'] for e in reads), 'Continuation backup follows diagnostic reads')
        if raw['continuation_interface'] == 'ui':
            drains = [e for e in trace if e['type'] == 'capture_drain' and e.get('reason') == 'before_database_snapshot']
            require(len(drains) == 1 and drains[0]['complete'] is True
                    and response['sequence'] < drains[0]['sequence'] < bounds['after_continuation'][0], 'UI capture not drained before backup')
    else:
        require(status != 200 or raw['observations']['continuation_outcome'] == 'identity_binding_incomplete',
                'Unexplained omitted continuation')
    return {'verified': True, 'snapshots': projections, 'scope': before['scope'],
            'restart_observed': False, 'new_primary_samples': 0}
