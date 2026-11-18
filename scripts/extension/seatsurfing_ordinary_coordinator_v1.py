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
import subprocess
import sys
from launch_seatsurfing_browser_v1 import launch_native_browser
from launch_seatsurfing_api_v1 import run_api_operation
from seatsurfing_fixture_lifecycle_v1 import FixtureLifecycle, command as lifecycle_command
from seatsurfing_postgres_checkpoint_v2 import APP, PG, BROWSER
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
            self.warm = {'opened':opened,'capture':checkpoint_capture,'state':warm_state,
                    'actor':current_actor,'storage':checkpoint_storage,'api_id':api['createdId']}
            return self.warm
        except Exception as error:
            self.phase = 'failed'
            self.report.update(status='producer_stage_unavailable',error_type=type(error).__name__)
            raise
        finally:
            if self.lifecycle is not None:
                write_private(self.directory/'producer-lifecycle.json', self.lifecycle.events)
            write_private(self.directory/'producer-stage.json', self.report)

    def capture_checkpoint(self, *, private_key):
        if self.phase != 'warm_editor_paused': raise RuntimeError('Require original paused warm editor')
        self.phase = 'checkpoint_in_progress'
        report = {'status':'checkpoint_in_progress','runtime_qualified':False}
        try:
            if hashlib.sha256(Path(private_key).read_bytes()).hexdigest() != self.provision['private_key_sha256']:
                raise RuntimeError('Private signing key differs from original provisioning')
            observed = self.lifecycle._inspect('paused')
            current = self.snapshot('pre-checkpoint-state')
            if current != self.warm['state']: raise RuntimeError('Warm state changed before checkpoint')
            storage_raw = self.warm['storage'].read_bytes()
            network_path = self.bridge.artifact_directory/'browser-network.json'
            network_raw = network_path.read_bytes()
            proof = build_checkpoint_observation(self.warm, storage_raw, network_raw, current, observed)
            observation = self.directory/'checkpoint-observation.json'; write_private(observation, proof)
            checkpoint = self.directory/'joint-checkpoint'; output = self.directory/'checkpoint-result.json'
            command = [sys.executable, str(Path(__file__).with_name('seatsurfing_joint_checkpoint_v2.py')),
                'capture','--checkpoint',str(checkpoint),'--build-report',str(self.build_report),
                '--private-key',str(Path(private_key).absolute()),'--public-key',str(self.public_key),
                '--origin','http://127.0.0.1:8080','--storage',str(self.warm['storage']),
                '--observation',str(observation),'--output',str(output)]
            try:
                result = subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=330)
            except subprocess.TimeoutExpired as error:
                (self.directory/'checkpoint.stdout').write_bytes(error.stdout or b'')
                (self.directory/'checkpoint.stderr').write_bytes(error.stderr or b'')
                raise
            (self.directory/'checkpoint.stdout').write_bytes(result.stdout)
            (self.directory/'checkpoint.stderr').write_bytes(result.stderr)
            if result.returncode or result.stdout or result.stderr: raise RuntimeError('Joint checkpoint acquisition unavailable')
            value = json.loads(output.read_text())
            if value['status'] != 'joint_checkpoint_captured_runtime_unqualified': raise RuntimeError('Unexpected joint checkpoint result')
            manifest_raw = (checkpoint/'manifest.json').read_bytes()
            if hashlib.sha256(manifest_raw).hexdigest() != value['manifest_sha256']: raise RuntimeError('Checkpoint manifest binding mismatch')
            baseline = json.loads((checkpoint/'database/baseline.json').read_text())
            if baseline['state'] != current['state']: raise RuntimeError('Dump baseline differs from full warm row evidence')
            self.lifecycle._inspect('paused')
            self.checkpoint, self.checkpoint_result = checkpoint, value
            self.phase = 'checkpoint_captured'
            report.update(status=self.phase,manifest_sha256=value['manifest_sha256'])
            return value
        except Exception as error:
            self.phase='failed'; report.update(status='checkpoint_unavailable',error_type=type(error).__name__)
            raise
        finally: write_private(self.directory/'checkpoint-stage.json',report)

    def warm_edit(self):
        if self.phase != 'checkpoint_captured': raise RuntimeError('Warm edit requires captured original checkpoint')
        self.phase='warm_edit_in_progress'
        report={'status':self.phase,'runtime_qualified':False}
        try:
            start=time.time_ns()//1000
            self.lifecycle.resume()
            edited=observe_command(self.bridge,{'requestId':'edit','operation':'edit','edit':self.edit})
            self.lifecycle.pause()
            end=time.time_ns()//1000
            after=self.snapshot('after-warm-edit')
            comparison=compare_ordinary_state(self.warm['state'],after,session_id=self.report['session_id'],
                location_id=self.warm['api_id'],window_start_us=start,window_end_us=end,edit=self.edit)
            write_private(self.directory/'warm-edit-state-comparison.json',comparison)
            # Native worker checks unchanged original credentials after its edit;
            # fresh database evidence independently verifies current identity.
            captured={**self.warm['capture'],'network':edited['network']}
            actor=self.actor('actor-after-warm-edit',captured,self.warm['storage'],self.warm['actor']['continuity'])
            self.phase='warm_edit_paused'
            self.warm_result={'native':edited,'state':after,'actor':actor,'state_comparison':comparison}
            report.update(status=self.phase,request_comparison_pending=True)
            return self.warm_result
        except Exception as error:
            self.phase='failed';report.update(status='warm_edit_unavailable',error_type=type(error).__name__)
            raise
        finally:
            write_private(self.directory/'warm-lifecycle.json',self.lifecycle.events)
            write_private(self.directory/'warm-stage.json',report)

    def restore_native_editor(self, *, private_key):
        if self.phase != 'warm_edit_paused': raise RuntimeError('Restore requires the completed original warm branch')
        self.phase='restore_native_in_progress'
        report={'status':self.phase,'runtime_qualified':False}
        try:
            self.lifecycle.resume()
            stopped=self.lifecycle.stop(self.bridge.close)
            # Retain final native trace before removing the stopped container.
            final_trace=self.bridge.artifact_directory/'final-network.json'
            final_raw=final_trace.read_bytes()
            if len(final_raw)>32*1024*1024:raise RuntimeError('Final native trace bound')
            final=json.loads(final_raw)
            if final.get('failure') is not None or final.get('pendingIds') or final.get('pendingCaptures')!=0:
                raise RuntimeError('Original worker did not retain a complete final trace')
            original=json.loads((self.directory/'checkpoint-observation.json').read_text())
            proof={**original,'browser_and_application_paused':False,'browser_and_application_stopped':True,
                   'stopped_identity':stopped['after'],'original_final_trace_sha256':hashlib.sha256(final_raw).hexdigest()}
            observation=self.directory/'native-restore-observation.json';write_private(observation,proof)
            output=self.directory/'native-restore-result.json'
            command=[sys.executable,str(Path(__file__).with_name('seatsurfing_joint_checkpoint_v2.py')),
                'restore','--checkpoint',str(self.checkpoint),'--build-report',str(self.build_report),
                '--private-key',str(Path(private_key).absolute()),'--public-key',str(self.public_key),
                '--origin','http://127.0.0.1:8080','--expected-manifest-sha256',self.checkpoint_result['manifest_sha256'],
                '--observation',str(observation),'--output',str(output)]
            try:result=subprocess.run(command,stdout=subprocess.PIPE,stderr=subprocess.PIPE,timeout=330)
            except subprocess.TimeoutExpired as error:
                (self.directory/'native-restore.stdout').write_bytes(error.stdout or b'')
                (self.directory/'native-restore.stderr').write_bytes(error.stderr or b'')
                raise
            (self.directory/'native-restore.stdout').write_bytes(result.stdout)
            (self.directory/'native-restore.stderr').write_bytes(result.stderr)
            if result.returncode or result.stdout or result.stderr:raise RuntimeError('Stopped joint restore unavailable')
            restored=json.loads(output.read_text())
            if restored['status']!='database_restored_browser_context_not_started':raise RuntimeError('Restore was not verified')
            if restored['storage_sha256']!=self.warm['capture']['storageSha256']:raise RuntimeError('Restored storage differs from original checkpoint')
            identity=self.lifecycle._inspect('stopped')
            if identity['container_ids']!=stopped['after']['container_ids']:raise RuntimeError('Stopped fixture changed during restore')
            # Both original processes are stopped, restoration verified, and the
            # old worker artifacts retained. Remove only that labelled browser.
            lifecycle_command(['docker','rm',BROWSER])
            startup_start=time.time_ns()//1000
            lifecycle_command(['docker','start',APP])
            for _ in range(90):
                app,=json.loads(lifecycle_command(['docker','inspect',APP]))
                if app['Id']!=identity['container_ids'][0] or not app['State']['Running'] or app['State'].get('Restarting'):
                    raise RuntimeError('Original application failed restart')
                health=app['State'].get('Health',{}).get('Status')
                if health=='healthy':break
                if health=='unhealthy':raise RuntimeError('Original application health failed after restore')
                time.sleep(1)
            else:raise TimeoutError('Original application readiness observation expired')
            captured=json.loads(Path(restored['storage_path']).read_text())
            values={row['name']:row['value'] for row in captured['origins'][0]['localStorage']}
            configuration=self.directory/'restored-native-config.json'
            write_private(configuration,{'mode':'verified_restoration','origin':'http://127.0.0.1:8080',
                'storagePath':str(Path(restored['storage_path']).absolute()),'storageSha256':restored['storage_sha256'],
                'nativeCredentials':{'accessToken':values['accessToken'],'refreshToken':values['refreshToken']}})
            self.original_bridge,self.original_lifecycle=self.bridge,self.lifecycle
            self.bridge=launch_native_browser(tools=self.provision['node_tools'],configuration=configuration,
                private_directory=self.directory/'restored-native',build_report=self.build_report)
            while not self.bridge.ready and not self.bridge.failed:
                try:self.bridge.await_ready(seconds=30)
                except TimeoutError:continue
            if not self.bridge.ready:raise RuntimeError('Restored native worker unavailable')
            self.lifecycle=FixtureLifecycle(self.build)
            if self.lifecycle.ids[:2]!=tuple(identity['container_ids'][:2]):raise RuntimeError('Restored application/database identities changed')
            if self.lifecycle.processes[1]!=self.original_lifecycle.processes[1]:raise RuntimeError('Database process changed during restore')
            opened=observe_command(self.bridge,{'requestId':'open','operation':'open','id':self.warm['api_id']})
            capture=observe_command(self.bridge,{'requestId':'capture','operation':'capture'})
            self.lifecycle.pause()
            startup_end=time.time_ns()//1000
            state=self.snapshot('restored-native-editor-state')
            comparison=compare_ordinary_state(self.warm['state'],state,session_id=self.report['session_id'],
                location_id=self.warm['api_id'],window_start_us=startup_start,window_end_us=startup_end)
            write_private(self.directory/'restored-native-startup-comparison.json',comparison)
            storage=self.bridge.artifact_directory/'browser-storage.json'
            actor=self.actor('actor-restored-native-editor',capture,storage,self.warm['actor']['continuity'])
            if opened['readback']!=self.warm['opened']['readback']:raise RuntimeError('Restored native readback differs from original warm editor')
            if opened['loader']['materialization']!=self.warm['opened']['loader']['materialization']:
                raise RuntimeError('Restored native editor inputs differ from original warm inputs')
            self.restored_native={'opened':opened,'capture':capture,'state':state,'actor':actor,'storage':storage}
            self.phase='restored_native_editor_paused';report.update(status=self.phase)
            return self.restored_native
        except Exception as error:
            self.phase='failed';report.update(status='native_restore_unavailable',error_type=type(error).__name__)
            raise
        finally:
            write_private(self.directory/'native-restore-stage.json',report)
            write_private(self.directory/'native-restore-lifecycle.json',self.lifecycle.events)

    def restored_native_edit(self):
        if self.phase!='restored_native_editor_paused':raise RuntimeError('Require verified restored native editor')
        self.phase='restored_native_edit_in_progress'
        report={'status':self.phase,'runtime_qualified':False}
        try:
            start=time.time_ns()//1000
            self.lifecycle.resume()
            edited=observe_command(self.bridge,{'requestId':'edit','operation':'edit','edit':self.edit})
            self.lifecycle.pause()
            end=time.time_ns()//1000
            after=self.snapshot('after-restored-native-edit')
            comparison=compare_ordinary_state(self.warm['state'],after,session_id=self.report['session_id'],
                location_id=self.warm['api_id'],window_start_us=start,window_end_us=end,edit=self.edit)
            write_private(self.directory/'restored-native-edit-state-comparison.json',comparison)
            captured={**self.restored_native['capture'],'network':edited['network']}
            actor=self.actor('actor-after-restored-native-edit',captured,self.restored_native['storage'],self.warm['actor']['continuity'])
            self.native_result={'native':edited,'state':after,'actor':actor,'state_comparison':comparison}
            self.phase='restored_native_edit_paused';report.update(status=self.phase,request_comparison_pending=True)
            return self.native_result
        except Exception as error:
            self.phase='failed';report.update(status='restored_native_edit_unavailable',error_type=type(error).__name__)
            raise
        finally:
            write_private(self.directory/'restored-native-edit-stage.json',report)
            write_private(self.directory/'restored-native-edit-lifecycle.json',self.lifecycle.events)


