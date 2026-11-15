"""Empty publication ABI, including the retained actual authored counterexample.

These are consumer unit checks, not reruns or repairs of the scientific policy.
The actual source/context were separately replayed once inside Docker.
"""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from utopia.optimization.native_numeric_designer import checked
from utopia.system.native_kernel import NativeScienceKernel
from utopia.system.model import ChannelKind
from utopia.system.runtime import DeliveredValue, GraphRuntimeError


def empty_kernel():
    kernel = NativeScienceKernel.__new__(NativeScienceKernel)
    kernel._simulation = SimpleNamespace(conference_system=SimpleNamespace(
        conferences=[SimpleNamespace(conference_id='actual-conference',
            submitted_papers=[], decisions={'accept': [], 'reject': []})]))
    return kernel


def context(payloads):
    # The consumer receives delivered inputs, not producer MechanismValues.
    return SimpleNamespace(inputs={'decisions': tuple(DeliveredValue(
        channel=ChannelKind.DECISION, artifact_type='native-paper-decision', payload=p,
        actor_ids=(), artifact_ids=(), lineage_event_ids=(), source_mechanism='authored.selection',
        source_port='decisions', emitted_period=1, available_period=1) for p in payloads)})


def test_exact_empty_marker_completes_no_paper_cycle_without_mutation():
    payloads = [{'empty_cycle': True}]
    before = deepcopy(payloads)
    empty_kernel()._apply_decisions(context(payloads))
    assert payloads == before


@pytest.mark.parametrize('payloads', [[], [{'empty_cycle': False}],
    [{'empty_cycle': True, 'decision': 'accept'}],
    # Actual longitudinal parent-trajectory U1: a score on no paper is not
    # an accepted-paper observation or a reason to repair the author's output.
    [{'empty_cycle': True, 'final_score': 10.0}],
    # Actual longitudinal scalar T2 returns an already wrapped decision and
    # wraps it a second time; the consumer must not silently unwrap it.
    [{'payload': {'empty_cycle': True}}],
    [{'empty_cycle': True}, {'empty_cycle': True}]])
def test_other_empty_batches_fail_without_becoming_an_acceptance_or_loss(payloads):
    before = deepcopy(payloads)
    with pytest.raises(GraphRuntimeError, match='empty native cycle requires an explicit empty decision batch'):
        empty_kernel()._apply_decisions(context(payloads))
    assert payloads == before


def test_retained_actual_counterexample_reaches_the_identical_consumer_error():
    root = Path(__file__).resolve().parents[2]
    diagnostic = checked(json.loads((root / 'research/results/native-parent-empty-cycle-diagnostic-v1.json').read_text()))
    assert diagnostic['cold_sandbox_result_matches_original']
    assert diagnostic['submitted_counts'] == [0] and diagnostic['year'] == 1
    assert not diagnostic['generated_source_repaired'] and diagnostic['new_native_worlds'] == 0
    payloads = [value['payload'] for value in diagnostic['actual_decisions']]
    with pytest.raises(GraphRuntimeError) as error:
        empty_kernel()._apply_decisions(context(payloads))
    assert str(error.value) == diagnostic['consumer_failure_reproduced']['error']


def test_double_wrapped_real_paper_is_not_silently_repaired_either():
    kernel = NativeScienceKernel.__new__(NativeScienceKernel)
    kernel._simulation = SimpleNamespace(conference_system=SimpleNamespace(
        conferences=[SimpleNamespace(conference_id='actual-conference',
            submitted_papers=[{'id': 'actual-paper'}],
            decisions={'accept': [], 'reject': []})]))
    kernel.spec = SimpleNamespace(mechanisms=[])
    payloads = [{'payload': {'paper_id': 'actual-paper', 'conference_id': 'actual-conference',
        'decision': 'accept', 'final_score': 0.0}}]
    before = deepcopy(payloads)
    with pytest.raises(GraphRuntimeError, match='cover exactly the real submitted paper identities'):
        kernel._apply_decisions(context(payloads))
    assert payloads == before
