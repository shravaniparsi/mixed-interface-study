"""Ordinary coordinator: producer stage and original warm editor preparation.

No CLI dispatcher. Parent owns the registered job, build/provision, checkpoint,
continuation branches, evidence sealing and teardown. This stage cannot qualify
an application on its own and must never be rerun after a partial failure.
"""
import hashlib
import json
import os
from pathlib import Path
import time
from launch_seatsurfing_browser_v1 import launch_native_browser
from launch_seatsurfing_api_v1 import run_api_operation
from seatsurfing_fixture_lifecycle_v1 import FixtureLifecycle
from capture_seatsurfing_comparison_state_v1 import capture_state
from compare_seatsurfing_ordinary_producers_v1 import compare_creation_step, compare_producer_rows
from compare_seatsurfing_ordinary_state_v1 import compare_ordinary_state
from verify_seatsurfing_actor_state_v1 import verify_actor_state


def write_private(path, value):
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, 'w') as stream: json.dump(value, stream, indent=2); stream.write('\n')


def observe_command(bridge, command):
    """Send once; short read timeouts observe the SAME original pending handle."""
    try:
        return bridge.send(command, command_seconds=90, observe_seconds=30)
    except TimeoutError:
        while bridge.pending is not None and not bridge.failed:
            try:
                return bridge.observe_pending(seconds=30)
            except TimeoutError:
                continue
        raise TimeoutError('Original native command deadline exhausted; no resend') from None


