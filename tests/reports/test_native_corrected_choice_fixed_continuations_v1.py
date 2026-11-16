"""SCRIPTED process metadata/path guards only; never model/native work."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import supervise_native_corrected_choice_fixed_evaluation_v1 as supervisor
from scripts import supervise_native_corrected_choice_search_v1 as shared_supervisor
from scripts import finish_native_corrected_choice_fixed_evaluation_v1 as closure
from scripts import finish_native_corrected_choice_fixed_readouts_v1 as reports
from utopia.optimization.native_numeric_designer import save


@pytest.mark.parametrize('exit_code', [0, 2])
def test_named_writer_actual_exit_status_and_no_redispatch(tmp_path, monkeypatch, exit_code):
    plan = save(tmp_path / 'plan.json', {'source_commit': 'a' * 40})
    monkeypatch.setattr(supervisor.driver, 'require_plan', lambda root: plan)
    calls = []
    def popen(argv, **kwargs):
        calls.append(argv)
        assert argv[3] == 'scripts.run_native_corrected_choice_fixed_evaluation_v1'
        assert supervisor.driver.read(tmp_path / 'writer-supervision-start.json')['command'] == argv
        return SimpleNamespace(pid=1234, wait=lambda: exit_code)
    monkeypatch.setattr(shared_supervisor.subprocess, 'Popen', popen)
    if exit_code:
        with pytest.raises(SystemExit): supervisor.run(tmp_path)
    else: supervisor.run(tmp_path)
    end = supervisor.driver.read(tmp_path / 'writer-exit.json')
    assert end['schema'] == supervisor.PREFIX + '-exit.v1' and end['exit_code'] == exit_code
    with pytest.raises(ValueError, match='no scientific restart'): supervisor.run(tmp_path)
    assert len(calls) == 1


def args_for(tmp_path):
    roots = {key: tmp_path / key for key in ('reader', 'raw', 'science', 'analysis',
        'origin-run', 'origin-source', 'origin-analysis', 'origin-readouts')}
    for root in roots.values(): root.mkdir()
    save(roots['raw'] / 'plan.json', {'schema': closure.SCHEMA + '.plan',
        'origin': {key: str(roots['origin-' + key]) for key in ('run', 'source', 'analysis', 'readouts')}})
    return roots, SimpleNamespace(run=roots['raw'], frozen_source=roots['science'], analysis=roots['analysis'],
        output=tmp_path / 'external', writer_pid=11)


@pytest.mark.parametrize('module', [closure, reports])
@pytest.mark.parametrize('location', ['reader', 'raw', 'science', 'origin-run', 'origin-source',
    'origin-analysis', 'origin-readouts', 'alias', 'existing'])
def test_output_rejected_before_wait_or_creation(tmp_path, monkeypatch, module, location):
    roots, args = args_for(tmp_path); monkeypatch.setattr(module, 'ROOT', roots['reader'])
    monkeypatch.setattr(module, 'finish', lambda *a, **kw: pytest.fail('must reject before wait'))
    if location == 'alias':
        alias = tmp_path / 'alias'; alias.symlink_to(roots['origin-source'], target_is_directory=True)
        args.output = alias / 'not-created'
    elif location == 'existing': args.output = roots['origin-run']
    else: args.output = roots[location] / 'not-created'
    with pytest.raises(ValueError, match='before waiting'): module.run(args)
    if location != 'existing': assert not args.output.exists()


def test_continuation_contract_has_actual_supervisor_and_paired_cost_bindings(tmp_path, monkeypatch):
    _, args = args_for(tmp_path); calls = []
    for module in (closure, reports):
        monkeypatch.setattr(module, 'finish', lambda a, **kwargs: calls.append(kwargs))
        module.run(args)
    assert calls[0]['writer_wait'].keywords['schema_prefix'] == supervisor.PREFIX
    assert calls[0]['plan_schema'] == calls[1]['plan_schema'] == closure.SCHEMA + '.plan'
    assert calls[0]['audit_module'] == 'scripts.audit_native_corrected_choice_fixed_evaluation_v1'
    assert calls[1]['report_module'] == 'scripts.reports.native_corrected_choice_fixed_evaluation_v1'
    assert '--cost-one' in calls[1]['report_extra_arguments'] and '--cost-two' in calls[1]['report_extra_arguments']
