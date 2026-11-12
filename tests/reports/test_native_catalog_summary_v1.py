"""SCRIPTED figure/data plumbing; no actual policy result or native inference."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.reports import native_catalog_actuation_summary_v1 as module
from scripts import finish_native_catalog_summary_v1 as finish
from utopia.optimization.native_numeric_designer import save, checked
from utopia.system.design_patch import digest


def seal(value):
    value.pop('content_sha256', None); value['content_sha256'] = digest(value); return value


def report():
    worlds = []
    for condition in module.CONDITIONS:
        annual = [{'year': year, 'authors': [{'id': 'SCRIPTED-founder-' + str(i),
            'is_active': i < 5 - year // 2, 'resources': 30 - year,
            'project_start_year': 1, 'project_end_year': 2,
            'newest_direction': {'direction': 'SCRIPTED-topic'}} for i in range(5)]} for year in range(1, 5)]
        p = -sum(a['is_active'] for y in annual for a in y['authors'])
        worlds.append({'condition': condition, 'identity': 'SCRIPTED-' + condition, 'seed': 61001,
            'status': 'complete', 'scores': {'throughput': -3., 'founder-activity': float(p)},
            'annual': annual, 'physical_wire_requests': 12, 'committed_responses': 11,
            'wire_without_committed_reply': 1, 'direction_requests': [] if condition == 'project' else [
                {'wire_index': 0, 'literal_instruction_present': condition == 'information'}],
            'catalog_project_effects': [{'SCRIPTED': True}] if condition == 'project' else []})
    return seal({'schema': 'scienceutopia.native-catalog-actuation-report.v1',
        'scientific_source_commit': 'a' * 40, 'plan_sha256': 'b' * 64,
        'audit_content_sha256': 'c' * 64, 'raw_inventory_sha256': 'd' * 64,
        'catalog': {'directions': [{'topic': 'SCRIPTED-topic', 'years': 2}]}, 'worlds': worlds,
        'new_model_calls': 0, 'new_code_executions': 0, 'loss_or_selection_changed': False})


def test_literal_projects_boundary_flags_and_cut_differences_without_mutation():
    r = report(); before = digest(r); summary = module.summarize(r)
    assert digest(r) == before and len(summary['annual_project_states']) == 60
    assert summary['worlds'][0]['annual'][0]['active_founders'] == 5
    assert summary['worlds'][0]['annual'][-1]['active_founders'] == 3
    assert all(w['loss_difference_from_cut'] == {'throughput': 0., 'founder-activity': 0.} for w in summary['worlds'])
    assert summary['worlds'][2]['direction_request_attempts'] == 0
    assert summary['worlds'][2]['verified_catalog_project_effects'] == 1
    assert not summary['new_native_worlds']


def test_failed_prefixes_have_no_loss_or_cut_difference_and_empty_world_has_no_states():
    r = report(); failed = r['worlds'][0]
    failed.update(status='failed', scores={o: None for o in module.OBJECTIVES}, annual=failed['annual'][:2])
    summary = module.summarize(seal(r))
    assert len(summary['worlds'][0]['annual']) == 2
    assert all(v is None for w in summary['worlds'] for v in w['loss_difference_from_cut'].values())
    failed['annual'] = []; summary = module.summarize(seal(r))
    assert not summary['worlds'][0]['annual'] and len(summary['founder_ids']) == 5


@pytest.mark.parametrize('change', ['missing', 'duplicate', 'different-seed', 'bad-P', 'bool-loss',
    'false-duration', 'new-founder', 'missing-year', 'scored-null', 'unscored-complete', 'duplicate-wire', 'bad-count'])
def test_ambiguous_or_invented_outcomes_fail_closed(change):
    r = report(); w = r['worlds'][0]
    if change == 'missing': r['worlds'].pop()
    elif change == 'duplicate': r['worlds'][1]['identity'] = w['identity']
    elif change == 'different-seed': w['seed'] += 1
    elif change == 'bad-P': w['scores']['founder-activity'] -= 1
    elif change == 'bool-loss': w['scores']['throughput'] = True
    elif change == 'false-duration': w['annual'][0]['authors'][0]['project_end_year'] = 1
    elif change == 'new-founder': w['annual'][1]['authors'][0]['id'] = 'SCRIPTED-new'
    elif change == 'missing-year': w['annual'].pop(1)
    elif change == 'scored-null': w['status'] = 'failed'
    elif change == 'unscored-complete': w['scores']['throughput'] = None
    elif change == 'duplicate-wire': w['direction_requests'] *= 2
    else: w['committed_responses'] = 13
    with pytest.raises(ValueError): module.summarize(seal(r))


def test_real_double_figure_export_is_deterministic_with_all_literal_rows(tmp_path, monkeypatch):
    inputs = tmp_path / 'inputs'; inputs.mkdir(); r = report()
    for name in ('one', 'two'): save(inputs / (name + '.json'), {k: v for k, v in r.items() if k != 'content_sha256'})
    monkeypatch.setattr(module, 'pinned_revision', lambda root: 'e' * 40)
    outputs = [tmp_path / 'first', tmp_path / 'second']
    for out in outputs:
        module.export(SimpleNamespace(one=inputs / 'one.json', two=inputs / 'two.json', output=out))
        assert len((out / 'annual-project-states.csv').read_text().splitlines()) == 61
        assert (out / 'project-states.png').stat().st_size > 10000
        assert 'Founder 5' in (out / 'project-states.svg').read_text()
    assert {p.name: p.read_bytes() for p in outputs[0].iterdir()} == {p.name: p.read_bytes() for p in outputs[1].iterdir()}
    with pytest.raises(ValueError):
        module.export(SimpleNamespace(one=inputs / 'one.json', two=inputs / 'one.json', output=tmp_path / 'bad'))


@pytest.mark.parametrize('failure', [None, 'closure', 'summary-1', 'different-bytes'])
def test_summary_wait_and_terminal_receipts_never_retry_science(tmp_path, monkeypatch, failure):
    chain = tmp_path / 'chain'; chain.mkdir()
    save(chain / 'started.json', {'schema': 'scienceutopia.native-catalog-choices-finish.v1',
        'scientific_source_commit': 'a' * 40, 'new_inference_allowed': False})
    monkeypatch.setattr(finish, 'git_binding', lambda root: 'e' * 40)
    def wait(*a, **kw):
        if failure == 'closure': raise ValueError('SCRIPTED stopped original report')
        return {'report_files': {'SCRIPTED': 'same'}}
    monkeypatch.setattr(finish, 'wait_reports', wait)
    monkeypatch.setattr(finish, 'sha', lambda path: 'f' * 64)
    calls = []
    def run(argv, **kw):
        out = Path(argv[argv.index('--output') + 1]); calls.append(out.name)
        if out.name == failure: return SimpleNamespace(returncode=2)
        out.mkdir(); save(out / 'SCRIPTED.json', {'value': out.name if failure == 'different-bytes' else 'same'})
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(finish.subprocess, 'run', run)
    args = SimpleNamespace(chain=chain, output=tmp_path / 'out')
    if failure:
        with pytest.raises(ValueError): finish.run(args)
    else: finish.run(args)
    assert calls == ([] if failure == 'closure' else ['summary-1'] if failure == 'summary-1' else ['summary-1', 'summary-2'])
    assert checked(json.loads((args.output / 'ended.json').read_text()))['status'] == ('stopped' if failure else 'closed')
    with pytest.raises(ValueError): finish.run(args)
