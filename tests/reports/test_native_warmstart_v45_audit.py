"""SCRIPTED read-only audit contracts; no models, containers or native worlds."""
from copy import deepcopy
from pathlib import Path
import subprocess
import sys
from types import ModuleType, SimpleNamespace

import pytest

from scripts import analyze_native_autonomous_search_v14 as previous
from scripts import analyze_native_warmstart_v45 as audit
from utopia.system.design_patch import digest
from utopia.utils.data_utils import write_json_atomic


def save(path, value):
    write_json_atomic(path, value, sort_keys=True, allow_nan=False)


def test_legacy_replay_passes_no_new_initialization_and_optional_bank_is_literal(tmp_path, monkeypatch):
    captured = []
    binding = {'initial_system': {}, 'loss_spec': {}, 'seeds': [42], 'world': {'source_commit': 'fixture'},
        'seed': 42, 'learning_rate': .1, 'strategies': {'scripted': {}}, 'mode': 'blackbox',
        'strategy_learning_rate': .1, 'strategy_baseline': 0., 'exploration': .1}
    class Reader:
        def __init__(self, directory, **kwargs):
            captured.append(kwargs)
    monkeypatch.setattr(previous, 'ReadOnlyAdaptive', Reader)
    monkeypatch.setattr(previous.SystemSpec, 'from_dict', lambda value: value)
    save(tmp_path / 'native-adaptive-state.json', {'binding': binding, 'records': [], 'pending': None})
    previous.replay_campaign(tmp_path, 'blackbox')
    assert 'initial_evidence' not in captured[-1]
    bank = {'scripted': {'historical_source': 'different', 'nested_literal': [1, 2]}}
    binding['initial_evidence'] = bank
    save(tmp_path / 'native-adaptive-state.json', {'binding': binding, 'records': [], 'pending': None})
    previous.replay_campaign(tmp_path, 'blackbox')
    assert captured[-1]['initial_evidence'] == bank
    assert captured[-1]['initial_evidence'] is not bank


def test_source_proof_covers_new_driver_dynamic_import_helpers_and_native_tree(tmp_path, monkeypatch):
    files = {'utopia/core.py': 'VALUE = 1\n',
        'scripts/run_native_warmstart_v45.py': 'def run():\n    from scripts import helper\n',
        'scripts/analyze_native_warmstart_v45.py': 'from scripts.helper import read\n',
        'scripts/helper.py': 'def read():\n    return 1\n',
        'research/protocols/campaigns/native-warmstart-v45-a1.md': 'SCRIPTED protocol\n',
        'research/objectives/losses/native-joint-v5-throughput.json': '{}\n',
        'research/objectives/losses/native-reviewed-production-efficiency-v13.json': '{}\n'}
    for name, body in files.items():
        path = tmp_path / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(body)
    subprocess.run(['git', 'init', '-q'], cwd=tmp_path, check=True)
    subprocess.run(['git', 'add', '.'], cwd=tmp_path, check=True)
    subprocess.run(['git', '-c', 'user.name=Scripted QA', '-c', 'user.email=qa@example.invalid',
        'commit', '-qm', 'SCRIPTED source proof fixture'], cwd=tmp_path, check=True)
    source = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=tmp_path, text=True).strip()
    monkeypatch.setattr(audit, 'ROOT', tmp_path)
    proof = audit.source_proofs(source, protocol='research/protocols/campaigns/native-warmstart-v45-a1.md')
    assert set(proof['files']) == set(files)
    (tmp_path / 'scripts/helper.py').write_text('def read():\n    return 2\n')
    with pytest.raises(ValueError, match='source differs'):
        audit.source_proofs(source, protocol='research/protocols/campaigns/native-warmstart-v45-a1.md')


@pytest.mark.parametrize('source,protocol', [('fixture', 'x'), ('a' * 40, '../protocol.md'),
    ('A' * 40, 'research/protocols/campaigns/native-warmstart-v45-a1.md')])
def test_source_proof_has_no_fixture_or_path_escape_bypass(source, protocol):
    with pytest.raises(ValueError):
        audit.source_proofs(source, protocol=protocol)


def test_raw_mutation_is_detected_even_when_inner_audit_fails(tmp_path, monkeypatch):
    save(tmp_path / 'raw.json', {'unchanged': True})
    def bad(*args, **kwargs):
        save(tmp_path / 'raw.json', {'changed': True})
        raise RuntimeError('SCRIPTED failure')
    monkeypatch.setattr(audit, '_analyze', bad)
    with pytest.raises(ValueError, match='evidence changed'):
        audit.analyze(tmp_path, expected_source='a' * 40)


