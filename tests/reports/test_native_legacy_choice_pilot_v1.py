"""Pure plan and finite-dispatch contracts, not real-model feasibility."""
from copy import deepcopy
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import run_native_legacy_choice_pilot_v1 as driver
from tests.reports.test_native_longitudinal_comparison_v1 import plan, closed, sealed
from utopia.optimization.native_scientist_transport_v1 import contract
from utopia.system import SystemSpec
from utopia.system.native_legacy_choice_controls import controls
from utopia.utils.data_utils import file_sha256


def inputs(tmp_path, monkeypatch):
    original, _ = plan(tmp_path, monkeypatch)
    original.pop('content_sha256')
    original['scientist_transport'] = contract(read_seconds=900)
    original['operational_protocol'] = {'path': driver.TRANSPORT_PROTOCOL,
        'sha256': file_sha256(driver.ROOT / driver.TRANSPORT_PROTOCOL)}
    original = sealed(original)
    fixed = driver.read(driver.ROOT / driver.FIXED_RECEIPT)
    return original, closed(original), fixed


def test_three_controls_preserve_world_losses_and_exact_transport(tmp_path, monkeypatch):
    original, audit, fixed = inputs(tmp_path, monkeypatch)
    options = dict(source=original['source_commit'], origin={'SCRIPTED': True},
        observer_backend=original['observer_contract']['backend'],
        original_sources={'original_source': original['source_commit']})
    p = driver.build_plan(original, audit, fixed, **options)
    assert p['losses'] == original['losses'] and p['world']['world_conditions'] == original['world']['world_conditions']
    assert p['scientist_transport'] == contract(read_seconds=900)
    assert [j['condition'] for j in p['jobs']] == list(driver.LABELS)
    assert all(j['seed'] == 61001 for j in p['jobs'])
    expected = controls(SystemSpec.from_dict(original['reference_systems']['post-funding-cost']))
    assert [j['system'] for j in p['jobs']] == [v.to_dict() for v in expected.values()]
    assert p['budget']['native_worlds_upper_bound'] == 3 and p['budget']['designer_generation_POSTs'] == 0
    assert p['budget']['stop_after_technical_failure'] and not p['budget']['replace_failed_slots']
    assert not any(p[k] for k in ('held_out_evaluation', 'automatic_invention', 'policy_selection', 'publication_ready'))
    changed = deepcopy(original); changed['scientist_transport'] = contract(read_seconds=120)
    with pytest.raises(ValueError, match='scientist900'):
        driver.build_plan(changed, audit, fixed, **options)


@pytest.mark.parametrize('failure_at', [None, 1])
def test_public_run_consumes_all_complete_controls_or_stops_on_technical_failure_once(
        tmp_path, monkeypatch, failure_at):
    original, audit, fixed = inputs(tmp_path / 'inputs', monkeypatch)
    root = tmp_path / 'run'; root.mkdir()
    origins = [tmp_path / 'origin', tmp_path / 'fixed']
    for d in origins:
        d.mkdir(); (d / 'writer.lock').touch()
    p = driver.build_plan(original, audit, fixed, source=original['source_commit'],
        origin={'run': str(origins[0])}, observer_backend=original['observer_contract']['backend'],
        original_sources={'original_source': original['source_commit']})
    p['preceding_fixed_receipt']['run'] = str(origins[1]); p = sealed(p)
    monkeypatch.setattr(driver, 'require_plan', lambda root: p)
    monkeypatch.setattr(driver, 'require_environment', lambda: None)
    observer = SimpleNamespace(audit=lambda: sealed({'SCRIPTED': 'terminal observer'}))
    monkeypatch.setattr(driver, 'CommonContentObserver', lambda *a, **k: observer)
    calls = []
    def observe(root, p, job, observer):
        calls.append(job['condition'])
        if len(calls) - 1 == failure_at:
            raise ValueError('SCRIPTED technical unknown; never a numeric loss')
    monkeypatch.setattr(driver, 'observe', observe)
    if failure_at is None:
        driver.run(root)
        assert calls == list(driver.LABELS)
        assert driver.read(root / 'terminal.json')['status'] == 'closed'
        assert driver.read(root / 'observer-audit.json') == observer.audit()
    else:
        with pytest.raises(ValueError, match='technical unknown'):
            driver.run(root)
        assert calls == list(driver.LABELS[:2])
        end = driver.read(root / 'terminal.json')
        assert end['status'] == 'stopped' and end['completed_jobs'] == 1
    with pytest.raises(ValueError, match='no redispatch'):
        driver.run(root)
    assert len(calls) == (3 if failure_at is None else 2)


def test_retained_public_path_proof_binds_actual_httpx_and_historical_failures():
    import hashlib
    import json
    import subprocess
    from utopia.optimization.native_numeric_designer import checked
    receipt = checked(json.loads((driver.ROOT / 'research/results/native-legacy-choice-pilot-software-retention-v1.json').read_text()))
    raw = (driver.ROOT / receipt['verification_file']).read_bytes()
    assert hashlib.sha256(raw).hexdigest() == receipt['verification_file_sha256']
    value = json.loads(raw)
    assert value['source_commit'] == receipt['source_commit']
    assert value['scientist_httpx_requests'] == receipt['scientist_httpx_requests'] == 459
    assert value['all_scientist_read_headers'] == ['900'] and value['all_scientist_retry_headers'] == ['0']
    assert value['native_direction_requests'] == [0, 16, 16]
    assert value['advice_delivered_in_direction_prompts'] == [0, 0, 16]
    for name, expected in receipt['source_files'].items():
        body = subprocess.check_output(['git', 'show', receipt['source_commit'] + ':' + name], cwd=driver.ROOT)
        assert hashlib.sha256(body).hexdigest() == expected
    assert len(receipt['preserved_prior_failures']) == 2
    assert receipt['historical_upstream_closure_is_scripted_fixture']
    assert not receipt['scientific_feasibility_or_improvement_claimed']
    assert receipt['new_real_model_calls'] == 0 and not receipt['publication_ready']


def test_closure_uses_the_existing_finite_readonly_chain_not_another_scientific_run(monkeypatch):
    from scripts import finish_native_legacy_choice_pilot_v1 as finish
    captured = {}
    def invoke(args, **kwargs):
        captured.update(kwargs); return 'SCRIPTED-contract-only'
    monkeypatch.setattr(finish, 'finish', invoke)
    assert finish.run(SimpleNamespace()) == 'SCRIPTED-contract-only'
    assert captured['plan_schema'] == driver.SCHEMA + '.plan'
    assert captured['audit_module'] == 'scripts.audit_native_legacy_choice_pilot_v1'
    assert captured['writer_command'] == 'scripts.run_native_legacy_choice_pilot_v1 run'
