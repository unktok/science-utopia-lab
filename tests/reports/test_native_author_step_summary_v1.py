"""SCRIPTED journal projection checks; no native replay, model or code execution."""
import json

import pytest

from scripts.reports.native_author_step_summary_v1 import read_session, summarize_steps
from utopia.optimization.native_numeric_designer import save
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256, write_json_atomic


def step(i, tool, *, filename='code/a.py', value='literal code', document='a', status='applied'):
    result = {'filename': filename, 'path': '/source/' + filename,
        'resource': 'draft', 'selection': {'offset': 0, 'limit': 65536},
        'descriptor': {'type': 'string'}, 'value': value, 'value_included': True,
        'complete': True, 'slice_reaches_end': True, 'content_sha256': digest(value)}
    return {'schema': 'scienceutopia.staged-author-step.v15', 'step': i,
        'status': status, 'errors': [], 'model_reply': {'output': {'tool': tool}},
        'transition': {'tool': tool, 'ok': True, 'errors': [], 'result': result,
            'document_before_sha256': document, 'document_after_sha256': document}}


def test_every_step_and_nonconsecutive_full_read_loop_are_counted_not_just_tail():
    steps = [step(0, 'plan'), step(1, 'read_file'), step(2, 'read_file', filename='code/b.py'),
        step(3, 'read_file'), step(4, 'write_file'), step(5, 'finish', status='finished')]
    steps[4]['transition']['document_after_sha256'] = 'b'
    result = summarize_steps(steps)
    assert result['completed_steps'] == 6 and len(result['steps']) == 6
    assert result['attempted_edit_steps'] == result['successful_document_changes'] == 1
    assert result['duplicate_unchanged_read_observations'] == 1
    assert result['largest_identical_read_class'] == 2
    assert result['steps'][3]['read']['previous_identical_observations'] == 1
    assert result['explicit_finish_observed']


@pytest.mark.parametrize('changed', ['document', 'value', 'slice', 'descriptor'])
def test_different_observed_document_value_slice_or_address_is_not_a_repeat(changed):
    steps = [step(0, 'read_file'), step(1, 'read_file')]
    target = steps[1]['transition']
    if changed == 'document': target['document_after_sha256'] = 'b'
    elif changed == 'value': target['result']['value'] = 'different literal code'
    elif changed == 'slice': target['result']['selection']['offset'] = 1
    else: target['result']['descriptor'] = {'type': 'other'}
    assert summarize_steps(steps)['duplicate_unchanged_read_observations'] == 0


def test_unknown_document_freshness_does_not_become_an_unchanged_read_claim():
    steps = [step(0, 'read_file'), step(1, 'read_file')]
    for item in steps: item['transition'].pop('document_after_sha256')
    result = summarize_steps(steps)
    assert result['successful_read_observations'] == 2
    assert result['duplicate_unchanged_read_observations'] == 0


@pytest.mark.parametrize('action', [None, [], {'arguments': []}, {'tool': []}])
def test_schema_rejected_actions_remain_errors_without_treating_them_as_tools(action):
    item = step(0, 'read_file'); item.update(transition=None, status='invalid-response', errors=[{'SCRIPTED': True}])
    item['model_reply']['output'] = action
    result = summarize_steps([item])
    assert result['attempted_tool_counts'] == {'<unparsed-action>': 1}
    assert result['steps'][0]['errors'] == [{'SCRIPTED': True}]
    assert result['successful_read_observations'] == result['attempted_edit_steps'] == 0
    assert not result['explicit_finish_observed']


