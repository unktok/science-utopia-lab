"""Finite scheduling fixtures, no process control, real waiting or heavy QA."""
import pytest

from scripts.wait_native_workflow_transport_qa_v3 import wait_window


def check(identities, loads, *, seconds=180):
    now = [0]; rows = []
    ids, cpu = iter(identities), iter(loads)
    result = wait_window(123, 'original', ceiling=200, maximum_seconds=seconds,
        observe=lambda pid: next(ids), cpu=lambda: next(cpu), clock=lambda: now[0],
        poll=lambda value: now.__setitem__(0, now[0] + value), retain=rows.append)
    return result, rows


def test_live_inference_blocks_even_low_cpu_and_two_clean_observations_are_required():
    r, rows = check(['original', None, None], [10, 150, 125])
    assert r['checks'] == 3 and r['elapsed_seconds'] == 60
    assert [r['consecutive_ready_observations'] for r in rows] == [0, 1, 2]
    assert r['exclusive_resource_lease_proved'] is False


def test_high_host_cpu_breaks_the_resource_window_even_after_known_pid_disappears():
    r, rows = check([None] * 4, [100, 700, 100, 100])
    assert [r['consecutive_ready_observations'] for r in rows] == [1, 0, 1, 2]


def test_reused_pid_does_not_authorize_qa():
    with pytest.raises(ValueError, match='reused'):
        check(['different process'], [0])


def test_observation_error_is_not_converted_into_absence_or_idle():
    def failed(pid): raise OSError('SCRIPTED observer unavailable')
    with pytest.raises(OSError):
        wait_window(123, 'original', ceiling=200, maximum_seconds=30, observe=failed,
            cpu=lambda: 0, poll=lambda v: pytest.fail('do not dispatch or wait on an assumed absence'))


def test_finite_wait_exhaustion_never_starts_another_stage():
    with pytest.raises(TimeoutError, match='external work left untouched'):
        check(['original'] * 3, [500] * 3, seconds=30)


@pytest.mark.parametrize('load', [float('nan'), float('inf'), -1, None, True])
def test_bad_cpu_observation_is_not_a_zero_load(load):
    with pytest.raises(ValueError, match='CPU measurement'):
        check([None], [load])
