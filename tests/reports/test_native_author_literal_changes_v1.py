"""SCRIPTED journal analysis checks, never new native-world evidence."""
from copy import deepcopy
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.reports import native_author_literal_changes_v1 as report
from tests.optimization.test_native_literal_change_observation_v1 import document
from tests.reports.test_native_author_step_summary_v1 import session
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256


def fixture():
    before = document(); after = deepcopy(before)
    after['mechanisms'][0]['parameters']['code_artifact']['source'] = (
        '# SCRIPTED different text, same AST\n' + before['mechanisms'][0]['parameters']['code_artifact']['source'])
    def intent(i, doc):
        return {'step': i, 'prompt': json.dumps({'literal_current_system': doc, 'current_system_sha256': digest(doc)})}
    steps = [{'step': 0, 'status': 'applied', 'content_sha256': 'SCRIPTED receipt',
        'model_reply': {'output': {'tool': 'write_file'}},
        'transition': {'tool': 'write_file', 'ok': True,
            'document_before_sha256': digest(before), 'document_after_sha256': digest(after)}}]
    return [intent(0, before), intent(1, after)], steps


def test_literal_changes_project_without_executing_or_repairing_source():
    intents, steps = fixture(); saved = deepcopy((intents, steps))
    result = report.project(intents, steps); row, = result['edits']
    assert row['status'] == 'observed-literal-before-and-next-view'
    change, = row['diagnostic']['node_changes']
    assert change['standard_python_AST_equal'] is True
    assert row['diagnostic']['literal_document_changed']
    assert (intents, steps) == saved and not row['diagnostic']['veto_on_finish']


@pytest.mark.parametrize('kind', ['last-edit', 'retrieval-only', 'non-json-prompt', 'null-document'])
def test_missing_full_next_document_is_unassessed_not_zero_changes(kind):
    intents, steps = fixture()
    if kind == 'last-edit': intents.pop()
    elif kind == 'retrieval-only': intents[1]['prompt'] = {'current_system_sha256': 'SCRIPTED pointer'}
    elif kind == 'non-json-prompt': intents[1]['prompt'] = 'SCRIPTED no full document'
    else: intents[1]['prompt'] = {'literal_current_system': None}
    row, = report.project(intents, steps)['edits']
    assert row['status'] == 'literal-before-or-next-view-unavailable' and row['diagnostic'] is None


@pytest.mark.parametrize('kind', ['before-identity', 'after-identity', 'receipt-before', 'receipt-after'])
def test_mismatched_original_bindings_stop_analysis_not_become_a_scientific_null(kind):
    intents, steps = fixture()
    if kind.startswith('receipt'):
        steps[0]['transition']['document_' + kind.split('-')[1] + '_sha256'] = 'SCRIPTED mismatch'
    else:
        i = 0 if kind.startswith('before') else 1
        prompt = json.loads(intents[i]['prompt']); prompt['current_system_sha256'] = 'SCRIPTED mismatch'
        intents[i]['prompt'] = prompt
    with pytest.raises(ValueError): report.project(intents, steps)


@pytest.mark.parametrize('kind', ['rejected', 'malformed-tool', 'failed-transition'])
def test_unsuccessful_edits_stay_visible_without_an_implementation_verdict(kind):
    intents, steps = fixture(); steps[0]['status'] = 'invalid-response'
    if kind == 'rejected': steps[0]['transition'] = None
    elif kind == 'malformed-tool':
        steps[0]['model_reply']['output']['tool'] = []
        steps[0]['transition']['ok'] = False
    else: steps[0]['transition']['ok'] = False
    result = report.project(intents, steps); row, = result['edits']
    assert result['edit_attempts'] == 1 and row['diagnostic'] is None
    assert row['status'] == 'not-applied-no-change-verdict'


def test_non_edit_steps_do_not_become_an_edit_or_zero_change_claim():
    intents, steps = fixture(); steps[0]['transition'] = None
    steps[0]['model_reply']['output'] = {'tool': []}
    assert report.project(intents, steps)['edits'] == []
    steps[0]['step'] = 2
    with pytest.raises(ValueError): report.project(intents, steps)


