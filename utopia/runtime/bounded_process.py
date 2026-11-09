"""Wall-clock bound for a caller-owned process group, never untrusted shell."""
import math
import os
from pathlib import Path
import signal
import subprocess
import time


def run_bounded(argv, *, seconds, cwd=None, env=None):
    if (not isinstance(argv, list) or not argv or any(not isinstance(x, str) for x in argv)
            or type(seconds) not in (int, float) or not math.isfinite(seconds) or seconds <= 0):
        raise ValueError('explicit argv and finite positive wall allowance required')
    begin = time.monotonic()
    child = subprocess.Popen(argv, cwd=cwd, env=env, start_new_session=True,
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    timeout = False
    try:
        child.wait(timeout=seconds)
    except subprocess.TimeoutExpired:
        timeout = True
        # This PID is the session/process-group leader created above, not a
        # user-supplied PID or a broad server process. The model server stays up.
        try:
            os.killpg(child.pid, signal.SIGTERM)
        except ProcessLookupError:
            pass
        try:
            child.wait(timeout=1.)
        except subprocess.TimeoutExpired:
            try:
                os.killpg(child.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            child.wait(timeout=2.)
    return {'argv': argv, 'wall_allowance_seconds': seconds, 'timed_out': timeout,
            'returncode': child.returncode, 'elapsed_seconds': time.monotonic()-begin,
            'server_cancel_confirmed': False if timeout else None,
            'redispatched': False}
