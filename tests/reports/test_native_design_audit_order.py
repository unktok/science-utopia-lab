"""Order-only replay regressions; SCRIPTED observations, no native inference."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import native_design_benchmark_plan as spec
from scripts import run_native_design_benchmark as driver
from scripts import native_design_audit_order as order
from scripts import audit_native_design_benchmark_order as adapter
from tests.reports.test_native_design_benchmark_plan import plan


def reseal(value):
    value.pop('content_sha256', None)
    value['content_sha256'] = order.digest(value)
    return value


def sorted_roundtrip(value):
    return json.loads(json.dumps(value, sort_keys=True))


def restore(p):
    return order.restore_plan(p, spec=spec, source=p['source_commit'],
                             seed_usage_sha256=p['evaluation_seed_usage_sha256'])


def fixture(root):
    p = plan()
    metrics = {t['metric_id']: {'status': 'measured', 'value': 0}
               for loss in p['losses'].values() for t in loss['per_run']['terms']}
    # Reference scores all tie on purpose: chronology affects every all-tied list.
    for name in p['reference_systems']:
        path = root / 'references' / name / 'observation.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({'status': 'complete', 'metadata': {
            'technical_failures': [], 'runs': [{'SCRIPTED': True}],
            'measurements': [{'run_id': 'SCRIPTED', 'metrics': metrics}]}}))
    states = {(run, arm): SimpleNamespace(state={'pending': None, 'records': [
        {'generation_error': {'SCRIPTED': True}, 'observations': []} for _ in range(4)]})
        for run, bindings in p['campaign_bindings'].items() for arm in bindings}

    def loader(base, unused_plan, run, arm):
        assert Path(base) == root
        return states[run, arm]

    s = driver.selection_payload(root, p, frozen_utc='SCRIPTED', campaign_loader=loader)
    return p, s, loader, states


def test_sorted_json_roundtrip_needs_both_plan_and_selection_mapping_order(tmp_path):
    p, s, loader, _ = fixture(tmp_path)
    saved_p, saved_s = sorted_roundtrip(p), sorted_roundtrip(s)
    assert saved_p == p and saved_s == s
    assert list(saved_p['reference_systems']) != list(p['reference_systems'])
    wrong = driver.selection_payload(tmp_path, saved_p, frozen_utc='SCRIPTED', campaign_loader=loader)
    assert not order.same_values(wrong, s)
    restored_p = restore(saved_p)
    assert order.same_values(restored_p, saved_p) and list(restored_p['reference_systems']) == list(p['reference_systems'])
    original_jobs = driver.evaluation_jobs(p, s)
    assert driver.evaluation_jobs(restored_p, saved_s) != original_jobs
    restored_s = order.restore_selection(tmp_path, saved_s, plan=restored_p,
                                        driver=driver, campaign_loader=loader)
    assert driver.evaluation_jobs(restored_p, restored_s) == original_jobs
    assert restored_s['content_sha256'] == saved_s['content_sha256']
    assert restored_s['pooled']['throughput']['all_tied_row_ids'] == [
        'reference:' + name for name in p['reference_systems']]


@pytest.mark.parametrize('change', [
    lambda p: p['budget'].update(search_slots=119),
    lambda p: p['objectives'].reverse(),
    lambda p: p['losses']['throughput']['per_run']['terms'][0].update(weight=999),
    lambda p: p.update(source_commit='b' * 40),
])
def test_plan_reconstruction_rejects_resealed_value_or_list_changes(change):
    p = sorted_roundtrip(plan()); change(p); reseal(p)
    with pytest.raises(ValueError):
        order.restore_plan(p, spec=spec, source='a' * 40,
                           seed_usage_sha256=p['evaluation_seed_usage_sha256'])


def test_seed_history_is_bound_to_actual_inventory_not_only_saved_plan():
    p = plan()
    with pytest.raises(ValueError, match='source-pinned'):
        order.restore_plan(p, spec=spec, source=p['source_commit'], seed_usage_sha256='b' * 64)


@pytest.mark.parametrize('change', [
    lambda s: s['pooled']['throughput']['all_tied_row_ids'].reverse(),
    lambda s: s['selected']['throughput:parameters'].update(loss=-999.),
    lambda s: s['all_rows'].reverse(),
    lambda s: s.update(plan_sha256='b' * 64),
])
def test_selection_reconstruction_rejects_resealed_values_and_list_order(tmp_path, change):
    p, s, loader, _ = fixture(tmp_path); change(s); reseal(s)
    with pytest.raises(ValueError):
        order.restore_selection(tmp_path, s, plan=p, driver=driver, campaign_loader=loader)


@pytest.mark.parametrize('incomplete', ['pending', 'short'])
def test_original_closed_search_guards_remain_active(tmp_path, incomplete):
    p, s, loader, states = fixture(tmp_path)
    state = next(iter(states.values())).state
    if incomplete == 'pending': state['pending'] = {'SCRIPTED': True}
    else: state['records'].pop()
    with pytest.raises(ValueError, match='every declared search slot'):
        order.restore_selection(tmp_path, s, plan=p, driver=driver, campaign_loader=loader)


@pytest.mark.parametrize('a,b', [(True, 1), (1, 1.0), ([1, 2], [2, 1])])
def test_same_values_is_strict_except_mapping_insertion_order(a, b):
    assert not order.same_values(a, b)
    assert order.same_values({'b': 2, 'a': 1}, {'a': 1, 'b': 2})


def test_reader_targets_only_exact_paths_rechecks_raw_and_returns_independent_objects(tmp_path):
    ordered_p = {'b': 2, 'a': 1}; ordered_s = {'d': 4, 'c': 3}
    for name, value in [('plan.json', ordered_p), ('selection.json', ordered_s)]:
        (tmp_path / name).write_text(json.dumps(value, sort_keys=True))
    nested = tmp_path / 'other' / 'plan.json'; nested.parent.mkdir(); nested.write_text('{"a":1,"b":2}')
    read = lambda p: json.loads(Path(p).read_text())
    reader = order.OrderedSourceReader(read, tmp_path, saved_plan=read(tmp_path / 'plan.json'),
        ordered_plan=ordered_p, saved_selection=read(tmp_path / 'selection.json'), ordered_selection=ordered_s)
    assert list(reader(tmp_path / 'plan.json')) == ['b', 'a']
    assert list(reader(nested)) == ['a', 'b']
    reader(tmp_path / 'selection.json')['d'] = 999
    assert reader(tmp_path / 'selection.json') == ordered_s
    (tmp_path / 'plan.json').write_text('{"a":1,"b":999}')
    with pytest.raises(ValueError, match='changed after preparation'):
        reader(tmp_path / 'plan.json')


def test_private_function_copy_changes_only_reader_and_does_not_bypass_other_guards():
    namespace = {'read': lambda p: {'bad': True}, 'guard': lambda value: value == {'ok': True}}
    exec('def analyze(path):\n value=read(path)\n if not guard(value): raise ValueError("guard retained")\n return value', namespace)
    original = namespace['analyze']; before = dict(original.__globals__)
    copied = order.with_ordered_reader(original, lambda p: {'ok': True})
    assert copied.__code__ is original.__code__
    assert original.__globals__ == before and copied('SCRIPTED') == {'ok': True}
    assert {k for k in copied.__globals__ if copied.__globals__[k] is not before[k]} == {'read'}
    with pytest.raises(ValueError, match='guard retained'): original('SCRIPTED')
    with pytest.raises(ValueError, match='guard retained'):
        order.with_ordered_reader(original, lambda p: {'ok': False})('SCRIPTED')


def test_adapter_refuses_live_or_aborted_writer_and_overwriting_or_inside_source_outputs(tmp_path):
    raw = tmp_path / 'raw'; raw.mkdir(); source = tmp_path / 'source'; source.mkdir()
    with pytest.raises(ValueError, match='normal writer closure'): adapter.require_closed(raw, 'a' * 40)
    start = {'source_commit': 'a' * 40, 'action': 'all', 'status': 'started',
             'started_utc': '2026-11-07T00:00:00+00:00'}
    (raw / 'writer.started.json').write_text(json.dumps(start))
    end = {**start, 'status': 'exited', 'exit_code': 0, 'ended_utc': '2026-11-07T01:00:00+00:00'}
    (raw / 'writer.ended.json').write_text(json.dumps(end)); adapter.require_closed(raw, 'a' * 40)
    for bad in [True, 1, None]:
        (raw / 'writer.ended.json').write_text(json.dumps({**end, 'exit_code': bad}))
        with pytest.raises(ValueError): adapter.require_closed(raw, 'a' * 40)
    for path in [raw / 'output.json', source / 'output.json']:
        with pytest.raises(ValueError, match='outside raw and frozen'): adapter.fresh_output(path, raw, source)
    existing = tmp_path / 'existing.json'; existing.write_text('preserve')
    with pytest.raises(ValueError, match='fresh'): adapter.fresh_output(existing, raw, source)
    assert existing.read_text() == 'preserve'


def test_closed_report_preserves_explicit_adapter_provenance_without_changing_old_fixture():
    from scripts.reports.native_design_benchmark import project
    from tests.reports.test_native_design_benchmark_report import fixture as report_fixture
    p, a = report_fixture()
    assert 'input_audit_analysis_adapter' not in project(p, a, expected_source=p['source_commit'])
    a['analysis_adapter'] = {'schema': adapter.SCHEMA, 'SCRIPTED': True}; reseal(a)
    r = project(p, a, expected_source=p['source_commit'])
    assert r['input_audit_analysis_adapter'] == a['analysis_adapter']
    r['input_audit_analysis_adapter']['SCRIPTED'] = False
    assert a['analysis_adapter']['SCRIPTED'] is True