def test_collect_uses_original_full_chain_and_retains_unavailable_views(tmp_path):
    session(tmp_path)
    before = {str(p): file_sha256(p) for p in tmp_path.iterdir()}
    result = report.collect(tmp_path)
    assert result['terminal_status'] == 'generated' and result['completed_steps'] == 4
    assert result['original_file_sha256'] == before
    assert result['edit_attempts'] == 0 and not result['full_native_cold_replay']
    assert before == {str(p): file_sha256(p) for p in tmp_path.iterdir()}


def test_pending_original_session_cannot_be_presented_as_a_closed_export(tmp_path):
    session(tmp_path, pending=True)
    with pytest.raises(ValueError, match='closed original session'): report.collect(tmp_path)


def test_changed_original_journal_is_not_repaired_or_replayed(tmp_path):
    session(tmp_path)
    p = tmp_path / 'step-01.started.json'
    p.write_text(p.read_text() + '\n')
    with pytest.raises(ValueError): report.collect(tmp_path)


@pytest.mark.parametrize('target', ['reader', 'scientific', 'session', 'existing', 'duplicate'])
def test_export_rejects_unsafe_output_before_reading_or_writing(tmp_path, monkeypatch, target):
    reader = tmp_path / 'reader'; scientific = tmp_path / 'science'; raw = tmp_path / 'journal'
    for p in (reader, scientific, raw): p.mkdir()
    monkeypatch.setattr(report, 'ROOT', reader)
    def forbidden(*args): raise AssertionError('no source or journal read before path preflight')
    monkeypatch.setattr(report, 'pinned_revision', forbidden)
    out = {'reader': reader / 'out.json', 'scientific': scientific / 'out.json',
        'session': raw / 'out.json'}.get(target, tmp_path / 'output.json')
    if target == 'existing': out.write_text('SCRIPTED retained bytes')
    args = SimpleNamespace(origin_source=scientific, session=[raw, raw] if target == 'duplicate' else [raw], output=out)
    with pytest.raises(ValueError): report.export(args)


def test_public_export_roundtrip_keeps_source_binding_and_explicit_non_claims(tmp_path, monkeypatch):
    reader = tmp_path / 'reader'; scientific = tmp_path / 'science'; raw = tmp_path / 'journal'
    for p in (reader, scientific, raw): p.mkdir()
    session(raw); monkeypatch.setattr(report, 'ROOT', reader)
    monkeypatch.setattr(report, 'pinned_revision', lambda p: 'SCRIPTED-' + Path(p).name)
    args = SimpleNamespace(origin_source=scientific, session=[raw], output=tmp_path / 'report.json')
    first = report.export(args); second_args = SimpleNamespace(**{**vars(args), 'output': tmp_path / 'report-two.json'})
    second = report.export(second_args)
    assert first == second == report.checked(json.loads(args.output.read_text()))
    assert first['analysis_source_commit'] == 'SCRIPTED-reader'
    assert all(first[k] == 0 for k in ('new_model_calls', 'new_native_worlds', 'new_probe_attempts',
        'new_authored_source_executions', 'new_author_prompts_exposing_this_diagnostic'))
    assert all(first[k] is False for k in ('source_repair', 'veto_on_finish', 'changes_loss', 'publication_ready'))


def test_source_change_during_export_prevents_output(tmp_path, monkeypatch):
    reader = tmp_path / 'reader'; scientific = tmp_path / 'science'; raw = tmp_path / 'journal'
    for p in (reader, scientific, raw): p.mkdir()
    session(raw); monkeypatch.setattr(report, 'ROOT', reader)
    calls = iter(['SCRIPTED-reader', 'SCRIPTED-science', 'SCRIPTED-changed', 'SCRIPTED-science'])
    monkeypatch.setattr(report, 'pinned_revision', lambda p: next(calls))
    out = tmp_path / 'report.json'
    with pytest.raises(ValueError, match='source changed'):
        report.export(SimpleNamespace(origin_source=scientific, session=[raw], output=out))
    assert not out.exists()
