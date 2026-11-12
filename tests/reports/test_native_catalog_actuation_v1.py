"""Explicit SCRIPTED controller/origin tests, not scientific observations."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import run_native_catalog_actuation_v1 as driver
from scripts import finish_native_catalog_actuation_v1 as finish
from scripts import finish_native_catalog_readouts_v1 as readouts
from tests.reports.test_native_capacity_objective_loop_v1 import plan as original_plan
from utopia.optimization.native_bounded_staged_designer import CompletionUnknown
from utopia.system.design_patch import clone, digest


def seal(value):
    value.pop('content_sha256', None); value['content_sha256'] = digest(value); return value


def evidence(tmp_path, monkeypatch, image_override=None):
    original = original_plan(tmp_path / 'inputs', monkeypatch, image_override=image_override)
    audit = seal({'SCRIPTED': 'original development audit is mocked, not science'})
    p = seal(driver.build_plan(original, audit, source='e' * 40, origin={'run': str(tmp_path / 'origin')}))
    return original, audit, p


def test_common_authority_literal_anchor_catalog_native_laws_and_no_loss_gate(tmp_path, monkeypatch):
    original, _, p = evidence(tmp_path, monkeypatch)
    assert p['world']['world_conditions'] == original['world']['world_conditions']
    assert p['losses'] == original['losses'] and p['development_seed_reused']
    assert not p['held_out_evaluation'] and not p['automatic_invention'] and not p['policy_selection']
    assert not p['measurement_contract']['adoption_constraint']
    assert p['anchor'] == original['reference_systems']['reviewed-all-reserve-proximity']
    assert len(p['jobs']) == 3 and p['budget']['designer_generation_POSTs'] == p['budget']['critic_POSTs'] == 0
    assert p['budget']['world_wall_seconds'] == 7200 and not p['budget']['replace_failed_slots']
    systems = [clone(j['system']) for j in p['jobs']]
    for system in systems:
        node = next(n for n in system['mechanisms'] if n['mechanism_id'] == 'developer-catalog-agenda')
        node['parameters'].pop('actuation')
    assert systems[0] == systems[1] == systems[2]


@pytest.mark.parametrize('change', ['source', 'world', 'anchor', 'instrument', 'constraint'])
def test_world_anchor_or_measurement_changes_fail_before_dispatch(tmp_path, monkeypatch, change):
    original, audit, p = evidence(tmp_path, monkeypatch); source = 'e' * 40
    if change == 'source': source = 'bad'
    elif change == 'world': original['world']['world_conditions']['papers_per_project'] = 1
    elif change == 'anchor': original['reference_systems']['reviewed-all-reserve-proximity']['version'] += 1
    elif change == 'instrument': original['measurement_contract']['instrument_sha256'] = '0' * 64
    else: original['measurement_contract']['adoption_constraint'] = True
    with pytest.raises(ValueError): driver.build_plan(original, audit, source=source, origin=p['origin'])


def setup(tmp_path, monkeypatch):
    _, _, p = evidence(tmp_path, monkeypatch)
    root = tmp_path / 'run'; root.mkdir(); origin = Path(p['origin']['run']); origin.mkdir()
    (origin / 'writer.lock').touch()
    monkeypatch.setattr(driver, 'require_environment', lambda: None)
    monkeypatch.setattr(driver, 'require_plan', lambda root: p)
    return root, p


def test_terminal_nulls_are_not_refilled_and_study_cannot_be_redispatched(tmp_path, monkeypatch):
    root, p = setup(tmp_path, monkeypatch); calls = []
    def observe(root, p, job):
        calls.append(job['condition'])
        driver.save(root / 'controls' / job['identity'] / 'observation.json', {'status': 'failed', 'SCRIPTED': True})
    monkeypatch.setattr(driver, 'observe', observe); driver.run(root)
    assert calls == list(driver.MODES) and driver.read(root / 'terminal.json')['completed_jobs'] == 3
    assert driver.read(root / 'terminal.json')['status'] == 'closed'
    with pytest.raises(ValueError, match='consumed'): driver.run(root)


def test_unknown_dispatch_stops_all_later_jobs(tmp_path, monkeypatch):
    root, _ = setup(tmp_path, monkeypatch); calls = []
    def observe(*args): calls.append(1); raise CompletionUnknown('SCRIPTED uncertain dispatch')
    monkeypatch.setattr(driver, 'observe', observe)
    with pytest.raises(CompletionUnknown): driver.run(root)
    assert calls == [1] and driver.read(root / 'terminal.json')['status'] == 'stopped'
    assert driver.read(root / 'terminal.json')['completed_jobs'] == 0


def test_saved_plan_reconstructs_all_actuation_and_catalog_parameters(tmp_path, monkeypatch):
    original, audit, p = evidence(tmp_path, monkeypatch)
    monkeypatch.setattr(driver, 'origin_evidence', lambda origin: (original, audit))
    monkeypatch.setattr(driver, 'pinned_revision', lambda root: p['source_commit'])
    driver.save(tmp_path / 'plan.json', {k: v for k, v in p.items() if k != 'content_sha256'})
    assert driver.require_plan(tmp_path) == p
    p['jobs'][0]['condition'] = 'project'; seal(p)
    other = tmp_path / 'changed'; driver.save(other / 'plan.json', {k: v for k, v in p.items() if k != 'content_sha256'})
    with pytest.raises(ValueError, match='reconstruction'): driver.require_plan(other)


def test_finish_connects_original_reader_and_writer_without_new_inference(monkeypatch):
    calls = []
    monkeypatch.setattr(finish, 'finish', lambda args, **kw: calls.append(kw))
    finish.run(SimpleNamespace())
    assert calls[0]['audit_module'] == 'scripts.audit_native_catalog_actuation_v1'
    assert calls[0]['writer_command'] == 'scripts.run_native_catalog_actuation_v1 run'


@pytest.mark.parametrize('kind', ['choices', 'effects', 'requests'])
def test_readout_waits_for_actual_original_closure_and_explicit_scope(tmp_path, monkeypatch, kind):
    calls = []
    monkeypatch.setattr(readouts, 'finish', lambda args, **kw: calls.append(kw))
    readouts.run(SimpleNamespace(kind=kind, frozen_source=tmp_path))
    assert calls[0]['preceding_schema'] == 'scienceutopia.native-catalog-actuation-finish.v1'
    assert calls[0]['continuation_schema'] == 'scienceutopia.native-catalog-' + kind + '-finish.v1'
    if kind == 'effects': assert 'catalog-actuation-controls' in calls[0]['report_extra_arguments']
