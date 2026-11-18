"""Bounded lifecycle transitions for the prospective ordinary coordinator.

No dispatch, retry, automatic rollback, or scientific qualification. Failure
poisons this instance; the owning coordinator retains evidence and cleans up.
"""
import json
import os
import subprocess
import time
import seatsurfing_postgres_checkpoint_v2 as checkpoint

LABEL = 'seatsurfing-qualification-v1'


def command(argv):
    result = subprocess.run(argv, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=20)
    if result.returncode or result.stderr:
        raise RuntimeError('Lifecycle command failed; stderr_sha256=' + checkpoint.digest(result.stderr))
    return result.stdout


class FixtureLifecycle:
    def __init__(self, build):
        if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('GITHUB_REPOSITORY') != 'shravaniparsi/mixed-interface-study':
            raise RuntimeError('Lifecycle requires the registered study CI repository')
        if build.get('study_commit') != os.environ.get('GITHUB_SHA'):
            raise RuntimeError('Build and executing study commit differ')
        self.image = checkpoint.bind_build(build)
        self.ids = None
        self.processes = None
        self.phase = 'running'
        self.events = []
        self._inspect('running')

    def _inspect(self, expected):
        items = json.loads(command(['docker', 'inspect', checkpoint.APP, checkpoint.PG, checkpoint.BROWSER]))
        if len(items) != 3:
            raise RuntimeError('Incomplete fixture inspection')
        app, pg, browser = items
        ids = tuple(item['Id'] for item in items)
        if self.ids is not None and self.ids != ids:
            raise RuntimeError('Fixture container identity changed')
        for item, image in zip(items, (self.image, checkpoint.PG_IMAGE_ID, checkpoint.BROWSER_IMAGE_ID)):
            if item['Image'] != image or item['Config'].get('Labels', {}).get('org.mixed-interface.study') != LABEL:
                raise RuntimeError('Fixture image or ownership mismatch')
            if item['State'].get('Restarting') or item['HostConfig'].get('RestartPolicy', {}).get('Name') != 'no':
                raise RuntimeError('Restarting fixture unsupported')
        if pg['HostConfig']['NetworkMode'] != 'none' or not pg['State']['Running'] or pg['State']['Paused']:
            raise RuntimeError('Database isolation/state mismatch')
        for item in (app, browser):
            if item['HostConfig']['NetworkMode'] not in ('container:' + checkpoint.PG, 'container:' + pg['Id']):
                raise RuntimeError('Fixture network namespace mismatch')
            running, paused = {'running': (True, False), 'paused': (True, True), 'stopped': (False, False)}[expected]
            if item['State']['Running'] is not running or item['State']['Paused'] is not paused:
                raise RuntimeError('Unexpected ' + expected + ' fixture state')
        processes = tuple((item['State']['Pid'], item['State']['StartedAt'], item['RestartCount']) for item in items)
        if expected != 'stopped':
            if any(not isinstance(pid, int) or pid <= 0 or not started or count != 0 for pid, started, count in processes):
                raise RuntimeError('Invalid or restarted fixture process')
            if self.processes is not None and self.processes != processes:
                raise RuntimeError('Warm fixture process identity changed')
            self.processes = processes
        self.ids = ids
        return {'container_ids': list(ids), 'processes': [list(p) for p in processes], 'state': expected, 'observed_at_us': time.time_ns() // 1000}

    def _transition(self, expected, target, action):
        if self.phase != expected:
            raise RuntimeError('Invalid or previously failed lifecycle transition')
        event = {'from': expected, 'to': target, 'started_at_us': time.time_ns() // 1000}
        self.events.append(event)
        self.phase = 'failed'  # Never retry a partly executed transition.
        try:
            event['before'] = self._inspect(expected)
            action()
            event['after'] = self._inspect(target)
            if target == 'paused':
                checkpoint.CAPTURE_PAUSED = True
                checkpoint.guard()  # Reject in-flight DB work, even with quiet HTTP.
            elif target == 'stopped':
                checkpoint.CAPTURE_PAUSED = False
                checkpoint.guard()  # Require zero other DB connections before restore.
            event['status'] = 'observed'
            self.phase = target
            return event
        except Exception as error:
            event['status'] = 'failed'
            event['error_type'] = type(error).__name__
            raise

    def pause(self):
        def action():
            # Freeze the client first so no new requests follow the server pause.
            command(['docker', 'pause', checkpoint.BROWSER])
            command(['docker', 'pause', checkpoint.APP])
        return self._transition('running', 'paused', action)

    def resume(self):
        def action():
            command(['docker', 'unpause', checkpoint.APP])
            command(['docker', 'unpause', checkpoint.BROWSER])
        return self._transition('paused', 'running', action)

    def stop(self, close_browser):
        # Caller resumes explicitly before this operation. Closing stdin lets
        # the worker retain its final trace and close Chromium before app stop.
        def action():
            close_browser()
            command(['docker', 'stop', '--time', '10', checkpoint.APP])
        return self._transition('running', 'stopped', action)
