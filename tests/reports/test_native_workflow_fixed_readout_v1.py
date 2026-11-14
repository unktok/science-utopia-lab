"""New workflow evaluation routing; physical primitives explicitly SCRIPTED.

This does not execute native worlds or stand in for the deferred cold CLI proof.
"""
from types import SimpleNamespace

import pytest

from scripts.reports import native_institution_effect_trace_v1 as effects
from scripts.reports import native_planning_choice_trace_v1 as choices
from scripts.run_native_workflow_fixed_evaluation_v1 import read, save
from tests.reports.test_native_workflow_fixed_audit_report_v1 import audited


def inputs(tmp_path, monkeypatch):
    root, plan, audit, *_ = audited(tmp_path, monkeypatch)
    paths = [tmp_path / 'one.json', tmp_path / 'two.json']
    for path in paths: save(path, {k: v for k, v in audit.items() if k != 'content_sha256'})
    frozen = tmp_path / 'frozen'; frozen.mkdir()
    return SimpleNamespace(run=root, frozen_source=frozen, audit_one=paths[0], audit_two=paths[1],
        output=tmp_path / 'readout', scope='workflow-fixed-evaluation', study='workflow-fixed-evaluation'), plan


def test_effect_scope_forwards_every_physical_world_and_enables_workflow_boundary(tmp_path, monkeypatch):
    args, p = inputs(tmp_path, monkeypatch); calls = []
    monkeypatch.setattr(effects, 'pinned_revision', lambda source: p['source_commit'])
    def trace(cell, world, source, *, workflow=False):
        calls.append((world['identity'], workflow))
        return {k: world[k] for k in ('identity', 'role', 'seed', 'status')} | {'annual': [], 'code_calls': []}
    monkeypatch.setattr(effects, 'trace_world', trace)
    effects.export(args)
    assert calls == [(j['identity'], True) for j in p['jobs']]
    r = read(args.output / 'report.json')
    assert r['scope'] == 'workflow-fixed-evaluation' and len(r['worlds']) == 4
    assert r['worlds'][0]['status'] == 'failed'  # No dropping a failed evaluated policy.
    assert not r['interpretation']['causal_mechanism_effect_identified']


def test_choice_scope_uses_exact_fixed_summary_before_tracing_all_worlds(tmp_path, monkeypatch):
    args, p = inputs(tmp_path, monkeypatch); calls = []
    monkeypatch.setattr(choices, 'pinned_revision', lambda source: p['source_commit'])
    def trace(cell, world, catalog):
        calls.append(world['identity'])
        assert set(catalog) == {r['topic'] for r in p['catalog']['directions']}
        return {k: world[k] for k in ('identity', 'role', 'seed', 'status')} | {'annual': [], 'direction_requests': []}
    monkeypatch.setattr(choices, 'summarize_world', trace)
    choices.export(args)
    assert calls == [j['identity'] for j in p['jobs']]
    r = read(args.output / 'report.json')
    assert r['schema'] == 'scienceutopia.native-workflow-fixed-choice-trace.v1'
    assert len(r['worlds']) == 4 and not r['loss_or_selection_changed']


@pytest.mark.parametrize('reader', ['effects', 'choices'])
def test_workflow_fixed_audit_cannot_be_relabelled_as_old_study(tmp_path, monkeypatch, reader):
    args, p = inputs(tmp_path, monkeypatch)
    module = effects if reader == 'effects' else choices
    monkeypatch.setattr(module, 'pinned_revision', lambda source: p['source_commit'])
    if reader == 'effects': args.scope = 'planning-fixed-evaluation'
    else: args.study = 'fixed-evaluation'
    with pytest.raises(ValueError): module.export(args)
    assert not args.output.exists()
