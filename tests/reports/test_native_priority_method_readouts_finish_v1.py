"""SCRIPTED finite metadata/process tests, no inference or plotting imports."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import finish_native_code_tested_report_v1 as base
from scripts import finish_native_priority_method_readouts_v1 as module
from utopia.optimization.native_numeric_designer import save


@pytest.mark.parametrize('location', ['reader', 'science', 'raw', 'analysis', 'symlink', 'existing'])
def test_preflight_before_any_wait_or_mkdir(tmp_path, monkeypatch, location):
    paths = {name: tmp_path / name for name in ('reader', 'science', 'raw', 'analysis')}
    for path in paths.values(): path.mkdir()
    monkeypatch.setattr(module, 'ROOT', paths['reader'])
    def forbidden(*a, **k): raise AssertionError('must stop before inherited continuation')
    monkeypatch.setattr(module, 'finish', forbidden)
    if location == 'symlink':
        alias = tmp_path / 'alias'; alias.symlink_to(paths['reader'], target_is_directory=True)
        output = alias / 'new'
    elif location == 'existing':
        output = tmp_path / 'existing'; output.mkdir()
    else: output = paths[location] / 'new'
    args = SimpleNamespace(run=paths['raw'], analysis=paths['analysis'],
        frozen_source=paths['science'], output=output)
    with pytest.raises(ValueError, match='before waiting'): module.run(args)
    if location != 'existing': assert not output.exists()


@pytest.mark.parametrize('fail', [None, 'closure', 'report-1', 'report-2', 'different-bytes'])
def test_exact_chain_two_exports_or_preserved_stop(tmp_path, monkeypatch, fail):
    raw = tmp_path / 'raw'; raw.mkdir(); analysis = tmp_path / 'analysis'; analysis.mkdir()
    source = tmp_path / 'science'; source.mkdir()
    save(raw / 'plan.json', {'schema': 'scienceutopia.native-priority-method-comparison.v1.plan',
        'source_commit': 'a' * 40})
    save(analysis / 'started.json', {'schema': 'scienceutopia.native-priority-method-comparison.v1.finish',
        'scientific_source_commit': 'a' * 40, 'plan_file_sha256': base.sha(raw / 'plan.json')})
    (analysis / 'ended.json').write_text('SCRIPTED closed')
    monkeypatch.setattr(base, 'git_binding', lambda root: 'b' * 40)
    monkeypatch.setattr(module, 'ROOT', tmp_path / 'reader')
    def wait(directory):
        if fail == 'closure': raise ValueError('SCRIPTED stopped closure')
        return {'audit_file_sha256': 'c' * 64, 'cost_file_sha256': 'd' * 64}
    monkeypatch.setattr(base, 'wait_analysis', wait)
    calls = []
    def execute(argv, **kwargs):
        assert argv[2] == 'scripts.reports.native_priority_method_readout_v1'
        for key, value in (('frozen-source', source), ('cost-one', analysis / 'costs-1.json'),
                           ('cost-two', analysis / 'costs-2.json')):
            assert argv[argv.index('--' + key) + 1] == str(value.resolve())
        output = Path(argv[argv.index('--output') + 1]); calls.append(output.name)
        assert (output.parent / (output.name + '.started.json')).exists()
        if fail == output.name: return SimpleNamespace(returncode=2)
        output.mkdir(); (output / 'SCRIPTED.json').write_text(output.name if fail == 'different-bytes' else 'matching')
        return SimpleNamespace(returncode=0)
    monkeypatch.setattr(base.subprocess, 'run', execute)
    args = SimpleNamespace(run=raw, analysis=analysis, frozen_source=source, output=tmp_path / 'out')
    if fail:
        with pytest.raises(ValueError): module.run(args)
    else: module.run(args)
    assert calls == ([] if fail == 'closure' else ['report-1'] if fail == 'report-1' else ['report-1', 'report-2'])
    end = json.loads((args.output / 'ended.json').read_text())
    assert end['status'] == ('stopped' if fail else 'closed')
    if not fail:
        assert end['new_model_calls'] == 0 and end['new_native_worlds'] == 0
        assert not end['publication_ready'] and not end['visual_review_complete']
    with pytest.raises(ValueError): module.run(args)
