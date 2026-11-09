"""Pure scheduler gates, not a live campaign or a synthetic scientific pass."""
import pytest

from scripts.run_pre_scale_completion_chain_v1 import wait_closed


def test_closure_file_does_not_allow_model_switch_while_original_writer_exists(tmp_path):
    (tmp_path/'mechanisms-complete.json').write_text('{}')
    identities=iter(['same-writer','same-writer',None]);waits=[]
    r=wait_closed(tmp_path,123,'same-writer',observe=lambda pid:next(identities),
        poll=waits.append,clock=lambda:0.)
    assert waits==[15,15] and r['original_writer_absent']
    assert r['original_process_exit_status'] is None


def test_failed_original_writer_does_not_dispatch_a_replacement(tmp_path):
    with pytest.raises(ValueError,match='without complete'):
        wait_closed(tmp_path,123,'same-writer',observe=lambda pid:None)


def test_reused_pid_is_not_a_finished_original_writer(tmp_path):
    (tmp_path/'mechanisms-complete.json').write_text('{}')
    with pytest.raises(ValueError,match='identity changed'):
        wait_closed(tmp_path,123,'same-writer',observe=lambda pid:'different-writer')


def test_finite_wait_expiry_leaves_scientific_writer_untouched(tmp_path):
    times=iter([0.,20.])
    with pytest.raises(ValueError,match='wait allowance'):
        wait_closed(tmp_path,123,'same-writer',seconds=10,observe=lambda pid:'same-writer',clock=lambda:next(times),
            poll=lambda seconds:pytest.fail('must stop at finite allowance'))
