"""Scripted safety/accounting checks; zero real model or generated-code calls."""
import json
from pathlib import Path

import pytest
from scripts import diagnose_native_reasoning_budget_v41 as h
from tests.optimization.test_native_designer_contract_v16 import Response
from utopia.optimization.native_designer_tools_v25 import response_message_from_action


class Session:
    def __init__(self, outcomes, output=None):
        self.outcomes, self.output, self.posts = outcomes, output, []

    def post(self, url, **kwargs):
        index = len(self.posts)
        if self.output:
            assert (self.output / f'call-{index:02d}.started.json').exists()
        payload = json.loads(kwargs['data']); self.posts.append(payload)
        assert url == 'http://127.0.0.1:11434/api/chat' and kwargs['timeout'] == (10, 900)
        outcome = self.outcomes[index]
        if outcome == 'timeout':
            raise TimeoutError('SCRIPTED no response/cost counters')
        if outcome == 'interrupt':
            raise KeyboardInterrupt('SCRIPTED interrupted call')
        action = {'tool': 'plan', 'objective_reasoning': 'SCRIPTED arithmetic', 'design_intent': 'SCRIPTED intent'}
        if outcome == 'wrong-tool':
            action = {'tool': 'read_file', 'filename': 'system.json'}
        body = {'model': 'SCRIPTED-model' if outcome != 'foreign' else 'foreign-model',
            'done': True, 'done_reason': 'length' if outcome == 'length' else 'stop',
            'message': response_message_from_action(action), 'prompt_eval_count': 100, 'eval_count': 20}
        if outcome == 'length':
            body['message'].update(content='', thinking='SCRIPTED reasoning only')
            body['eval_count'] = 8192
        if outcome == 'eof':
            result = Response({'error': 'EOF'}); result.status_code = 500
            def fail():
                raise RuntimeError('SCRIPTED HTTP500')
            result.raise_for_status = fail
            return result
        return Response(body)


@pytest.mark.parametrize('outcome', ['success', 'length', 'wrong-tool', 'foreign', 'eof', 'timeout', 'interrupt'])
def test_completion_plan_schema_and_unknown_costs_are_not_salvaged(outcome):
    session = Session([outcome])
    result = h.dispatch(session, {'model': 'SCRIPTED-model'}, {'model': 'SCRIPTED-model', 'think': True})
    assert len(session.posts) == 1 and result['action_applied'] is False
    assert result['technical_success'] is (outcome == 'success')
    if outcome == 'length':
        assert result['complete_envelope'] is False and result['content_characters'] == 0
        assert result['costs']['eval_count'] == 8192 and result['plan_schema_valid'] is False
    if outcome in ('eof', 'timeout', 'interrupt'):
        assert result['costs'] == {'prompt_eval_count': None, 'eval_count': None}
    assert result.get('interrupted', False) is (outcome == 'interrupt')


@pytest.fixture
def value(tmp_path, monkeypatch):
    raw = tmp_path / 'original'; raw.mkdir(); (raw / 'evidence.txt').write_text('SCRIPTED immutable')
    monkeypatch.setattr(h, 'pinned_revision', lambda _: 'a' * 40)
    monkeypatch.setattr(h, 'runtime_binding', lambda: {'SCRIPTED': '1' * 64})
    monkeypatch.setattr(h, 'backend_binding', lambda *a: {'SCRIPTED-backend': 'fixed'})
    result = {'raw_root': str(raw), 'source_commit': 'a' * 40, 'runtime': h.runtime_binding(),
        'provider': {'model': 'SCRIPTED-model'}, 'backend': {'SCRIPTED-backend': 'fixed'},
        'payload': {'model': 'SCRIPTED-model', 'think': True, 'options': {'seed': 42, 'num_predict': 8192}},
        'maximum_POSTs': 2, 'calls': [{'ordinal': i, 'think': mode} for i, mode in enumerate(h.MODES)],
        'closure': {'raw_inventory': h.archive._inventory(raw), 'input_files': {}}}
    result['content_sha256'] = h.digest(result)
    return result


def test_fixed_two_calls_change_only_think_and_never_resume(value, tmp_path, monkeypatch):
    def forbidden(*args, **kwargs):
        raise AssertionError('no action interpretation or generated code execution')
    monkeypatch.setattr('utopia.optimization.native_staged_author_v15.transition', forbidden)
    output = tmp_path / 'probe'; session = Session(['length', 'success'], output)
    result = h.run(value, output, session=session)
    assert result['recorded_attempts'] == result['completed_receipts'] == len(session.posts) == 2
    old, new = session.posts
    assert old['think'] is True and new['think'] is False
    assert {k: v for k, v in old.items() if k != 'think'} == {k: v for k, v in new.items() if k != 'think'}
    assert result['actions_applied'] == result['native_worlds'] == 0
    assert result['original_files_unchanged'] is True
    with pytest.raises(FileExistsError):
        h.run(value, output, session=session)
    assert len(session.posts) == 2


def test_interrupted_intent_is_charged_and_not_redispatched(value, tmp_path):
    output = tmp_path / 'interrupted'; session = Session(['interrupt'], output)
    with pytest.raises(KeyboardInterrupt):
        h.run(value, output, session=session)
    summary = json.loads((output / 'summary.json').read_text())
    assert summary['recorded_attempts'] == summary['completed_receipts'] == 1
    assert len(session.posts) == 1


def test_original_evidence_change_is_detected(value, tmp_path):
    Path(value['raw_root'], 'evidence.txt').write_text('SCRIPTED changed')
    with pytest.raises(ValueError, match='original evidence changed'):
        h.run(value, tmp_path / 'changed', session=Session(['success', 'success']))


@pytest.mark.parametrize('field, replacement', [('calls', []), ('maximum_POSTs', 3), ('content_sha256', '0' * 64)])
def test_forged_or_expanded_probe_rejects_before_post(value, tmp_path, field, replacement):
    value[field] = replacement
    if field != 'content_sha256':
        value['content_sha256'] = h.digest({k: v for k, v in value.items() if k != 'content_sha256'})
    session = Session([])
    with pytest.raises(ValueError):
        h.run(value, tmp_path / 'bad', session=session)
    assert session.posts == []