def scripted_setup(root, monkeypatch):
    """Only orchestration is scripted; helper truth is tested in its own suite."""
    bank = {'content_sha256': 'historical-bank', 'source_audit': {'source_commit': 'old-source'}}
    bindings = {name: {'initial_evidence': deepcopy(bank), 'world': {'source_commit': 'new-source'}} for name in audit.ARMS}
    plan = {'classification': 'SCRIPTED-AUDIT-ORCHESTRATION-NOT-SCIENTIFIC',
        'content_sha256': 'scripted-plan',
        'campaign_bindings': bindings, 'losses': {name: {'id': name} for name in audit.ARMS},
        'world_binding': {'source_commit': 'new-source'}, 'initial_system': {}, 'experiment': {},
        'designer_provider_binding': {}, 'designer': {'max_steps': 16, 'max_tokens': 8192}}
    save(root / 'writer.ended.json', {'status': 'SCRIPTED terminal'})
    monkeypatch.setattr(audit, '_writer_and_progress', lambda *a: {'started': {}, 'ended': {}, 'progress': {}})
    monkeypatch.setattr(audit, '_role_proofs', lambda *a: {'scientific_generation': False})
    monkeypatch.setattr(audit, '_certificate_proof', lambda *a: {'new_model_calls_during_replay': 0})
    monkeypatch.setattr(audit, '_plan_and_bank', lambda *a: (plan, bank, {'status': 'SCRIPTED'}))
    monkeypatch.setattr(audit, 'replay_campaign', lambda path, method: SimpleNamespace(
        binding=bindings[path.parent.name]))
    def native(directory, **kwargs):
        return {'observations': [{'status': 'technical-failure', 'loss': None}],
            'records': [], 'pending': None, 'terminal': True, 'consumed_native_slots': 1,
            'technical_failures': 1, 'physical_native_worlds': 0, 'physical_world_directory_count': 0,
            'physical_researcher_responses': 0, 'completed_researcher_responses': 0,
            'physical_wire_requests': 0, 'recorded_code_executions_including_partial': 0,
            'completed_researcher_model_call_seconds': 0., 'physical_response_caches': []}
    monkeypatch.setattr(audit, 'audit_native_campaign', native)
    monkeypatch.setattr(audit, 'audit_authoring', lambda *a, **k: {'generations': 1,
        'dispatch_intents': 2, 'completed_step_receipts': 2, 'recorded_POST_attempts': 0,
        'known_HTTP_responses': 0, 'known_designer_responses': 2, 'interrupted_response_unknown': 0,
        'valid_finished_generations': 0, 'proofs': []})
    module = ModuleType('utopia.optimization.native_initial_evidence')
    module.objective_view = lambda bank, loss: {'selection': {'loss': -7. if loss['id'] == 'throughput' else -11.8,
        'selected_observation_id': 'historical', 'tied_observation_ids': ['historical', 'same-source-different-run']}}
    monkeypatch.setitem(sys.modules, module.__name__, module)
    return plan, bank


def test_failed_new_slots_cannot_be_reported_as_historical_success_and_audit_is_repeatable(tmp_path, monkeypatch):
    scripted_setup(tmp_path, monkeypatch)
    before = audit._inventory(tmp_path)
    first = audit.analyze(tmp_path, expected_source='a' * 40)
    assert first == audit.analyze(tmp_path, expected_source='a' * 40)
    assert audit._inventory(tmp_path) == before
    assert first['status'] == 'budget-complete-with-failures'
    assert first['consumed_native_slots'] == first['technical_failures'] == 2
    assert first['physical_native_worlds'] == first['physical_researcher_responses'] == 0
    assert first['new_model_calls_during_audit'] == first['new_code_executions_during_audit'] == 0
    for value in first['comparisons'].values():
        assert value['new_best_loss'] is None and not value['historical_best_updated']
        assert value['observed_improvement_over_historical'] is None
        assert len(value['historical_initial_selection']['tied_observation_ids']) == 2
    assert first['content_sha256'] == digest({k: v for k, v in first.items() if k != 'content_sha256'})