def session(tmp_path, *, pending=False, finish=True):
    binding = {'schema': 'scienceutopia.staged-author-request.v15',
        'request': {'SCRIPTED': 'no actual institution'}, 'settings': {'max_steps': 16}}
    binding['request_sha256'] = digest(binding['request']); binding['binding_sha256'] = digest(binding)
    write_json_atomic(tmp_path / 'request.json', binding)
    steps = []; receipts = []
    tools = ['plan', 'read_file', 'read_file'] if pending else ['plan', 'read_file', 'read_file', 'finish']
    for i, tool in enumerate(tools):
        start = {'schema': 'scienceutopia.staged-author-dispatch.v15', 'step': i,
            'binding_sha256': binding['binding_sha256'], 'prompt': 'SCRIPTED prompt',
            'prompt_sha256': digest('SCRIPTED prompt'), 'previous_steps_sha256': digest(steps)}
        path = tmp_path / f'step-{i:02}.started.json'; write_json_atomic(path, start)
        completed = None
        status = 'interrupted-response-unknown'
        if not (pending and i == len(tools) - 1):
            item = step(i, tool, status='finished' if finish and tool == 'finish' else 'applied')
            item['binding_sha256'] = binding['binding_sha256']
            item['started_file_sha256'] = file_sha256(path)
            completed = tmp_path / f'step-{i:02}.completed.json'; steps.append(save(completed, item)); status = item['status']
        receipts.append({'step': i, 'status': status, 'started_sha256': file_sha256(path),
            'completed_sha256': None if completed is None else file_sha256(completed)})
    terminal = {'schema': 'scienceutopia.staged-author-result.v15',
        'binding_sha256': binding['binding_sha256'], 'request_sha256': binding['request_sha256'],
        'status': 'generated' if finish and not pending else 'generation-failed',
        'selected_step': len(steps) - 1 if finish and not pending else None, 'steps': receipts}
    save(tmp_path / 'response.json', terminal)


@pytest.mark.parametrize('pending', [False, True])
def test_literal_plain_intents_sealed_receipts_terminal_and_unknown_are_distinct(tmp_path, pending):
    session(tmp_path, pending=pending)
    result = read_session(tmp_path)
    assert result['started_calls'] == (3 if pending else 4)
    assert result['completed_steps'] == (2 if pending else 4)
    assert result['started_without_committed_receipt'] == int(pending)
    assert result['terminal_status'] == ('generation-failed' if pending else 'generated')
    assert result['explicit_finish_observed'] is (not pending)
    assert not result['full_native_cold_replay'] and result['new_model_calls'] == 0


@pytest.mark.parametrize('changed', ['binding', 'intent', 'completed', 'terminal', 'terminal-status', 'gap', 'symlink'])
def test_changed_binding_bytes_prefix_or_terminal_cannot_be_presented_as_verified(tmp_path, changed):
    session(tmp_path)
    if changed == 'binding':
        p = tmp_path / 'request.json'; value = json.loads(p.read_text()); value['request']['SCRIPTED'] = 'changed'; write_json_atomic(p, value)
    elif changed == 'intent':
        p = tmp_path / 'step-01.started.json'; p.write_text(p.read_text() + '\n')
    elif changed == 'completed':
        p = tmp_path / 'step-01.completed.json'; value = json.loads(p.read_text()); value['status'] = 'changed'; write_json_atomic(p, value)
    elif changed in ('terminal', 'terminal-status'):
        p = tmp_path / 'response.json'; value = json.loads(p.read_text()); value.pop('content_sha256')
        if changed == 'terminal': value['steps'][1]['completed_sha256'] = 'f' * 64
        else: value['status'] = 'generation-failed'
        value['content_sha256'] = digest(value); write_json_atomic(p, value)
    elif changed == 'gap': (tmp_path / 'step-01.started.json').rename(tmp_path / 'missing-intent.json')
    else:
        p = tmp_path / 'step-01.started.json'; actual = tmp_path / 'linked-intent.json'; p.rename(actual); p.symlink_to(actual)
    with pytest.raises(ValueError): read_session(tmp_path)


def test_missing_terminal_is_an_observed_prefix_not_a_fabricated_terminal(tmp_path):
    session(tmp_path); (tmp_path / 'response.json').rename(tmp_path / 'saved-response-not-at-terminal-path.json')
    result = read_session(tmp_path)
    assert result['explicit_finish_observed'] and not result['terminal_record_present']
    assert result['terminal_status'] is None


def test_resealed_cross_session_step_cannot_pass_only_by_rebinding_its_terminal_hash(tmp_path):
    session(tmp_path)
    p = tmp_path / 'step-03.completed.json'; item = json.loads(p.read_text()); item.pop('content_sha256')
    item['binding_sha256'] = 'f' * 64; item['content_sha256'] = digest(item); write_json_atomic(p, item)
    terminal = tmp_path / 'response.json'; value = json.loads(terminal.read_text()); value.pop('content_sha256')
    value['steps'][3]['completed_sha256'] = file_sha256(p)
    value['content_sha256'] = digest(value); write_json_atomic(terminal, value)
    with pytest.raises(ValueError, match='original intent'): read_session(tmp_path)


def test_nonchronological_completed_projection_is_rejected():
    with pytest.raises(ValueError, match='chronological'): summarize_steps([step(1, 'read_file')])
