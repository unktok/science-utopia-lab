"""Explicit mocked physical/calibration joins, real observer public audit API.

Not original-world integration or real model execution readiness evidence.
"""
from pathlib import Path

import pytest

from scripts import audit_native_planning_objective_loop_v1 as audit
from scripts import run_native_planning_objective_loop_v1 as driver
from scripts import finish_native_planning_objective_loop_v1 as finish
from scripts.analyze_native_open_v7 import _inventory
from tests.reports.test_native_planning_objective_loop_v1 import plan
from tests.reports.test_native_objective_instrument_audit_v1 import setup as original_setup


def setup(tmp_path, monkeypatch):
    return original_setup(tmp_path, monkeypatch, plan_factory=lambda p,m:plan(p,m)[0],
        driver_module=driver, initial_readiness=True)


def test_eight_reference_six_own_nulls_and_initial_calibration_cold_joins_twice(tmp_path, monkeypatch):
    root, p = setup(tmp_path, monkeypatch); before = _inventory(root)
    paths = [tmp_path / 'one.json', tmp_path / 'two.json']
    for path in paths: audit.worker(root, path)
    assert paths[0].read_bytes() == paths[1].read_bytes() and before == _inventory(root)
    result = driver.read(paths[0])
    assert result['schema'] == 'scienceutopia.native-planning-objective-loop-audit.v1'
    assert len(result['worlds']) == 8 and len(result['readiness']) == len(result['authoring']) == 6
    assert result['initial_readiness']['certificate']['plan']['request']['SCRIPTED'] == 'initial planning request'
    assert not result['selection']['baseline_fallback']


def test_reference_cannot_precede_its_actual_initial_readiness(tmp_path, monkeypatch):
    root, _ = setup(tmp_path, monkeypatch)
    path = next((root / 'references').glob('*/started.json')); body = driver.read(path)
    body.pop('content_sha256'); body['started_utc'] = '2026-11-11T18:00:00+00:00'
    path.unlink(); driver.save(path, body)
    with pytest.raises(ValueError, match='predates initial readiness'): audit.worker(root, tmp_path / 'no.json')


def test_initial_prototype_cannot_contain_imported_history(tmp_path, monkeypatch):
    root, _ = setup(tmp_path, monkeypatch)
    # The original helper's fake replay map is deliberately exposed only by
    # calling the currently patched pure reader; no actual campaign is edited.
    from scripts.analyze_native_autonomous_search_v14 import replay_campaign
    prototype = replay_campaign(root / 'initial-readiness/campaign', 'blackbox')
    prototype.state['pending'] = {'SCRIPTED': 'not empty'}
    with pytest.raises(ValueError, match='empty source-bound'): audit.worker(root, tmp_path / 'no.json')


def test_finish_uses_explicit_planning_schema_reader_and_original_writer(monkeypatch):
    calls = []; monkeypatch.setattr(finish, 'finish', lambda args, **kw: calls.append(kw))
    finish.run(object())
    assert calls[0]['audit_module'] == 'scripts.audit_native_planning_objective_loop_v1'
    assert calls[0]['writer_command'] == 'scripts.run_native_planning_objective_loop_v1 run'
