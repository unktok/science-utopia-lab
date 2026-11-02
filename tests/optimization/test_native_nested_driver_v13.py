"""Finite v13 orchestration guards; fixtures are not native research results."""
import fcntl
from types import SimpleNamespace

import pytest

from scripts import run_native_nested_search_v13 as driver
from utopia.optimization.native_manifest_inbox import ExternalAuthoringPending
from utopia.utils.data_utils import write_json_atomic


def campaign(records=None):
    return SimpleNamespace(binding={'unit_test_only': True},
        state={'records': records or [], 'pending': None})


def plan():
    return {'world': {'source_commit': 'unit-only', 'classification': 'scripted-not-native-results'}}


def test_zero_initial_evidence_does_not_claim_results(tmp_path):
    result = driver.summarize(tmp_path, plan(), {'a': campaign(), 'b': campaign()})
    assert result['planned_native_world_budget'] == 8
    assert result['consumed_native_slots'] == 0 and result['committed_draws'] == 0
    assert result['status'] == 'in-progress' and not result['budget_terminal']
    assert result['physical_reply_count'] == 0 and not result['claims']['live_fixed_Qwen_researchers']


def test_all_invalid_vocabularies_consume_eight_null_slots_not_eight_worlds(tmp_path):
    rows = [{'request': {'count': count}, 'generation_error': {'loss': None},
             'draws': [], 'observations': []} for count in driver.COUNTS]
    result = driver.summarize(tmp_path, plan(), {'a': campaign(rows), 'b': campaign(rows)})
    assert result['budget_terminal'] and result['status'] == 'budget-complete-with-failures'
    assert result['consumed_native_slots'] == result['technical_failures'] == 8
    assert result['complete_native_worlds'] == result['committed_draws'] == 0


def test_complete_and_failed_actual_slots_are_not_hidden_or_replaced(tmp_path):
    rows = []
    for count in driver.COUNTS:
        rows.append({'request': {'count': count}, 'generation_error': None,
            'draws': [{}] * count,
            'observations': [{'status': 'complete', 'metadata': {}, 'loss': 1.}] * count})
    a, b = campaign(rows), campaign(rows)
    result = driver.summarize(tmp_path, plan(), {'a': a, 'b': b})
    assert result['status'] == 'complete' and result['complete_native_worlds'] == 8
    b.state['records'] = [*rows[:-1], {**rows[-1], 'observations': [None]}]
    failed = driver.summarize(tmp_path, plan(), {'a': a, 'b': b})
    assert failed['status'] == 'budget-complete-with-failures'
    assert failed['complete_native_worlds'] == 7 and failed['technical_failures'] == 1
    assert failed['consumed_native_slots'] == failed['committed_draws'] == 8


def test_waiting_own_author_does_not_block_other_arm_fixed_stages(tmp_path):
    class Controller:
        def __init__(self, waiting=False):
            self.state, self.calls, self.waiting = {'records': []}, 0, waiting
        def advance(self, **kwargs):
            self.calls += 1
            assert set(kwargs) == {'simulation_factory', 'generator'}
            if self.waiting:
                raise ExternalAuthoringPending('own-exact-request', tmp_path/'request', tmp_path/'response')
            self.state['records'].append({})
    a, b = Controller(True), Controller()
    snapshots = []
    waiting = driver.advance_arms(['a', 'b'], {'a': a, 'b': b}, {'a': object(), 'b': object()},
        simulation_factory=object(), snapshot=lambda: snapshots.append(True))
    assert set(waiting) == {'a'} and a.calls == 1 and b.calls == 3 and len(snapshots) == 4


def test_previously_consumed_failed_stage_is_not_rerolled():
    class Controller:
        def __init__(self):
            self.state = {'records': [{'generation_error': {'loss': None}}]}
        def advance(self, **kwargs):
            self.state['records'].append({})
    c = Controller()
    driver.advance_arms(['a'], {'a': c}, {'a': object()}, simulation_factory=object(), snapshot=lambda: None)
    assert len(c.state['records']) == 3 and c.state['records'][0]['generation_error']['loss'] is None


def test_unexpected_external_infrastructure_failure_is_not_numeric_loss():
    class Controller:
        state = {'records': []}
        def advance(self, **kwargs):
            raise RuntimeError('unit-only external infrastructure problem')
    with pytest.raises(RuntimeError, match='infrastructure problem'):
        driver.advance_arms(['a'], {'a': Controller()}, {'a': object()},
            simulation_factory=object(), snapshot=lambda: None)


def test_exact_loss_order_and_identity_not_arbitrary_external_loss(tmp_path, monkeypatch):
    monkeypatch.setattr(driver, 'ROOT', tmp_path)
    source = driver.ROOT/'research/objectives/losses'
    from tests.optimization.test_native_adaptive_search import loss_spec
    losses = [dict(loss_spec(), id=name.removesuffix('.json')) for name in driver.LOSS_NAMES]
    for name, loss in zip(driver.LOSS_NAMES, losses):
        write_json_atomic(source/name, loss)
    paths = [source/name for name in driver.LOSS_NAMES]
    assert driver.load_preregistered_losses(paths) == losses
    with pytest.raises(ValueError, match='exact preregistered'):
        driver.load_preregistered_losses(paths[::-1])
    with pytest.raises(ValueError, match='exact preregistered'):
        driver.load_preregistered_losses([paths[0], paths[0]])


def test_writer_lock_rejected_before_model_factory(tmp_path, monkeypatch):
    monkeypatch.setattr('sys.argv', ['runner', '--output', str(tmp_path), '--data-cache', 'absent',
        '--loss', 'absent-a', '--loss', 'absent-b'])
    monkeypatch.setattr(driver.subprocess, 'check_output', lambda *a, **k: b'')
    monkeypatch.setattr(driver, 'run', lambda args: pytest.fail('lock must precede native factory'))
    with (tmp_path/'pilot-writer.lock').open('a') as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        with pytest.raises(RuntimeError, match='another nested native writer'):
            driver.main()


def test_dirty_source_rejected_before_model_or_output_creation(tmp_path, monkeypatch):
    target = tmp_path/'not-created'
    monkeypatch.setattr('sys.argv', ['runner', '--output', str(target), '--data-cache', 'absent',
        '--loss', 'absent-a', '--loss', 'absent-b'])
    monkeypatch.setattr(driver.subprocess, 'check_output', lambda *a, **k: b' M user-change\n')
    monkeypatch.setattr(driver, 'run', lambda args: pytest.fail('dirty source cannot run'))
    with pytest.raises(SystemExit):
        driver.main()
    assert not target.exists()
