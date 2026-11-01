"""Runner orchestration/reporting units, never native scientific evidence."""
from types import SimpleNamespace

import pytest

from scripts.run_native_objective_structure_v8 import ROOT, advance_arms, summarize, load_preregistered_losses
from utopia.optimization.native_manifest_inbox import ExternalAuthoringPending


def campaign(records=None):
    return SimpleNamespace(binding={'strategies': {'invent': {}}},
        state={'records': records or [], 'pending': None})


def test_initial_report_is_not_live_or_completed(tmp_path):
    report = summarize(tmp_path, {'world': {'source_commit': 'unit-only', 'classification': 'scripted-fixture-not-native-results'}},
        {'a': campaign(), 'b': campaign()})
    assert report['status'] == 'in-progress' and report['physical_reply_count'] == 0
    assert not report['claims']['live_fixed_Qwen_researchers']
    assert report['complete_native_worlds'] == 0


def test_terminal_generation_failures_are_not_completed_native_worlds(tmp_path):
    rows = [{'generation_error': {'loss': None}, 'draws': [], 'observations': []} for _ in range(2)]
    report = summarize(tmp_path, {'world': {'source_commit': 'unit-only', 'classification': 'scripted-fixture-not-native-results'}},
        {'a': campaign(rows), 'b': campaign(rows)})
    assert report['budget_terminal'] and report['status'] == 'budget-complete-with-failures'
    assert report['technical_failures'] == 4 and report['complete_native_worlds'] == 0


def test_only_exact_preregistered_objectives_are_accepted_before_factory_access():
    paths = [ROOT / 'research/objectives/losses' / name for name in (
        'native-joint-v5-throughput.json', 'native-joint-v5-net-reviewed-utility.json')]
    assert [v['id'] for v in load_preregistered_losses(paths)] == [p.stem for p in paths]
    with pytest.raises(ValueError, match='exact preregistered'):
        load_preregistered_losses(paths[::-1])
    with pytest.raises(ValueError, match='exact preregistered'):
        load_preregistered_losses([paths[0], paths[0]])


def test_classification_must_be_explicit_even_without_completed_native_worlds(tmp_path):
    with pytest.raises(KeyError, match='classification'):
        summarize(tmp_path, {'world': {'source_commit': 'unit-only'}}, {'a': campaign(), 'b': campaign()})


def test_pending_arm_does_not_block_other_arm_or_trigger_repeated_authoring(tmp_path):
    class Controller:
        binding = {'strategies': {'invent': {}}}
        def __init__(self, waiting=False):
            self.state = {'records': []}
            self.calls, self.waiting = 0, waiting
        def advance(self, **kwargs):
            self.calls += 1
            assert kwargs['count'] == 2
            if self.waiting:
                raise ExternalAuthoringPending('exact', tmp_path / 'request', tmp_path / 'response')
            self.state['records'].append({})
    a, b = Controller(True), Controller()
    snapshots = []
    waiting = advance_arms(['a', 'b'], {'a': a, 'b': b}, {'a': object(), 'b': object()},
        simulation_factory=object(), snapshot=lambda: snapshots.append(1))
    assert set(waiting) == {'a'} and a.calls == 1 and b.calls == 2
    assert len(snapshots) == 3


def test_resume_does_not_repeat_completed_generation():
    class Controller:
        binding = {'strategies': {'invent': {}}}
        state = {'records': [{}]}
        def advance(self, **kwargs):
            self.state['records'].append({})
    c = Controller()
    advance_arms(['a'], {'a': c}, {'a': object()}, simulation_factory=object(), snapshot=lambda: None)
    assert len(c.state['records']) == 2


def test_unexpected_exception_is_not_relabelled_as_authoring_wait_or_objective_penalty():
    class Controller:
        binding = {'strategies': {'invent': {}}}
        state = {'records': []}
        def advance(self, **kwargs):
            raise RuntimeError('unit-only unexpected infrastructure failure')
    with pytest.raises(RuntimeError, match='unexpected infrastructure'):
        advance_arms(['a'], {'a': Controller()}, {'a': object()},
            simulation_factory=object(), snapshot=lambda: None)
