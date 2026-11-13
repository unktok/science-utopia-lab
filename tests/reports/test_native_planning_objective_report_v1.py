"""SCRIPTED reporting fixtures, never actual model readiness or policy gains."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.reports import native_objective_instrument_loop_v1 as core
from scripts.reports import native_planning_objective_loop_v1 as module
from scripts import finish_native_planning_objective_report_v1 as continuation
from scripts.analyze_native_open_v7 import _inventory
from tests.reports.test_native_objective_instrument_report_v1 import evidence as old_evidence
from tests.reports.test_native_objective_fixed_evaluation_v1 import seal
from utopia.system.design_patch import clone, digest
from utopia.system.native_planning_controls import ORDER


def evidence(tmp_path, monkeypatch):
    p, a, records, traces = old_evidence(tmp_path, monkeypatch)
    # Fictional copies of the existing fixture worlds, with no new inference.
    original = [w for w in a['worlds'] if w['role'] == 'developer-reference']
    p.update(schema='scienceutopia.native-planning-objective-loop.v1.plan', generations=3,
             reference_order=list(ORDER), reference_systems={})
    p['schedule'] = [s for s in p['schedule'] if s['generation'] < 3]
    worlds, pairs = [], []
    for i, label in enumerate(ORDER):
        world = clone(original[i % len(original)]); world['identity'] = 'reference-' + label
        p['reference_systems'][label] = clone(world['system']); worlds.append(world)
        observation = clone(a['developer_references']['pairs'][i % len(original)]['observation'])
        observation['suggestion_id'] = world['identity']
        pairs.append({'suggestion': {'suggestion_id': world['identity'], 'candidate': clone(world['system'])}, 'observation': observation})
    context = seal({'pairs': pairs, 'SCRIPTED': 'not an original physical audit'})
    records = {(o, g): clone(r) for (o, g), r in records.items() if g < 3}; authors = []; traces = {}
    for key, record in records.items():
        record['request']['observations'] = clone(pairs)
        record['request']['developer_reference_context']['context_sha256'] = context['content_sha256']
        record.update(request_sha256=digest(record['request']), definition=None, observations=[], draws=[],
                      generation_error={'type': 'ValueError', 'message': 'SCRIPTED null, not a loss', 'loss': None})
        traces[key] = {'component_testing': None, 'terminal_response_missing': True,
                       'events': [], 'completed_steps': None, 'drawn_candidate_artifact_observations': None}
        authors.append({'objective': key[0], 'generation': key[1], 'request_sha256': record['request_sha256'],
                        'definition': None, 'generation_error': clone(record['generation_error']), 'component_testing': None})
    seal(p)
    a.update(schema='scienceutopia.native-planning-objective-loop-audit.v1', plan_sha256=p['content_sha256'],
             worlds=worlds, authoring=authors, developer_references=context,
             initial_readiness={'SCRIPTED': 'actual certificate checked by original cold auditor'},
             readiness=[{'SCRIPTED': True}] * 6,
             selection={'selected': {o: {'loss': None, 'all_tied_ids': [], 'selected_id': None,
                                        'system': None, 'completed_submissions': 0} for o in p['objectives']}})
    seal(a); return p, a, records, traces


def test_all_six_nulls_and_eight_controls_without_penalty_or_fallback(tmp_path, monkeypatch):
    p, a, records, traces = evidence(tmp_path, monkeypatch)
    report = core.summarize(p, a, records, traces, study='planning-v1')
    assert len(report['slots']) == 6 and len(report['references']) == len(report['physical_worlds']) == 8
    assert all(r['status'] == 'generation-failure' and r['loss'] is None for r in report['slots'])
    assert all(r['selected_id'] is None for r in report['frozen_selection'].values())
    with pytest.raises(ValueError): core.summarize(p, a, records, traces)


@pytest.mark.parametrize('change', ['reference', 'readiness', 'generation', 'score'])
def test_incomplete_or_changed_planning_scope_rejected(tmp_path, monkeypatch, change):
    p, a, records, traces = evidence(tmp_path, monkeypatch)
    if change == 'reference': p['reference_order'].pop()
    elif change == 'generation': p['generations'] = 4
    elif change == 'readiness': a['initial_readiness'] = None
    else: a['worlds'][0]['scores']['content-utility'] = -999
    seal(p); a['plan_sha256'] = p['content_sha256']; seal(a)
    with pytest.raises(ValueError): core.summarize(p, a, records, traces, study='planning-v1')


def test_actual_double_export_keeps_all_eight_reference_labels(tmp_path, monkeypatch):
    p, a, records, _ = evidence(tmp_path, monkeypatch); root = tmp_path / 'raw'; root.mkdir()
    for author in a['authoring']:
        author['raw_directory'] = str(root / 'search' / author['objective'] / 'authoring' / ('generation-' + author['request_sha256']))
        Path(author['raw_directory']).mkdir(parents=True)
    for o in p['objectives']:
        core.save(root / 'search' / o / 'campaign/native-adaptive-state.json',
                  {'pending': None, 'records': [records[o, g] for g in range(3)]})
    core.save(root / 'plan.json', {k: v for k, v in p.items() if k != 'content_sha256'})
    a['raw_inventory_sha256'] = digest(_inventory(root)); seal(a)
    audits = [tmp_path / 'audit-one.json', tmp_path / 'audit-two.json']
    for path in audits: core.save(path, {k: v for k, v in a.items() if k != 'content_sha256'})
    before = _inventory(root); outputs = [tmp_path / 'one', tmp_path / 'two']
    for output in outputs: module.export(SimpleNamespace(run=root, audit_one=audits[0], audit_two=audits[1], output=output))
    assert before == _inventory(root)
    assert {f.name: f.read_bytes() for f in outputs[0].iterdir()} == {f.name: f.read_bytes() for f in outputs[1].iterdir()}
    assert len(list(outputs[0].iterdir())) == 7
    for name in ('objective-loss-paths.svg', 'objective-cross-scores.svg'):
        svg = (outputs[0] / name).read_text()
        assert all('R' + str(i) + ' = ' + label in svg for i, label in enumerate(ORDER, 1))


def test_waiter_uses_original_planning_normal_closure_not_a_new_inference_loop(monkeypatch):
    seen = {}
    monkeypatch.setattr(continuation, 'finish', lambda args, **kwargs: seen.update(kwargs))
    continuation.run(SimpleNamespace())
    assert seen['plan_schema'] == 'scienceutopia.native-planning-objective-loop.v1.plan'
    assert seen['preceding_schema'] == 'scienceutopia.native-planning-objective-loop-finish.v1'
    assert seen['report_module'] == 'scripts.reports.native_planning_objective_loop_v1'
