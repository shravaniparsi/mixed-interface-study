#!/usr/bin/env python3
"""Private bounded JSON-lines transport for the SeatSurfing native ordinary browser worker.

No Docker provisioning, job dispatch or scientific classification. A read timeout
leaves the same pending command/process intact; callers may observe it again
within its original deadline, never resend it or silently replace the worker.
"""
import hashlib
import json
from pathlib import Path
import os
import re
import selectors
import subprocess
import time


class BrowserBridge:
    def __init__(self, argv, private_directory, artifact_directory, mode):
        if mode not in ('native_login', 'verified_restoration'):
            raise ValueError('Unregistered worker mode')
        self.mode = mode
        self.artifact_directory = Path(artifact_directory).absolute()
        self.directory = Path(private_directory).resolve()
        self.directory.mkdir(mode=0o700, exist_ok=False)
        self.stderr = (self.directory / 'worker.stderr').open('xb')
        self.stdout = (self.directory / 'worker.stdout').open('xb')
        self.process = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=self.stderr)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.process.stdout, selectors.EVENT_READ)
        self.buffer = bytearray()
        self.used_ids = set()
        self.pending = None
        self.ready = False
        self.failed = False
        self.closed = False
        self.total_bytes = 0
        self.startup_deadline = time.monotonic() + 45
        self.save_status('starting')

    def save_status(self, status):
        item = {'status': status, 'pid': self.process.pid, 'exit_code': self.process.poll(),
                'pending_request': self.pending['id'] if self.pending else None,
                'completed_or_sent_ids': sorted(self.used_ids), 'received_bytes': self.total_bytes}
        (self.directory / 'transport-status.json').write_text(json.dumps(item, indent=2) + '\n')

    def read_message(self, seconds):
        deadline = time.monotonic() + seconds
        while True:
            if b'\n' in self.buffer:
                line, _, rest = self.buffer.partition(b'\n')
                self.buffer = bytearray(rest)
                if len(line) > 2 * 1024 * 1024:
                    raise ValueError('Worker response line exceeds bound')
                try:
                    result = json.loads(line)
                except (UnicodeError, json.JSONDecodeError):
                    raise ValueError('Malformed worker response; raw evidence retained') from None
                if not isinstance(result, dict):
                    raise ValueError('Worker response must be an object')
                return result
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError('Observation expired; same worker/command remains pending')
            if not self.selector.select(remaining):
                raise TimeoutError('Observation expired; same worker/command remains pending')
            data = os.read(self.process.stdout.fileno(), 65536)
            if not data:
                raise EOFError('Worker stdout closed; raw evidence retained')
            self.stdout.write(data); self.stdout.flush()
            self.total_bytes += len(data); self.buffer.extend(data)
            if self.total_bytes > 16 * 1024 * 1024 or len(self.buffer) > 2 * 1024 * 1024:
                raise ValueError('Worker output bound exceeded')

    def await_ready(self, seconds=45):
        if self.ready or self.closed:
            raise ValueError('Worker startup may only complete once')
        remaining = self.startup_deadline - time.monotonic()
        if remaining <= 0 or self.failed:
            self.failed = True; self.save_status('startup_deadline_expired')
            raise TimeoutError('Original worker startup deadline expired')
        try:
            result = self.read_message(min(seconds, remaining))
            if result != {'status': 'ready', 'mode': self.mode, 'browserVersion': '151.0.7922.34', 'runtimeQualified': False}:
                raise ValueError('Unexpected worker startup identity')
            self.ready = True
            self.save_status('ready')
            return result
        except TimeoutError:
            self.save_status('startup_observation_pending')
            raise
        except Exception:
            self.failed = True; self.save_status('startup_failed'); raise

    def send(self, command, command_seconds=90, observe_seconds=30):
        if not self.ready or self.closed or self.failed or self.pending is not None:
            raise ValueError('Worker is not ready for a new command')
        identity = command.get('requestId')
        if not isinstance(identity, str) or not re.fullmatch(r'[a-z0-9-]{1,64}', identity) or identity in self.used_ids:
            raise ValueError('Missing, malformed or reused request ID')
        if len(self.used_ids) >= 6 or not 0 < command_seconds <= 90:
            raise ValueError('Worker command count/time bound')
        raw = (json.dumps(command, separators=(',', ':')) + '\n').encode()
        if len(raw) > 65536:
            raise ValueError('Worker command byte bound')
        if self.process.poll() is not None:
            raise EOFError('Worker exited before command; no restart')
        self.used_ids.add(identity)
        self.pending = {'id': identity, 'deadline': time.monotonic() + command_seconds}
        (self.directory / f'{identity}.request.json').write_bytes(raw)
        self.save_status('command_pending')
        try:
            self.process.stdin.write(raw); self.process.stdin.flush()
        except Exception:
            self.failed = True; self.save_status('command_write_failed'); raise
        return self.observe_pending(observe_seconds)

    def observe_pending(self, seconds=30):
        if self.pending is None or self.closed or self.failed:
            raise ValueError('No live pending command to observe')
        remaining = self.pending['deadline'] - time.monotonic()
        if remaining <= 0:
            self.failed = True; self.save_status('command_deadline_expired')
            raise TimeoutError('Original command deadline expired; no resend or replacement')
        try:
            result = self.read_message(min(seconds, remaining))
            if result.get('requestId') != self.pending['id'] or result.get('status') not in ('completed', 'failed'):
                raise ValueError('Worker result identity/status mismatch')
            (self.directory / f"{self.pending['id']}.response.json").write_text(json.dumps(result) + '\n')
            if result['status'] == 'failed':
                raise RuntimeError('Worker reported command failure; private evidence retained')
            artifact = self.read_artifact(result, self.pending['id'])
            self.pending = None
            self.save_status('ready')
            return artifact
        except TimeoutError:
            self.save_status('command_observation_pending')
            raise
        except Exception:
            self.failed = True; self.save_status('worker_command_failed'); raise

    def read_artifact(self, message, identity):
        artifact = message.get('artifact')
        if not isinstance(artifact, dict) or set(artifact) != {'file', 'sha256'}:
            raise ValueError('Missing exact private artifact identity')
        if artifact['file'] != identity + '-result.json' or not re.fullmatch(r'[a-f0-9]{64}', artifact.get('sha256', '')):
            raise ValueError('Unexpected artifact name/hash')
        path = self.artifact_directory / artifact['file']
        if self.artifact_directory.is_symlink() or path.is_symlink() or not path.is_file():
            raise ValueError('Artifact must be a regular private file')
        if path.resolve().parent != self.artifact_directory.resolve():
            raise ValueError('Artifact escaped private directory')
        if path.stat().st_size > 32 * 1024 * 1024:
            raise ValueError('Private result artifact byte bound')
        raw = path.read_bytes()
        if hashlib.sha256(raw).hexdigest() != artifact['sha256']:
            raise ValueError('Private artifact hash mismatch')
        result = json.loads(raw)
        if not isinstance(result, dict):
            raise ValueError('Private worker result must be an object')
        return result

    def close(self):
        """Explicit final cleanup only. Parent owns removal of its Docker container."""
        if self.closed:
            return
        self.closed = True
        try:
            self.process.stdin.close()
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.terminate()
                try: self.process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self.process.kill(); self.process.wait(timeout=5)
            self.save_status('closed')
        finally:
            self.selector.close()
            self.process.stdout.close()
            self.stdout.close(); self.stderr.close()
