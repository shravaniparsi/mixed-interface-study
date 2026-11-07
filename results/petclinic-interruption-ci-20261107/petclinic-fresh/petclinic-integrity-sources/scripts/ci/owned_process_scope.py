"""Bounded direct-child cleanup and interruption handling for CI launchers.

A confirmed direct-child exit is not proof that detached descendants exited.
Only processes created by this scope can be signalled.
"""
from contextlib import contextmanager
import os
import signal
import subprocess
import time


@contextmanager
def interruption_as_exception():
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGTERM, signal.SIGINT)}
    def interrupt(signum, frame):
        raise SystemExit(128 + signum)
    try:
        for sig in previous:
            signal.signal(sig, interrupt)
        yield
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


@contextmanager
def defer_stop_signals():
    previous = {sig: signal.getsignal(sig) for sig in (signal.SIGTERM, signal.SIGINT)}
    try:
        for sig in previous:
            signal.signal(sig, signal.SIG_IGN)
        yield
    finally:
        for sig, handler in previous.items():
            signal.signal(sig, handler)


def stop_owned_group(child, grace=5, kill_wait=2):
    """Stop a direct child launched with start_new_session=True.

    Signal its owned process group while its leader is alive. The result only
    confirms the direct child's exit; detached descendants need their own proof.
    """
    if grace <= 0 or kill_wait <= 0:
        raise ValueError('Cleanup deadlines must be positive')
    began = time.monotonic()
    record = {'pid': child.pid, 'exit_confirmed': False,
              'descendant_cleanup': 'not_established', 'signals': [], 'errors': []}
    try:
        if child.poll() is None:
            if os.getpgid(child.pid) != child.pid:
                raise ValueError('Child is not the leader of an owned process group')
            for sig, wait in ((signal.SIGTERM, grace), (signal.SIGKILL, kill_wait)):
                try:
                    os.killpg(child.pid, sig)
                    record['signals'].append(sig.name)
                except ProcessLookupError:
                    pass
                try:
                    child.wait(timeout=wait)
                    break
                except subprocess.TimeoutExpired:
                    continue
        record['exit_confirmed'] = child.poll() is not None
        record['returncode'] = child.returncode
    except ProcessLookupError:
        # The child may exit between poll and the group-identity check.
        try:
            child.wait(timeout=kill_wait)
            record['exit_confirmed'] = True
            record['returncode'] = child.returncode
        except subprocess.TimeoutExpired:
            record['errors'].append('Exit race did not resolve before deadline')
    except Exception as error:
        record['errors'].append(type(error).__name__ + ': ' + str(error))
    record['elapsed_s'] = time.monotonic() - began
    return record