class OrdinaryCoordinator:
    def __init__(self, *, build_report, provision_report, public_key, directory, edit, node_binary='node'):
        if edit not in [{'path':'/description','value':'Edit description'}, {'path':'/announcement','value':'Edit notice'}]:
            raise ValueError('Ordinary edit is outside frozen coverage')
        self.build_report = Path(build_report).absolute()
        self.provision_report = Path(provision_report).absolute()
        self.public_key = Path(public_key).absolute()
        self.directory = Path(directory).absolute()
        self.edit, self.node_binary = edit, node_binary
        self.build = json.loads(self.build_report.read_text())
        self.provision = json.loads(self.provision_report.read_text())
        if self.provision.get('status') != 'isolated_fixture_ready_browser_and_actor_unqualified':
            raise ValueError('Require successful original provisioning')
        if self.provision['build_report_sha256'] != hashlib.sha256(self.build_report.read_bytes()).hexdigest():
            raise ValueError('Provisioning does not bind this build')
        self.config = json.loads(Path(self.provision['native_login_config']).read_text())
        if self.config.get('mode') != 'native_login' or self.config.get('origin') != 'http://127.0.0.1:8080':
            raise ValueError('Require original native-login configuration')
        self.organization = self.config['login']['organizationId']
        self.directory.mkdir(parents=True, mode=0o700, exist_ok=False)
        self.phase, self.bridge, self.lifecycle = 'prepared', None, None
        self.report = {'status':'prepared', 'edit':edit, 'scientific_cases_executed':0, 'runtime_qualified':False}

    def actor(self, name, capture, storage, expected=None):
        result = verify_actor_state(build_report=self.build_report, provision_report=self.provision_report,
            storage=storage, storage_sha256=capture['storageSha256'], events=capture['network']['events'],
            public_key=self.public_key, organization_id=self.organization,
            private_directory=self.directory/name, expected_continuity=expected, node_binary=self.node_binary)
        if result['status'] != 'actor_acquisition_and_identity_verified':
            raise RuntimeError('Ordinary actor acquisition/identity unavailable')
        return result

    def snapshot(self, name):
        result = capture_state(self.build)
        write_private(self.directory/(name+'.json'), result)
        return result

    def producer_stage(self):
        if self.phase != 'prepared': raise RuntimeError('Producer stage can execute only once')
        self.phase = 'in_progress'
        try:
            self.bridge = launch_native_browser(tools=self.provision['node_tools'],
                configuration=self.provision['native_login_config'], private_directory=self.directory/'native',
                build_report=self.build_report)
            # A startup observation timeout does not authorize another launch.
            while not self.bridge.ready and not self.bridge.failed:
                try: self.bridge.await_ready(seconds=30)
                except TimeoutError: continue
            if not self.bridge.ready: raise RuntimeError('Original browser startup unavailable')
            self.lifecycle = FixtureLifecycle(self.build)
            observe_command(self.bridge, {'requestId':'login','operation':'login'})
            session_capture = observe_command(self.bridge, {'requestId':'session','operation':'session_storage'})
            storage = self.bridge.artifact_directory/'session-storage.json'
            self.lifecycle.pause()
            original_actor = self.actor('actor-before-producers', session_capture, storage)
            session_id = original_actor['continuity']['sessionId']
            before_native = self.snapshot('before-native-create')
            native_start = time.time_ns() // 1000
            self.lifecycle.resume()
            native = observe_command(self.bridge, {'requestId':'create','operation':'create'})
            self.lifecycle.pause()
            native_end = time.time_ns() // 1000
            after_native = self.snapshot('after-native-create')
            native_comparison = compare_creation_step(before_native, after_native, location_id=native['createdId'],
                session_id=session_id, window_start_us=native_start, window_end_us=native_end)
            write_private(self.directory/'native-creation-comparison.json', native_comparison)

            api_start = time.time_ns() // 1000
            self.lifecycle.resume()
            api_report = run_api_operation(operation='ordinary_create', storage=storage,
                storage_sha256=session_capture['storageSha256'], build_report=self.build_report,
                private_directory=self.directory/'api-create')
            if api_report['status'] != 'api_worker_result_retained': raise RuntimeError('API producer worker unavailable')
            api = api_report['result']['result']
            if api.get('outcome') != 'ordinary_create_http_observed': raise RuntimeError('Ordinary API create not observed')
            self.lifecycle.pause()
            api_end = time.time_ns() // 1000
            after_api = self.snapshot('after-api-create')
            api_comparison = compare_creation_step(after_native, after_api, location_id=api['createdId'],
                session_id=session_id, window_start_us=api_start, window_end_us=api_end)
            write_private(self.directory/'api-creation-comparison.json', api_comparison)
            paired = compare_producer_rows(native_comparison, api_comparison, organization_id=self.organization)
            write_private(self.directory/'producer-pair.json', paired)

            open_start = time.time_ns() // 1000
            self.lifecycle.resume()
            opened = observe_command(self.bridge, {'requestId':'open','operation':'open','id':api['createdId'],'apiProducer':api})
            checkpoint_capture = observe_command(self.bridge, {'requestId':'capture','operation':'capture'})
            self.lifecycle.pause()
            open_end = time.time_ns() // 1000
            checkpoint_storage = self.bridge.artifact_directory/'browser-storage.json'
            current_actor = self.actor('actor-at-warm-editor', checkpoint_capture, checkpoint_storage, original_actor['continuity'])
            warm_state = self.snapshot('warm-editor-state')
            load_comparison = compare_ordinary_state(after_api, warm_state, session_id=session_id,
                location_id=api['createdId'], window_start_us=open_start, window_end_us=open_end)
            write_private(self.directory/'native-open-comparison.json', load_comparison)
            self.phase = 'warm_editor_paused'
            self.report.update(status=self.phase, native_id=native['createdId'], api_id=api['createdId'],
                session_id=session_id, producer_rows=paired, actor=current_actor,
                checkpoint_storage=str(checkpoint_storage), storage_sha256=checkpoint_capture['storageSha256'])
            # Keep the same browser/processes for checkpoint and the warm edit.
            # Parent must retain/seal and clean up even if any later gate fails.
            return {'opened':opened,'capture':checkpoint_capture,'state':warm_state,
                    'actor':current_actor,'storage':checkpoint_storage,'api_id':api['createdId']}
        except Exception as error:
            self.phase = 'failed'
            self.report.update(status='producer_stage_unavailable',error_type=type(error).__name__)
            raise
        finally:
            if self.lifecycle is not None:
                write_private(self.directory/'producer-lifecycle.json', self.lifecycle.events)
            write_private(self.directory/'producer-stage.json', self.report)
