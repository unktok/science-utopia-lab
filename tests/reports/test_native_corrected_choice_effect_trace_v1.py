"""SCRIPTED upstream physics/source; exact compound-cell export and null data."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.reports import native_institution_effect_trace_v1 as module
from scripts import finish_native_corrected_choice_effects_v1 as continuation
from utopia.optimization.native_numeric_designer import save, checked
from utopia.system.design_patch import digest
from utopia.utils.data_utils import write_json_atomic


def fixture(tmp_path, monkeypatch, *, fixed=False):
    raw, science, reader = (tmp_path / key for key in ('raw', 'science', 'reader'))
    for root in (raw, science, reader): root.mkdir()
    monkeypatch.setattr(module, 'ROOT', reader)
    monkeypatch.setattr(module, 'pinned_revision', lambda root: 'b' * 40 if root == reader else 'a' * 40)
    scope = 'corrected-choice-fixed-evaluation' if fixed else 'corrected-choice-development'
    p = save(raw / 'plan.json', {'schema': module.CORRECTED_SCOPES[scope] + '.plan', 'source_commit': 'a' * 40})
    worlds = []
    for index in range(2):
        # Intentionally repeated basename; different compound path AND audit
        # context distinguish it without AST/loss sharing or global globbing.
        cell = raw / ('method-' + str(index)) / 'worlds/repeated-s42'; cell.mkdir(parents=True)
        worlds.append({'identity': 'repeated', 'seed': 42, 'role': 'SCRIPTED-own',
            'method': 'SCRIPTED-method-' + str(index), 'optimizer_history': 0, 'objective': 'SCRIPTED-objective',
            'status': 'failed' if index else 'complete', 'loaded': {'context': str(cell / 'loaded-role-context-000.json')}})
    before = module._inventory(raw)
    audit = {'schema': module.SCOPES[scope], 'source_commit': p['source_commit'], 'plan_sha256': p['content_sha256'],
        'source_proof': {'status': 'verified-exact-source-closure', 'SCRIPTED': 'not physical provenance'},
        'closure': {'terminal': {'status': 'closed'}}, 'raw_inventory_sha256': digest(before),
        'new_model_calls': 0, 'new_code_executions': 0, 'worlds': worlds}
    paths = [tmp_path / ('audit-' + str(i) + '.json') for i in (1, 2)]
    for path in paths: save(path, audit)
    calls = []
    def trace(cell, world, source, **kwargs):
        calls.append((cell, world, source, kwargs))
        return {'identity': world['identity'], 'role': world['role'], 'seed': world['seed'],
            'status': world['status'], 'annual': [], 'code_calls': [],
            'code_attempts': None, 'causal_mechanism_effect_identified': False}
    monkeypatch.setattr(module, 'trace_world', trace)
    def forbidden(*a, **kw): pytest.fail('metadata-only trace export cannot call models or execute source')
    monkeypatch.setattr('requests.Session.post', forbidden)
    monkeypatch.setattr('openai.OpenAI.__init__', forbidden)
    monkeypatch.setattr('utopia.system.code_mechanisms.DockerCodeExecutor.execute', forbidden)
    return SimpleNamespace(run=raw, frozen_source=science, audit_one=paths[0], audit_two=paths[1],
        scope=scope, output=tmp_path / 'out'), p, audit, calls, reader


@pytest.mark.parametrize('fixed', [False, True])
def test_repeated_ids_preserve_exact_audited_cells_and_failed_world_not_a_fallback(tmp_path, monkeypatch, fixed):
    args, _, _, calls, _ = fixture(tmp_path, monkeypatch, fixed=fixed); module.export(args)
    import json
    report = checked(json.loads((args.output / 'report.json').read_text()))
    assert [row['audited_world_ordinal'] for row in report['worlds']] == [0, 1]
    assert [row['status'] for row in report['worlds']] == ['complete', 'failed']
    assert len({row['original_compound_cell'] for row in report['worlds']}) == 2
    assert all(call[3] == {'workflow': True} for call in calls)
    assert report['analysis_source_commit'] == 'b' * 40
    assert not report['interpretation']['causal_mechanism_effect_identified']


@pytest.mark.parametrize('problem', ['escape', 'reuse-cell', 'wrong-basename', 'different-plan'])
def test_foreign_or_ambiguous_physics_cannot_attach_to_a_corrected_candidate(tmp_path, monkeypatch, problem):
    args, p, audit, _, _ = fixture(tmp_path, monkeypatch)
    if problem == 'escape': audit['worlds'][1]['loaded']['context'] = str(tmp_path / 'foreign/worlds/repeated-s42/context.json')
    elif problem == 'reuse-cell': audit['worlds'][1]['loaded'] = audit['worlds'][0]['loaded']
    elif problem == 'wrong-basename': audit['worlds'][1]['identity'] = 'another'
    else:
        value = {k: v for k, v in p.items() if k != 'content_sha256'}; value['schema'] = 'SCRIPTED-other.plan'
        # New fixture evidence only; never an existing scientific record.
        (args.run / 'plan.json').unlink(); p = save(args.run / 'plan.json', value)
        audit['plan_sha256'] = p['content_sha256']; audit['raw_inventory_sha256'] = digest(module._inventory(args.run))
    for path in (args.audit_one, args.audit_two):
        path.unlink(); save(path, audit)
    with pytest.raises(ValueError): module.export(args)
    assert not args.output.exists()


def test_reader_source_output_is_rejected_before_any_source_binding(tmp_path, monkeypatch):
    args, _, _, _, reader = fixture(tmp_path, monkeypatch); args.output = reader / 'not-created'
    monkeypatch.setattr(module, 'pinned_revision', lambda *a: pytest.fail('output preflight must precede source binding'))
    with pytest.raises(ValueError, match='outside reader'): module.export(args)
    assert not args.output.exists()


@pytest.mark.parametrize('place', ['reader', 'raw', 'science', 'analysis', 'alias', 'existing'])
def test_waiting_effect_output_children_rejected_before_wait_or_creation(tmp_path, monkeypatch, place):
    roots = {key: tmp_path / key for key in ('reader', 'raw', 'science', 'analysis')}
    for root in roots.values(): root.mkdir()
    monkeypatch.setattr(continuation, 'ROOT', roots['reader'])
    monkeypatch.setattr(continuation, 'finish', lambda *a, **kw: pytest.fail('preflight must precede wait'))
    if place == 'alias':
        alias = tmp_path / 'alias'; alias.symlink_to(roots['reader']); output = alias / 'not-created'
    elif place == 'existing': output = roots['analysis']
    else: output = roots[place] / 'not-created'
    args = SimpleNamespace(run=roots['raw'], analysis=roots['analysis'], frozen_source=roots['science'], output=output)
    with pytest.raises(ValueError, match='before waiting'): continuation.run(args)


def test_actual_waiting_wrapper_binds_corrected_original_closure_and_source_scope(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(continuation, 'finish', lambda args, **kwargs: calls.append(kwargs))
    continuation.run(SimpleNamespace(run=tmp_path / 'raw', analysis=tmp_path / 'analysis',
        frozen_source=tmp_path / 'science', output=tmp_path / 'external'))
    assert calls[0]['plan_schema'] == 'scienceutopia.native-corrected-choice-search.v1.plan'
    assert calls[0]['preceding_schema'] == 'scienceutopia.native-corrected-choice-search.v1.finish'
    assert calls[0]['report_module'] == 'scripts.reports.native_institution_effect_trace_v1'
    assert calls[0]['report_extra_arguments'] == ('--frozen-source', str(tmp_path / 'science'),
        '--scope', 'corrected-choice-development')
