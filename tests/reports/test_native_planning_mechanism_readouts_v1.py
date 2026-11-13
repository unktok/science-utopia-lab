"""SCRIPTED choice/consumer readout tests; no real model results are inferred."""
from copy import deepcopy
import json
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest

from scripts import finish_native_planning_mechanism_readouts_v1 as finish
from scripts.reports import native_planning_choice_trace_v1 as module
from scripts.reports.native_institution_effect_trace_v1 import SCOPES
from scripts.reports.native_observed_request_classes_v1 import AUDITS
from tests.reports.test_native_instruction_timing_report_v1 import wire, response
from tests.reports.test_native_planning_objective_loop_v1 import plan, seal
from utopia.optimization.native_numeric_designer import checked, save
from utopia.system.design_patch import clone, digest


def state(year, actors=1):
    return {'year': year, 'ecosystem_data': {'agents': [
        {'id': 'actor' + str(i), 'can_author': True, 'is_active': True, 'resources': 30.,
         'project_start_year': 1, 'project_end_year': 1, 'newest_direction': {'topic': 'short'},
         'memory_bank': [{'type': 'select_research_direction', 'year': 1, 'direction': 'short',
                          'detailed_focus': 'SCRIPTED focus', 'thought': 'SCRIPTED reason'}]}
        for i in range(actors)]}}


def test_known_marker_is_not_an_assumption_about_every_new_information_institution(tmp_path, monkeypatch):
    states = {y: state(y, 2) for y in range(1, 5)}; before = deepcopy(states)
    monkeypatch.setattr(module, 'checkpoint', lambda cell, item, system: states[item['year']])
    w = wire('A NEW authored office says something else.\n' + wire()['payload']['messages'][0]['content'])
    monkeypatch.setattr(module, 'original_pairs', lambda cell: ([w], {0: response()}))
    world = {'identity': 'SCRIPTED', 'role': 'search:throughput', 'seed': 61001, 'status': 'complete',
             'scores': {'throughput': -2, 'content-utility': -1}, 'system': {},
             'physical_proof': {'annual_checkpoints': [{'year': y} for y in range(1, 5)]}}
    r = module.summarize_world(tmp_path, world, {'short': 1, 'long': 3})
    chosen = r['direction_requests'][0]
    assert not chosen['literal_known_developer_agenda_marker_present']
    assert 'literal_instruction_present' not in chosen
    assert chosen['matching_actual_memory_actor_ids'] == ['actor0', 'actor1']
    assert not chosen['unique_actor_attribution'] and chosen['selected_topic'] == 'short'
    assert states == before and len(r['annual']) == 4


def test_failed_prefix_is_not_a_completed_loss_and_complete_world_needs_four_boundaries(tmp_path):
    world = {'identity': 'SCRIPTED', 'role': 'search:content-utility', 'seed': 61001, 'status': 'failed',
             'scores': {'throughput': None, 'content-utility': None}, 'system': {}, 'physical_proof': {}}
    r = module.summarize_world(tmp_path, world, {'short': 1})
    assert r['annual'] == r['direction_requests'] == [] and r['partial_boundaries_are_not_completed_outcomes']
    assert all(v is None for v in r['scores'].values())
    world['status'] = 'complete'
    with pytest.raises(ValueError, match='annual prefix'): module.summarize_world(tmp_path, world, {'short': 1})


def test_existing_committed_reply_without_wire_is_rejected_not_silently_counted_as_zero(tmp_path):
    (tmp_path / 'replies').mkdir()
    with sqlite3.connect(tmp_path / 'replies/responses.sqlite') as db:
        db.execute('CREATE TABLE replies (data TEXT)'); db.execute("INSERT INTO replies VALUES ('SCRIPTED')")
    with pytest.raises(ValueError, match='without an original wire'): module.original_pairs(tmp_path)


