"""Conditional command-profile checks. All fixtures here are SCRIPTED, not worlds."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.reports import native_reserve_response_v1 as module
from utopia.optimization.native_numeric_designer import checked, save
from utopia.system.code_mechanisms import sha
from utopia.system.design_patch import digest


def frame(year=1):
    artifact = {'source': 'SCRIPTED mock executor never executes this string'}
    context = {'period': year, 'parameters': {'reserve_units': 21, 'allocation_rule': 'reserve-proximity'},
        'inputs': {'world': [{'payload': {'ecosystem': {'agents': [
            {'id': 'donor', 'can_author': True, 'is_active': True, 'resources': 40., 'project_end_year': 2},
            {'id': 'recipient', 'can_author': True, 'is_active': True, 'resources': 15., 'project_end_year': 2}]}}}]}}
    result = {'outputs': {'funds': [{'payload': {'from_actor': 'donor', 'to_actor': 'recipient', 'amount': 6, 'transaction_id': 'one'}}]},
        'state': {'period': year}}
    return {'artifact': artifact, 'context': context, 'result': result,
        'receipt': {**{k + '_sha256': sha(v) for k, v in [('artifact', artifact), ('context', context), ('result', result)]},
            'image_id': 'sha256:' + 'a' * 64}}


def test_command_summary_never_commits_native_balances_or_claims_an_outcome():
    f = frame(); before = deepcopy(f); result = module.command_summary(f['result'], f)
    assert result['requested_units'] == 6 and result['recipient_count'] == result['command_count'] == 1
    assert f == before and not any(k in result for k in ('loss', 'active_after', 'balance_after'))
    assert module.command_summary({'outputs': {'funds': []}}, f)['requested_units'] == 0


@pytest.mark.parametrize('change', ['bool', 'zero', 'negative', 'overspend', 'self', 'unknown', 'duplicate'])
def test_invalid_conserving_command_summary_is_not_repaired(change):
    f = frame(); payload = f['result']['outputs']['funds'][0]['payload']
    if change == 'bool': payload['amount'] = True
    elif change == 'zero': payload['amount'] = 0
    elif change == 'negative': payload['amount'] = -1
    elif change == 'overspend': payload['amount'] = 41
    elif change == 'self': payload['to_actor'] = 'donor'
    elif change == 'unknown': payload['to_actor'] = 'not-a-recorded-author'
    else: f['result']['outputs']['funds'].append(deepcopy(f['result']['outputs']['funds'][0]))
    with pytest.raises(ValueError): module.command_summary(f['result'], f)


def test_intervals_preserve_disjoint_equal_outputs_and_reject_gaps():
    rows = [{'reserve_units': i, 'transfer_payload_sha256': value, 'command_count': 0,
        'recipient_count': 0, 'requested_units': 0} for i, value in enumerate(['a', 'a', 'b', 'a'], 1)]
    result = module.intervals(rows)
    assert [(r['lower'], r['upper']) for r in result] == [(1, 2), (3, 3), (4, 4)]
    with pytest.raises(ValueError, match='unobserved gap'): module.intervals([rows[0], rows[2]])


def setup(tmp_path, monkeypatch):
    root, old, out = [tmp_path / n for n in ('raw', 'original-source', 'profile')]
    old_file = old / 'utopia/system/code_mechanisms.py'; old_file.parent.mkdir(parents=True)
    old_file.write_bytes((module.ROOT / 'utopia/system/code_mechanisms.py').read_bytes())
    context = root / ('references/' + module.REFERENCE + '/worlds/reference-' + module.REFERENCE + '-s61001/code-contexts.jsonl')
    context.parent.mkdir(parents=True); frames = [frame(y) for y in range(1, 5)]
    context.write_text(''.join(json.dumps(f) + '\n' for f in frames))
    inventory = {'SCRIPTED': 'mock raw inventory, not actual audit evidence'}
    plan = save(root / 'plan.json', {'source_commit': 'a' * 40,
        'reference_systems': {module.REFERENCE: {'mechanisms': [{'mechanism_id': 'developer-liquidity-director', 'parameters': {'code_artifact': frames[0]['artifact']}}]}}})
    audit = {'schema': 'scienceutopia.native-planning-objective-loop-audit.v1', 'source_commit': 'a' * 40,
        'plan_sha256': plan['content_sha256'], 'closure': {'terminal': {'status': 'closed'}},
        'source_proof': {'status': 'verified-exact-source-closure', 'SCRIPTED': 'mocked, no source-bound native proof'},
        'raw_inventory_sha256': digest(inventory), 'raw_files': 1}
    audits = [tmp_path / ('audit-' + str(i) + '.json') for i in (1, 2)]
    for path in audits: save(path, deepcopy(audit))
    monkeypatch.setattr(module, '_inventory', lambda p: inventory)
    monkeypatch.setattr(module, 'pinned_revision', lambda p: 'a' * 40 if p == old else 'b' * 40)
    calls = []
    class Executor:
        def __init__(self, **kw): self.image_id = frames[0]['receipt']['image_id']
        def execute(self, artifact, context):
            calls.append(deepcopy(context)); result = deepcopy(frames[context['period'] - 1]['result'])
            return SimpleNamespace(result=result, receipt={'SCRIPTED': True, 'artifact_sha256': sha(artifact), 'context_sha256': sha(context), 'result_sha256': sha(result)})
    monkeypatch.setattr(module, 'DockerCodeExecutor', Executor)
    args = SimpleNamespace(run=root, scientific_source=old, audit_one=audits[0], audit_two=audits[1], output=out)
    return args, frames, calls


def test_complete_mock_profile_keeps_full_input_bytes_except_one_parameter(tmp_path, monkeypatch):
    args, frames, calls = setup(tmp_path, monkeypatch); module.run(args)
    assert len(calls) == 240
    for context in calls:
        original = frames[context['period'] - 1]['context']; modified = deepcopy(context)
        modified['parameters']['reserve_units'] = 21; assert modified == original
    result = checked(json.loads((args.output / 'report.json').read_text()))
    assert result['new_code_executions'] == 240 and result['original_reserve21_replays_match']
    assert not result['interpretation']['native_transfer_commit_reexecuted']
    assert not result['interpretation']['loss_improvement_inferred_from_commands']
    assert result['interpretation']['new_native_worlds'] == result['interpretation']['new_model_calls'] == 0
    assert len(list((args.output / 'calls').glob('*.started.json'))) == 240
    assert len((args.output / 'response.csv').read_text().splitlines()) == 241
    assert b'\r\n' not in (args.output / 'response.csv').read_bytes()
    assert len(result['frames']) == 4 and all(f['distinct_transfer_outputs'] == 1 for f in result['frames'])


def test_failed_execution_stops_once_without_making_a_completed_report(tmp_path, monkeypatch):
    args, _, _ = setup(tmp_path, monkeypatch); calls = []
    class Fails:
        def __init__(self, image, **kw): self.image_id = image
        def execute(self, *a): calls.append(1); raise TimeoutError('SCRIPTED component timeout')
    monkeypatch.setattr(module, 'DockerCodeExecutor', Fails)
    with pytest.raises(TimeoutError): module.run(args)
    end = checked(json.loads((args.output / 'ended.json').read_text()))
    assert len(calls) == 1 and end['status'] == 'stopped'
    assert end['attempted_component_executions'] == 1 and end['completed_component_executions'] == 0
    assert not (args.output / 'report.json').exists()
    assert len(list((args.output / 'calls').glob('*.started.json'))) == 1


def test_wrong_execution_image_is_not_used_even_for_a_conditional_diagnostic(tmp_path, monkeypatch):
    args, _, _ = setup(tmp_path, monkeypatch)
    class Wrong:
        def __init__(self, **kw): self.image_id = 'sha256:' + 'f' * 64
        def execute(self, *a): pytest.fail('wrong image must never execute')
    monkeypatch.setattr(module, 'DockerCodeExecutor', Wrong)
    with pytest.raises(ValueError, match='execution image differs'): module.run(args)
    assert not args.output.exists()
