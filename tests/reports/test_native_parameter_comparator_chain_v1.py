"""Trusted finite scheduling: no science before verified upstream closure."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import chain_native_parameter_comparator_v1 as chain
from scripts.run_native_parameter_comparator_v1 import save
from utopia.system.design_patch import digest


def fixture(tmp_path, monkeypatch):
    args = SimpleNamespace(run=tmp_path / 'numeric-source/outputs/numeric', frozen_source=tmp_path / 'numeric-source',
        wait_run=tmp_path / 'previous-source/outputs/previous', wait_source=tmp_path / 'previous-source',
        wait_analysis=tmp_path / 'previous-analysis', output=tmp_path / 'chain', wait_writer_pid=101, wait_analysis_pid=102)
    save(args.run / 'plan.json', {'schema': 'scienceutopia.native-parameter-comparator.v1.plan', 'source_commit': 'n' * 40})
    save(args.wait_run / 'plan.json', {'schema': 'scienceutopia.native-parent-presentation-loop.v1.plan', 'source_commit': 'p' * 40})
    old = chain.read(args.wait_run / 'plan.json')
    save(args.wait_run / 'started.json', {'pid': 101, 'plan_sha256': old['content_sha256']})
    save(args.wait_run / 'terminal.json', {'status': 'closed'})
    args.wait_analysis.mkdir()
    chain.save(args.wait_analysis / 'started.json', {'scientific_source_commit': 'p' * 40, 'writer_pid': 101})
    audit = {'schema': 'scienceutopia.native-parent-presentation-loop-audit.v1', 'source_commit': 'p' * 40,
        'plan_sha256': old['content_sha256'], 'source_proof': {'status': 'verified-exact-source-closure'},
        'closure': {'started': chain.read(args.wait_run / 'started.json'), 'terminal': chain.read(args.wait_run / 'terminal.json')},
        'raw_inventory_sha256': digest(chain._inventory(args.wait_run)), 'new_model_calls': 0, 'new_code_executions': 0}
    for i in (1, 2):
        save(args.wait_analysis / ('audit-' + str(i) + '.json'), audit)
        save(args.wait_analysis / ('costs-' + str(i) + '.json'), {'SCRIPTED': 'same costs'})
    chain.save(args.wait_analysis / 'ended.json', {'status': 'closed',
        'audit_file_sha256': chain.sha(args.wait_analysis / 'audit-1.json'),
        'cost_file_sha256': chain.sha(args.wait_analysis / 'costs-1.json')})
    monkeypatch.setattr(chain, 'git_binding', lambda path: ('n' * 40 if Path(path) == args.frozen_source else
        'p' * 40 if Path(path) == args.wait_source else 'a' * 40))
    return args


def test_waits_for_both_original_identities_then_one_numeric_run_and_two_each_readouts(tmp_path, monkeypatch):
    args = fixture(tmp_path, monkeypatch); ticks = [0]; calls = []
    def observe(pid):
        if pid == 101 and ticks[0] < 2: return 'scripts.run_native_parent_presentation_loop_v1 run original'
        if pid == 102 and ticks[0] < 3: return 'scripts.finish_native_parent_presentation_loop_v1 original'
        return None
    def poll(seconds): ticks[0] += 1
    def command(cmd, **kw):
        assert ticks[0] >= 3 and kw['cwd'] == args.frozen_source
        calls.append(cmd); module = cmd[2]
        assert kw['env']['PYTHONHASHSEED'] == '42'
        if module == 'scripts.run_native_parameter_comparator_v1':
            assert 'timeout' not in kw
            save(args.run / 'started.json', {'SCRIPTED': 'one new scientific dispatch'})
        elif module == 'scripts.reports.native_parameter_comparator_v1':
            out = Path(cmd[cmd.index('--output') + 1]); out.mkdir()
            chain.save(out / 'report.json', {'SCRIPTED': 'same report'})
        else:
            save(Path(cmd[cmd.index('--output') + 1]), {'SCRIPTED': 'same cold projection', 'module': module})
        return SimpleNamespace(returncode=0)
    chain.run(args, observe=observe, poll=poll, clock=lambda: ticks[0], command=command)
    assert len(calls) == 7
    end = json.loads((args.output / 'ended.json').read_text())
    assert end['status'] == 'closed' and not end['publication_ready'] and not end['research_goal_complete']
    assert len(end['steps']) == 7
    with pytest.raises(ValueError, match='unconsumed'): chain.run(args, observe=observe, command=command)


@pytest.mark.parametrize('fault', ['writer-gone', 'writer-other', 'analysis-stopped', 'audit-different', 'raw-changed', 'cost-different'])
def test_no_next_inference_after_missing_stopped_changed_or_unaudited_upstream(tmp_path, monkeypatch, fault):
    args = fixture(tmp_path, monkeypatch)
    if fault == 'writer-gone': (args.wait_run / 'terminal.json').unlink()
    if fault == 'analysis-stopped':
        (args.wait_analysis / 'ended.json').unlink(); chain.save(args.wait_analysis / 'ended.json', {'status': 'stopped'})
    if fault == 'audit-different':
        (args.wait_analysis / 'audit-2.json').unlink()
        save(args.wait_analysis / 'audit-2.json', {'SCRIPTED': 'different'})
    if fault == 'raw-changed': save(args.wait_run / 'unexpected.json', {'SCRIPTED': 'new raw after audit'})
    if fault == 'cost-different':
        (args.wait_analysis / 'costs-2.json').unlink()
        save(args.wait_analysis / 'costs-2.json', {'SCRIPTED': 'different'})
    def observe(pid): return 'unrelated PID owner' if fault == 'writer-other' and pid == 101 else None
    with pytest.raises(ValueError):
        chain.run(args, observe=observe, command=lambda *a, **k: pytest.fail('unsafe next inference'))
    assert not (args.run / 'started.json').exists()


def test_failed_numeric_stage_is_not_retried_or_followed_by_successful_analysis(tmp_path, monkeypatch):
    args = fixture(tmp_path, monkeypatch); calls = []
    def fail(cmd, **kw): calls.append(cmd); return SimpleNamespace(returncode=1)
    with pytest.raises(ValueError, match='never retry'):
        chain.run(args, observe=lambda pid: None, command=fail)
    assert len(calls) == 1
    end = json.loads((args.output / 'ended.json').read_text())
    assert end['status'] == 'stopped' and end['stage'] == 'numeric-run' and not end['science_restarted']
    assert not list(args.output.glob('audit-*.started.json'))


def test_timeout_observing_a_live_analysis_leaves_original_and_next_science_untouched(tmp_path, monkeypatch):
    args = fixture(tmp_path, monkeypatch); (args.wait_analysis / 'ended.json').unlink(); ticks = [0]
    def poll(seconds): ticks[0] += 86401
    identity = 'scripts.finish_native_parent_presentation_loop_v1 original'
    with pytest.raises(ValueError, match='finite analysis wait'):
        chain.run(args, observe=lambda pid: identity if pid == 102 else None, poll=poll, clock=lambda: ticks[0],
            command=lambda *a, **k: pytest.fail('no next scientific dispatch'))
    assert not (args.run / 'started.json').exists()