@pytest.mark.parametrize('extra', ['responses.sqlite', 'generation-' + 'b' * 64])
def test_undeclared_scientist_cache_or_authoring_generation_is_rejected(tmp_path, monkeypatch, extra):
    scripted_setup(tmp_path, monkeypatch)
    if extra.startswith('generation-'):
        (tmp_path / 'rogue' / extra).mkdir(parents=True)
    else:
        save(tmp_path / 'rogue' / extra, {'SCRIPTED': 'not an actual response database'})
    with pytest.raises(ValueError, match='unaccounted'):
        audit.analyze(tmp_path, expected_source='a' * 40)


def test_terminal_receipt_is_required(tmp_path, monkeypatch):
    monkeypatch.setattr(audit, '_plan_and_bank', lambda *a: ({}, {}, {}))
    with pytest.raises(ValueError, match='ended writer'):
        audit.analyze(tmp_path, expected_source='a' * 40)


def test_two_slots_cannot_be_silently_refilled(tmp_path, monkeypatch):
    scripted_setup(tmp_path, monkeypatch)
    original = audit.audit_native_campaign
    def refilled(*a, **kwargs):
        result = original(*a, **kwargs)
        result['consumed_native_slots'] = 2
        return result
    monkeypatch.setattr(audit, 'audit_native_campaign', refilled)
    with pytest.raises(ValueError, match='exactly one terminal attempt'):
        audit.analyze(tmp_path, expected_source='a' * 40)


def terminal_fixture(root):
    plan = {'source_commit': 'a' * 40, 'content_sha256': 'pinned-plan'}
    started = {'schema': audit.PLAN_SCHEMA + '.writer', 'source_commit': plan['source_commit'],
        'action': 'run', 'pid': 123, 'argv': ['SCRIPTED'],
        'started_utc': '2000-01-01T00:00:00+00:00', 'status': 'started',
        'environment': {'PYTHONHASHSEED': '42'}}
    ended = {**deepcopy(started), 'status': 'exited', 'exit_code': 0,
        'ended_utc': '2000-01-01T00:00:01+00:00'}
    runs = {name: {'observations': [{'status': 'technical-failure', 'loss': None}]} for name in audit.ARMS}
    progress = {'schema': audit.PLAN_SCHEMA + '.progress', 'source_commit': plan['source_commit'],
        'plan_sha256': plan['content_sha256'],
        'arms': {name: {'consumed_slots': 1, 'pending': False, 'status': 'technical-failure', 'loss': None}
            for name in audit.ARMS}, 'counts': {'complete': 0, 'technical-failure': 2, 'generation-failure': 0},
        'terminal': True, 'consumed_native_slots': 2, 'status': 'budget-complete-with-failures'}
    progress['content_sha256'] = digest(progress)
    save(root / 'writer.started.json', started)
    save(root / 'writer.ended.json', ended)
    save(root / 'progress.json', progress)
    return plan, runs, started, ended, progress


def test_terminal_progress_and_matching_writer_are_exactly_replayed(tmp_path):
    plan, runs, started, ended, progress = terminal_fixture(tmp_path)
    assert audit._writer_and_progress(tmp_path, plan, runs) == {
        'started': started, 'ended': ended, 'progress': progress}


@pytest.mark.parametrize('mutation', ['loss', 'replenish', 'counts', 'source', 'aborted', 'old-writer', 'clock'])
def test_rehashed_progress_and_writer_tampering_is_rejected(tmp_path, mutation):
    plan, runs, started, ended, progress = terminal_fixture(tmp_path)
    if mutation == 'loss':
        progress['arms']['efficiency']['loss'] = 0.
    elif mutation == 'replenish':
        progress['arms']['efficiency']['consumed_slots'] = 2
    elif mutation == 'counts':
        progress['counts']['complete'] = 2
    elif mutation == 'source':
        ended['source_commit'] = 'b' * 40
    elif mutation == 'aborted':
        ended['status'] = 'aborted'
    elif mutation == 'old-writer':
        ended['pid'] = 122
    else:
        ended['ended_utc'] = '1999-01-01T00:00:00+00:00'
    progress['content_sha256'] = digest({k: v for k, v in progress.items() if k != 'content_sha256'})
    save(tmp_path / 'progress.json', progress)
    save(tmp_path / 'writer.ended.json', ended)
    with pytest.raises(ValueError):
        audit._writer_and_progress(tmp_path, plan, runs)
