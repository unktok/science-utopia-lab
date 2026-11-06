"""Cleanup lifecycle regressions; mocked clients never run authored code."""
import io
import subprocess

import pytest

from utopia.system import code_mechanisms as m


class Client:
    def __init__(self, returncode, *, wait_error=None, kill_error=None):
        self.returncode, self.wait_error, self.kill_error = returncode, wait_error, kill_error
        self.stdout, self.stderr = io.BytesIO(), io.BytesIO()
        self.killed = self.waited = False

    def poll(self):
        return self.returncode

    def kill(self):
        self.killed = True
        if self.kill_error:
            raise self.kill_error
        self.returncode = -9

    def wait(self):
        self.waited = True
        if self.wait_error:
            raise self.wait_error
        return self.returncode


@pytest.fixture
def executor():
    result = object.__new__(m.DockerCodeExecutor)
    result.docker = '/SCRIPTED/docker'
    return result


def test_successful_auto_removed_client_has_no_redundant_daemon_cleanup(executor, monkeypatch):
    def forbidden(*args, **kwargs):
        raise subprocess.TimeoutExpired('SCRIPTED redundant rm must never be called', 10)
    monkeypatch.setattr(m.subprocess, 'run', forbidden)
    process = Client(0)
    executor._cleanup_process(process, 'utopia-code-SCRIPTED-exact')
    assert process.waited and not process.killed
    assert process.stdout.closed and process.stderr.closed


@pytest.mark.parametrize('returncode', [None, 1, -9])
def test_live_or_unsuccessful_client_keeps_bounded_exact_name_cleanup(executor, monkeypatch, returncode):
    calls = []
    monkeypatch.setattr(m.subprocess, 'run', lambda command, **kw: calls.append((command, kw)))
    process = Client(returncode)
    executor._cleanup_process(process, 'utopia-code-SCRIPTED-exact')
    assert calls == [(['/SCRIPTED/docker', 'rm', '-f', 'utopia-code-SCRIPTED-exact'],
        {'capture_output': True, 'timeout': 10})]
    assert process.killed is (returncode is None) and process.waited
    assert process.stdout.closed and process.stderr.closed


@pytest.mark.parametrize('error', [subprocess.TimeoutExpired('SCRIPTED rm', 10), OSError('SCRIPTED daemon'), KeyboardInterrupt()])
def test_failed_daemon_cleanup_still_kills_reaps_closes_and_propagates(executor, monkeypatch, error):
    def failed(*args, **kwargs):
        raise error
    monkeypatch.setattr(m.subprocess, 'run', failed)
    process = Client(None)
    with pytest.raises(type(error)) as raised:
        executor._cleanup_process(process, 'utopia-code-SCRIPTED-exact')
    assert raised.value is error
    assert process.killed and process.waited and process.stdout.closed and process.stderr.closed


@pytest.mark.parametrize('kind', ['kill', 'wait'])
def test_local_cleanup_errors_cannot_leak_open_pipes(executor, monkeypatch, kind):
    monkeypatch.setattr(m.subprocess, 'run', lambda *a, **k: None)
    error = OSError('SCRIPTED local cleanup')
    process = Client(None, **{kind + '_error': error})
    with pytest.raises(OSError):
        executor._cleanup_process(process, 'utopia-code-SCRIPTED-exact')
    assert process.stdout.closed and process.stderr.closed