def build_checkpoint_observation(warm, storage_raw, network_raw, current_state, paused):
    capture=warm['capture'];actor=warm['actor'];network=capture['network']
    if capture.get('nativeStorageCapture') is not True or capture.get('browserRequestsSettled') is not True:
        raise ValueError('Original native capture evidence missing')
    if hashlib.sha256(storage_raw).hexdigest()!=capture['storageSha256'] or storage_raw.decode()!=capture['storageBytes']:
        raise ValueError('Original storage evidence mismatch')
    if hashlib.sha256(network_raw).hexdigest()!=network['traceSha256'] or json.loads(network_raw)!=network['events']:
        raise ValueError('Original network evidence mismatch')
    if network.get('pendingRequests')!=0 or network.get('pendingCaptures')!=0:
        raise ValueError('Unsettled browser evidence')
    if actor.get('status')!='actor_acquisition_and_identity_verified' or actor.get('database_acquisition_provenance_verified') is not True:
        raise ValueError('Verified actor acquisition missing')
    diagnostics=capture['diagnostics'];continuity=actor['continuity']
    for field, expected in [('accessToken','accessTokenSha256'),('refreshToken','refreshTokenSha256')]:
        if hashlib.sha256(diagnostics[field].encode()).hexdigest()!=continuity[expected]:raise ValueError('Original credential changed')
    if diagnostics['sessionStorage']!={} or diagnostics['cacheNames']!=[]:raise ValueError('Unmapped browser state')
    now_ms=time.time_ns()//1000000
    if diagnostics['expiry']<=now_ms+120000:raise ValueError('Insufficient original token lifetime')
    if not 0<=now_ms-network['observedAt']<=60000:raise ValueError('Checkpoint observation exceeded sixty seconds')
    if paused.get('state')!='paused' or current_state!=warm['state'] or current_state.get('status')!='paused_comparison_state_captured':
        raise ValueError('Original paused complete state unavailable')
    return {'native_storage_capture':True,'browser_requests_settled':True,
        'application_operations_settled':True,'settlement_scope':'observed_network_and_idle_database_under_paused_processes',
        'actor_verified':True,'token_unchanged':True,'refresh_outside_checkpoint_interval':True,
        'no_unmapped_browser_state':True,'browser_and_application_paused':True,
        'storage_sha256':capture['storageSha256'],'network_trace_sha256':network['traceSha256'],
        'paused_identity':paused,'pending_application_tasks_proven_absent':False,
        'warm_restore_equivalence_established':False}