def evidence(tmp_path, monkeypatch):
    p, _, _, _ = plan(tmp_path / 'input', monkeypatch); root = tmp_path / 'raw'; root.mkdir()
    frozen = tmp_path / 'frozen'; frozen.mkdir(); worlds = []
    for i, label in enumerate(p['reference_order'] + ['SCRIPTED-failed-own']):
        identity = 'reference-' + label if i < 8 else label
        cell = root / 'physical' / identity / 'worlds' / (identity + '-s61001'); cell.mkdir(parents=True)
        (cell / 'wire-requests.jsonl').write_text(''); (cell / 'replies').mkdir()
        with sqlite3.connect(cell / 'replies/responses.sqlite') as db:
            db.execute('CREATE TABLE replies (payload_sha TEXT, outcome TEXT, data TEXT, data_sha TEXT)')
        worlds.append({'identity': identity, 'role': 'developer-reference' if i < 8 else 'search:throughput',
            'seed': 61001, 'status': 'complete' if i < 8 else 'failed', 'system': p['initial_system'],
            'scores': {'throughput': 0 if i < 8 else None, 'content-utility': 0 if i < 8 else None},
            'physical_proof': {'annual_checkpoints': [{'year': y} for y in range(1, 5) if i < 8 or y == 1]}})
    a = {'schema': 'scienceutopia.native-planning-objective-loop-audit.v1', 'source_commit': p['source_commit'],
         'plan_sha256': p['content_sha256'], 'closure': {'terminal': {'status': 'closed'}},
         'source_proof': {'status': 'verified-exact-source-closure', 'SCRIPTED': 'not a real attestation'},
         'new_model_calls': 0, 'new_code_executions': 0, 'worlds': worlds, 'authoring': [{'SCRIPTED': True}] * 6}
    monkeypatch.setattr(module, 'pinned_revision', lambda *args: p['source_commit'])
    monkeypatch.setattr(module, 'checkpoint', lambda cell, item, system: state(item['year']))
    return root, frozen, p, a


def retain(root, p, a, tmp_path):
    save(root / 'plan.json', {k: v for k, v in p.items() if k != 'content_sha256'})
    a['plan_sha256'] = p['content_sha256']; a['raw_inventory_sha256'] = digest(module._inventory(root)); seal(a)
    paths = [tmp_path / 'audit-one.json', tmp_path / 'audit-two.json']
    for path in paths: save(path, {k: v for k, v in a.items() if k != 'content_sha256'})
    return paths


def test_full_export_twice_retains_all_controls_failed_prefix_and_project_dates(tmp_path, monkeypatch):
    root, frozen, p, a = evidence(tmp_path, monkeypatch); paths = retain(root, p, a, tmp_path)
    before = module._inventory(root); outputs = [tmp_path / 'one', tmp_path / 'two']
    for out in outputs:
        module.export(SimpleNamespace(run=root, frozen_source=frozen, audit_one=paths[0], audit_two=paths[1], output=out))
    assert before == module._inventory(root)
    assert {f.name: f.read_bytes() for f in outputs[0].iterdir()} == {f.name: f.read_bytes() for f in outputs[1].iterdir()}
    result = checked(json.loads((outputs[0] / 'report.json').read_text()))
    assert len(result['worlds']) == 9 and len(result['worlds'][-1]['annual']) == 1
    assert result['worlds'][-1]['partial_boundaries_are_not_completed_outcomes']
    assert result['known_marker_is_not_all_information'] and not result['loss_or_selection_changed']
    assert len(list(outputs[0].iterdir())) == 3


@pytest.mark.parametrize('change', ['reference', 'duplicate', 'stopped', 'catalog'])
def test_changed_scope_never_becomes_a_valid_trace(tmp_path, monkeypatch, change):
    root, frozen, p, a = evidence(tmp_path, monkeypatch)
    if change == 'reference': a['worlds'].pop(0)
    elif change == 'duplicate': a['worlds'].append(clone(a['worlds'][0]))
    elif change == 'stopped': a['closure']['terminal']['status'] = 'stopped'
    else: p['catalog']['directions'][0]['years'] += 1; seal(p)
    paths = retain(root, p, a, tmp_path)
    with pytest.raises(ValueError):
        module.export(SimpleNamespace(run=root, frozen_source=frozen, audit_one=paths[0], audit_two=paths[1], output=tmp_path / 'bad'))
    assert not (tmp_path / 'bad').exists()


@pytest.mark.parametrize('kind', ['choices', 'effects', 'requests'])
def test_waiters_use_explicit_planning_scope_and_never_infer_new_dispatch(tmp_path, monkeypatch, kind):
    seen = {}; monkeypatch.setattr(finish, 'finish', lambda args, **kw: seen.update(kw))
    finish.run(SimpleNamespace(kind=kind, frozen_source=tmp_path))
    assert seen['plan_schema'] == 'scienceutopia.native-planning-objective-loop.v1.plan'
    assert seen['preceding_schema'] == 'scienceutopia.native-planning-objective-loop-finish.v1'
    if kind == 'requests': assert seen['report_extra_arguments'] == ()
    elif kind == 'effects': assert seen['report_extra_arguments'][-2:] == ('--scope', 'planning-objective-development')
    else: assert seen['report_extra_arguments'] == ('--frozen-source', str(tmp_path.resolve()))
    assert SCOPES['planning-objective-development'] in AUDITS
