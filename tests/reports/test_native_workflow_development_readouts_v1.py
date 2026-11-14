"""SCRIPTED analysis routing; no scientist, designer, Docker, TeX or native forward."""
import json
from types import SimpleNamespace

import pytest

from scripts import finish_native_workflow_mechanism_readouts_v1 as finish
from scripts.reports import native_planning_choice_trace_v1 as choices
from scripts.reports import native_institution_effect_trace_v1 as effects
from scripts.reports import native_observed_request_classes_v1 as requests
from tests.reports.test_native_workflow_objective_report_v1 import fixture
from utopia.optimization.native_numeric_designer import save, checked
from utopia.system.design_patch import digest


def seal(value):
    value.pop('content_sha256', None)
    value['content_sha256'] = digest(value)


def evidence(tmp_path, monkeypatch):
    p, a, records = fixture()
    p['catalog'] = {'directions': [{'topic': 'SCRIPTED', 'years': 2}]}
    p['catalog']['directions_sha256'] = digest(p['catalog']['directions'])
    seal(p); a['plan_sha256'] = p['content_sha256']
    root = tmp_path / 'raw'; root.mkdir(); frozen = tmp_path / 'frozen'; frozen.mkdir()
    save(root / 'plan.json', {k: v for k, v in p.items() if k != 'content_sha256'})
    for objective in p['objectives']:
        path = root / 'search' / objective / 'campaign/native-adaptive-state.json'
        path.parent.mkdir(parents=True)
        path.write_text(json.dumps({'pending': None, 'records': [records[objective, g] for g in range(3)]}))
    for world in a['worlds']:
        world['seed'] = 61001
        (root / 'physical/worlds' / (world['identity'] + '-s61001')).mkdir(parents=True)
    a['raw_inventory_sha256'] = digest(choices._inventory(root)); seal(a)
    paths = [tmp_path / 'one.json', tmp_path / 'two.json']
    for path in paths: save(path, {k: v for k, v in a.items() if k != 'content_sha256'})
    monkeypatch.setattr(choices, 'pinned_revision', lambda source: p['source_commit'])
    monkeypatch.setattr(choices, 'summarize_world', lambda cell, world, catalog:
        {k: world[k] for k in ('identity', 'role', 'seed', 'status')} | {'annual': [], 'direction_requests': []})
    args = SimpleNamespace(run=root, frozen_source=frozen, audit_one=paths[0], audit_two=paths[1],
        output=tmp_path / 'out', study='workflow-development')
    return args, p, a, records


def test_workflow_development_uses_strict_original_six_slot_reader_and_retains_every_world(tmp_path, monkeypatch):
    args, p, a, _ = evidence(tmp_path, monkeypatch)
    before = choices._inventory(args.run)
    choices.export(args)
    result = checked(json.loads((args.output / 'report.json').read_text()))
    assert result['schema'] == 'scienceutopia.native-workflow-choice-trace.v1'
    assert [w['identity'] for w in result['worlds']] == [w['identity'] for w in a['worlds']]
    assert len(result['worlds']) == 7 and before == choices._inventory(args.run)
    assert not result['loss_or_selection_changed'] and result['new_model_calls'] == 0


@pytest.mark.parametrize('change', ['pending', 'missing-record', 'wrong-selection', 'missing-reference',
    'stopped', 'old-study-label', 'wrong-objective'])
def test_incomplete_or_relabeled_workflow_never_becomes_valid_choice_export(tmp_path, monkeypatch, change):
    args, p, a, _ = evidence(tmp_path, monkeypatch)
    if change in ('pending', 'missing-record'):
        path = args.run / 'search/throughput/campaign/native-adaptive-state.json'
        state = json.loads(path.read_text())
        if change == 'pending': state['pending'] = {'SCRIPTED': True}
        else: state['records'].pop()
        path.write_text(json.dumps(state))
    elif change == 'wrong-selection': a['selection']['selected']['throughput']['selected_id'] = 'wrong'
    elif change == 'missing-reference': a['worlds'].pop(0)
    elif change == 'stopped': a['closure']['terminal']['status'] = 'stopped'
    elif change == 'wrong-objective':
        p['objectives'] = ['../outside']; seal(p); a['plan_sha256'] = p['content_sha256']
        (args.run / 'plan.json').write_text(json.dumps(p))
    else: args.study = 'development'
    a['raw_inventory_sha256'] = digest(choices._inventory(args.run)); seal(a)
    # Replace only the SCRIPTED audit fixture; no scientific journal is amended.
    for path in (args.audit_one, args.audit_two): path.write_text(json.dumps(a))
    with pytest.raises((ValueError, KeyError)):
        choices.export(args)
    assert not args.output.exists()


@pytest.mark.parametrize('kind', ['choices', 'effects', 'requests'])
def test_waiter_uses_exact_workflow_closure_and_explicit_original_source_scope(tmp_path, monkeypatch, kind):
    seen = {}; monkeypatch.setattr(finish, 'finish', lambda args, **kw: seen.update(kw))
    finish.run(SimpleNamespace(kind=kind, frozen_source=tmp_path))
    assert seen['plan_schema'] == 'scienceutopia.native-workflow-objective-loop.v1.plan'
    assert seen['preceding_schema'] == 'scienceutopia.native-workflow-objective-loop-finish.v1'
    assert seen['continuation_schema'] == 'scienceutopia.native-workflow-' + kind + '-finish.v1'
    if kind == 'requests': assert seen['report_extra_arguments'] == ()
    else:
        assert seen['report_extra_arguments'][:2] == ('--frozen-source', str(tmp_path.resolve()))
        assert seen['report_extra_arguments'][-1] == ('workflow-development' if kind == 'choices' else 'workflow-objective-development')
    assert effects.SCOPES['workflow-objective-development'] in requests.AUDITS


def test_cold_cli_binds_all_relative_paths_in_caller_not_child_directory(tmp_path, monkeypatch):
    import subprocess
    import sys
    seen = {}
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv('SCIENCE_UTOPIA_COLD_PLANNING_CHOICES_WORKER', raising=False)
    monkeypatch.setattr(sys, 'argv', ['reader', '--run', 'raw', '--frozen-source', 'science',
        '--audit-one', 'audit-one.json', '--audit-two', 'audit-two.json', '--output', 'outputs/readout',
        '--study', 'workflow-development'])
    def launch(argv, **kwargs):
        seen.update(argv=argv, **kwargs)
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(subprocess, 'run', launch)
    choices.main()
    assert seen['cwd'] == tmp_path / 'science'
    for flag, value in (('--run', 'raw'), ('--frozen-source', 'science'),
            ('--audit-one', 'audit-one.json'), ('--audit-two', 'audit-two.json'),
            ('--output', 'outputs/readout')):
        position = seen['argv'].index(flag)
        assert seen['argv'][position + 1] == str((tmp_path / value).resolve())
