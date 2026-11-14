"""Prospective operator profile, not a new institution or scientific result."""
from pathlib import Path
import sqlite3
from types import SimpleNamespace
import json

import pytest

from scripts import run_native_workflow_objective_loop_v1 as driver
from tests.reports.test_native_workflow_objective_loop_v1 import setup
from utopia.optimization import native_scientist_transport_v1 as transport
from utopia.optimization.native_numeric_designer import save
from utopia.system.design_patch import clone


def plans(tmp_path, monkeypatch):
    old, original, audit, sources = setup(tmp_path, monkeypatch)
    new = driver.build_plan(original, audit, source=old['source_commit'], origin=old['origin'],
        backend=old['backend'], observer_backend=old['observer_contract']['backend'],
        prerequisite=old['prerequisite'], sources=sources, scientist_transport=transport.contract(read_seconds=900))
    return old, new, original, audit, sources


def test_legacy_plan_shape_and_science_stay_literal_with_explicit_operational_addition(tmp_path, monkeypatch):
    old, new, original, audit, sources = plans(tmp_path, monkeypatch)
    assert {k: v for k, v in new.items() if k not in ('scientist_transport', 'operational_protocol')} == old
    assert 'scientist_transport' not in old
    assert new['operational_protocol']['path'] == transport.PROTOCOL
    root = tmp_path / 'plan'; save(root / 'plan.json', new)
    monkeypatch.setattr(driver, 'pinned_revision', lambda root: new['source_commit'])
    monkeypatch.setattr(driver, 'origin_evidence', lambda origin: (original, audit))
    monkeypatch.setattr(driver, 'native_sources', lambda source: sources)
    monkeypatch.setattr(driver, 'prerequisite_binding', lambda path: new['prerequisite'])
    assert driver.require_plan(root) == driver.read(root / 'plan.json')
    changed = clone(new); changed['scientist_transport']['http_timeout_seconds']['read'] = 600
    other = tmp_path / 'changed'; save(other / 'plan.json', changed)
    with pytest.raises(ValueError, match='declared900s'):
        driver.require_plan(other)


def test_actual_reference_and_search_factory_router_selects_only_explicit_profile(tmp_path, monkeypatch):
    old, new, *_ = plans(tmp_path, monkeypatch); calls = []
    monkeypatch.setattr(driver, 'factory_for', lambda *a: calls.append(('legacy', a)) or 'legacy-factory')
    monkeypatch.setattr(transport, 'factory_for_profile', lambda *a: calls.append(('profile', a)) or 'profile-factory')
    assert driver.scientist_factory(tmp_path / 'worlds', old, tmp_path) == 'legacy-factory'
    assert driver.scientist_factory(tmp_path / 'worlds', new, tmp_path) == 'profile-factory'
    assert [v[0] for v in calls] == ['legacy', 'profile']
    assert calls[1][1][1] is new


def test_application_record_required_after_dispatch_and_never_implicitly_applied_to_legacy(tmp_path):
    cell = tmp_path / 'world'; cell.mkdir()
    spec = SimpleNamespace(fingerprint='f' * 64)
    p = {'source_commit': 'a' * 40, 'scientist_transport': transport.contract(read_seconds=900)}
    with pytest.raises(ValueError, match='missing after dispatch'):
        transport.require_cell_transport(cell, p, spec, seed=42, failed=False)
    assert transport.require_cell_transport(cell, p, spec, seed=42, failed=True)['scientific_POSTs'] == 0
    (cell / 'wire-requests.jsonl').write_text('SCRIPTED request exists')
    with pytest.raises(ValueError, match='missing after dispatch'):
        transport.require_cell_transport(cell, p, spec, seed=42, failed=True)
    (cell / 'replies').mkdir()
    binding = {'model': 'qwen3:8b', 'model_revision': 'b' * 64}
    with sqlite3.connect(cell / 'replies/responses.sqlite') as db:
        db.execute('CREATE TABLE metadata (binding TEXT)')
        db.execute('INSERT INTO metadata VALUES (?)', (json.dumps(binding),))
    applied = {'http_timeout_seconds': p['scientist_transport']['http_timeout_seconds'], 'sdk_max_retries': 0,
        'client_object_replaced': False, 'completion_callback_replaced': False, 'request_body_modified': False}
    save(cell / 'scientist-transport.json', transport.record_value(p['scientist_transport'],
        source=p['source_commit'], system_fingerprint=spec.fingerprint, seed=42, run_id=cell.name,
        cache_binding=binding, applied=applied))
    result = transport.require_cell_transport(cell, p, spec, seed=42, failed=False)
    assert result['applied']['http_timeout_seconds']['read'] == 900
    with pytest.raises(ValueError, match='unplanned'):
        transport.require_cell_transport(cell, {'source_commit': p['source_commit']}, spec, seed=42, failed=False)


def test_profile_factory_keeps_original_budget_source_and_safe_point_binding(tmp_path, monkeypatch):
    captures = []
    stop = SimpleNamespace(deadline=None)
    sim = SimpleNamespace(portable_stop=stop, llm=SimpleNamespace(response_cache=SimpleNamespace(stop=stop)))
    class Factory:
        model_digest = 'm'; corpus_sha256 = 'c'
        def __init__(self, *args, **kwargs): captures.append((args, kwargs))
        def __call__(self, *args): return sim
    monkeypatch.setattr(transport, 'LocalTransportBoundNativeFactory', Factory)
    monkeypatch.setattr(transport.time, 'monotonic', lambda: 100)
    p = {'data_cache': str(tmp_path / 'cache'), 'designer': {'SCRIPTED': True},
        'scientist': {'model_digest': 'm', 'corpus_sha256': 'c'}, 'experiment': {'SCRIPTED': True},
        'world': {'world_conditions': {'SCRIPTED': True}}, 'scientist_transport': transport.contract(read_seconds=900),
        'budget': {'world_wall_seconds': 7200}}
    factory = transport.factory_for_profile(tmp_path / 'worlds', p, tmp_path)
    assert factory('SCRIPTED-spec', 42, 'SCRIPTED-world') is sim
    args, kwargs = captures[0]
    assert kwargs['years'] == kwargs['corpus_years'] == 4
    assert kwargs['maximum_http_attempts'] == 1024 and kwargs['record_wire'] and kwargs['record_code']
    assert kwargs['inference_lock'] == tmp_path / 'inference.lock'
    assert kwargs['scientist_transport'] == p['scientist_transport']
    assert stop.deadline == 7300
