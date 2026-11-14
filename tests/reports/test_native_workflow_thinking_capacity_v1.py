"""SCRIPTED HTTP plus actual original workflow compiler; no model inference."""
import pytest

from scripts import diagnose_native_workflow_thinking_capacity_v1 as probe
from tests.reports.test_native_workflow_output_modes_v1 import setup, identity
from tests.optimization.test_native_workflow_designer_v1 import control
from utopia.optimization.native_numeric_designer import save


def length_reply(count, *, prompt=23862):
    return {'_envelope_override': {'done_reason': 'length', 'prompt_eval_count': prompt,
        'eval_count': count, 'message': {'role': 'assistant', 'thinking': 'SCRIPTED reasoning only', 'content': ''}}}


def prepare(tmp_path, monkeypatch, next_reply, *, old_reply=None):
    prior, calls, _ = setup(tmp_path, monkeypatch,
        [control, control, control, old_reply or length_reply(8192), next_reply])
    probe.shared.run(prior)
    # The fixture uses actual public replay but does not pretend to attest a
    # separate Git checkout; that subprocess/source binding is exercised in the
    # real retained-assay prepare/replay, not supplied by this fake backend.
    monkeypatch.setattr(probe, 'cold_replay', lambda root, source: probe.shared.replay(root))
    monkeypatch.setattr(probe, 'pinned_revision', lambda root: 'b' * 40)
    root = tmp_path / 'capacity'; root.mkdir()
    save(root / 'plan.json', probe.make_plan(prior, tmp_path / 'SCRIPTED-source', 'b' * 40))
    return root, prior, calls


def test_one_call_changes_only_output_budget_and_replays_public_compiler(tmp_path, monkeypatch):
    root, prior, calls = prepare(tmp_path, monkeypatch, identity)
    plan = probe.shared.read(root / 'plan.json'); old_payload = plan['origin']['intent']['payload']
    result = probe.run(root)
    assert result['proposal_status'] == 'submitted' and result['fresh_model_calls_upper_bound'] == 1
    assert result['new_scientist_worlds'] == result['new_scientific_losses'] == 0
    assert len(calls) == 8 and calls[-1]['options']['num_predict'] == 16384
    restored = dict(calls[-1]); restored['options'] = {**restored['options'], 'num_predict': 8192}
    assert restored == old_payload
    assert probe.replay(root) == result and len(calls) == 8
    assert probe.shared.replay(prior)['fresh_model_calls_upper_bound'] == 4
    with pytest.raises(ValueError, match='already attempted'): probe.run(root)
    assert len(calls) == 8


@pytest.mark.parametrize('unknown', [False, True])
def test_length_or_unknown_stops_without_another_call_or_salvage(tmp_path, monkeypatch, unknown):
    reply = {'_envelope_override': {'done': False}} if unknown else length_reply(16384)
    root, prior, calls = prepare(tmp_path, monkeypatch, reply)
    result = probe.run(root)
    assert result['completion_unknown'] is unknown and result['proposal_status'] == 'failed'
    assert result['status'] == ('stopped-completion-unknown' if unknown else 'closed-technical-probe-only')
    assert probe.shared.read(root / 'call/result.json')['literal_submission'] is None
    assert probe.replay(root) == result and len(calls) == 8
    with pytest.raises(ValueError, match='already attempted'): probe.run(root)
    assert len(calls) == 8


def test_measured_context_room_is_required_before_dispatch(tmp_path, monkeypatch):
    with pytest.raises(ValueError, match='measured context room'):
        prepare(tmp_path, monkeypatch, identity, old_reply=length_reply(8192, prompt=25000))
    assert not (tmp_path / 'capacity/started.json').exists()


def test_successful_prior_proposal_cannot_be_relabelled_as_capacity_failure(tmp_path, monkeypatch):
    with pytest.raises(ValueError, match='thinking-only length stop'):
        prepare(tmp_path, monkeypatch, identity, old_reply=identity)
    assert not (tmp_path / 'capacity/started.json').exists()
