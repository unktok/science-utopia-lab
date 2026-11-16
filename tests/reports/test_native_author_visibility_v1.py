"""SCRIPTED journals/joins and full native document data, not model/world proof."""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from scripts.reports.native_author_visibility_v1 import prompt_projection, read_visibility, join_visibility
from tests.optimization.test_native_world import loss_spec
from tests.reports.test_native_author_step_summary_v1 import step as completed_step
from utopia.optimization.native_numeric_designer import save
from utopia.optimization.native_objective_view import loss_arithmetic
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256, write_json_atomic

FIXTURES = Path(__file__).resolve().parents[1] / 'fixtures/native_author_context_boundary_v1'


def document(name='parent-terminal'):
    return json.loads((FIXTURES / (name + '.json')).read_text())


def view(*, body=None, index=4, attempts=3, successful=3, maximum=16, phase='general'):
    body = document() if body is None else body
    return {'active_context_contract': {'schema': 'scienceutopia.bounded-author-context.v45',
        'prospective_context_revision': 'matched-bounded-author-64k-v1'},
        '000_current_turn': {'authoring_workflow': {'schema': 'scienceutopia.authoring-workflow.v44',
            'phase': phase, 'inspection_attempts_since_last_draft_change': attempts,
            'successful_inspections_since_last_document_change': successful,
            'remaining_calls_including_this_one': maximum - index, 'submission_reserve': 3,
            'literal_current_system_byte_cap': 65536, 'literal_current_system_included': True}},
        'literal_current_system': body, 'current_system_sha256': digest(body),
        'loss_arithmetic': loss_arithmetic(loss_spec())}


def project(value, *, index=4, maximum=16, previous='applied'):
    return prompt_projection(json.dumps(value, ensure_ascii=False), index=index, maximum=maximum,
        previous_status=previous, expected_loss=loss_arithmetic(loss_spec()))


@pytest.mark.parametrize('name,phase,affected', [('parent-zero', 'implementation', False),
    ('parent-terminal', 'general', True), ('after-feature-write', 'general', True)])
def test_real_full_native_body_shapes_diagnose_old_phase_without_mutating_data(name, phase, affected):
    value = view(body=document(name), phase=phase); before = deepcopy(value); result = project(value)
    assert value == before and result['serializer_visibility_phase_mismatch'] is affected
    assert result['expected_phase_using_actual_body'] == 'implementation'
    assert result['supplied_body_matches_declared_document_hash']


def test_checkpoint_uses_attempts_not_only_successes():
    result = project(view(attempts=3, successful=0))
    assert result['serializer_visibility_phase_mismatch']
    assert result['successful_inspections'] == 0


@pytest.mark.parametrize('index,attempts,expected', [(0, 0, 'planning'),
    (13, 3, 'submit'), (14, 3, 'recovery'), (15, 3, 'submit')])
def test_submission_and_recovery_take_precedence_over_visibility(index, attempts, expected):
    result = project(view(index=index, attempts=attempts, successful=0, phase=expected), index=index)
    assert result['expected_phase_using_actual_body'] == expected
    assert not result['serializer_visibility_phase_mismatch']


def test_custom_maximum_is_read_not_assumed_to_be_sixteen():
    result = project(view(index=7, attempts=3, maximum=10, phase='submit'), index=7, maximum=10)
    assert result['remaining_calls'] == result['submission_reserve'] == 3
    assert not result['phase_differs_from_actual_body_interpretation']


def test_fixed_phase_and_omitted_body_are_not_relabelled_as_old_serializer_failures():
    value = view(phase='implementation')
    value['active_context_contract']['prospective_context_revision'] = 'matched-bounded-author-64k-v2-literal-visibility'
    assert not project(value)['serializer_visibility_phase_mismatch']
    value = view(); value['literal_current_system'] = None
    value['000_current_turn']['authoring_workflow']['literal_current_system_included'] = False
    result = project(value)
    assert result['compact_document_utf8_bytes'] is result['legacy_spaced_document_utf8_bytes'] is None
    assert not result['serializer_visibility_phase_mismatch']


def test_other_phase_flag_hash_and_loss_contradictions_remain_separate_evidence():
    value = view(body={'small': 'document'})
    value['000_current_turn']['authoring_workflow']['literal_current_system_included'] = False
    value['current_system_sha256'] = 'f' * 64; value['loss_arithmetic']['direction'] = 'SCRIPTED different'
    result = project(value)
    assert result['phase_differs_from_actual_body_interpretation']
    assert not result['serializer_visibility_phase_mismatch']
    assert not result['displayed_visibility_matches_body_presence']
    assert not result['supplied_body_matches_declared_document_hash']
    assert not result['exact_loss_arithmetic_and_definitions_present']


@pytest.mark.parametrize('change', ['revision', 'count-bool', 'negative', 'remaining', 'body-type', 'phase'])
def test_unsupported_or_malformed_metadata_is_not_imputed_as_zero_mismatches(change):
    value = view(); flow = value['000_current_turn']['authoring_workflow']
    if change == 'revision': value['active_context_contract']['prospective_context_revision'] = 'unknown'
    elif change == 'count-bool': flow['inspection_attempts_since_last_draft_change'] = True
    elif change == 'negative': flow['successful_inspections_since_last_document_change'] = -1
    elif change == 'remaining': flow['remaining_calls_including_this_one'] += 1
    elif change == 'body-type': value['literal_current_system'] = []
    else: flow['phase'] = 'unknown'
    with pytest.raises(ValueError): project(value)


def journal(path, *, pending=False):
    request = {'loss_spec': loss_spec(), 'generation': 0, 'SCRIPTED': 'no inference'}
    binding = {'schema': 'scienceutopia.staged-author-request.v15', 'request': request,
        'settings': {'max_steps': 16}, 'request_sha256': digest(request)}
    binding['binding_sha256'] = digest(binding); write_json_atomic(path / 'request.json', binding)
    steps = []; references = []
    for i, tool in enumerate(['plan', 'read_file', 'read_file', 'read_file', 'finish']):
        attempts = max(0, i - 1)
        prompt = json.dumps(view(index=i, attempts=attempts, successful=attempts,
            phase='planning' if not i else 'general'))
        start = {'schema': 'scienceutopia.staged-author-dispatch.v15', 'step': i,
            'binding_sha256': binding['binding_sha256'], 'prompt': prompt,
            'prompt_sha256': digest(prompt), 'previous_steps_sha256': digest(steps)}
        sp = path / f'step-{i:02}.started.json'; write_json_atomic(sp, start)
        cp = None
        if not (pending and i == 4):
            item = completed_step(i, tool, status='finished' if i == 4 else 'applied')
            item.update(binding_sha256=binding['binding_sha256'], started_file_sha256=file_sha256(sp))
            cp = path / f'step-{i:02}.completed.json'; saved = save(cp, item); steps.append(saved)
        references.append({'step': i, 'status': 'interrupted-response-unknown' if cp is None else steps[-1]['status'],
            'started_sha256': file_sha256(sp), 'completed_sha256': None if cp is None else file_sha256(cp)})
    if not pending:
        save(path / 'response.json', {'schema': 'scienceutopia.staged-author-result.v15',
            'binding_sha256': binding['binding_sha256'], 'request_sha256': binding['request_sha256'],
            'status': 'generated', 'selected_step': 4, 'steps': references})


@pytest.mark.parametrize('pending', [False, True])
def test_actual_plain_intent_sealed_receipt_api_and_pending_response_unknown(tmp_path, pending):
    journal(tmp_path, pending=pending); result = read_visibility(tmp_path)
    assert result['started_calls'] == 5 and result['completed_steps'] == (4 if pending else 5)
    assert result['uncommitted_responses'] == int(pending) and result['serializer_mismatch_calls'] == 1
    last = result['rows'][-1]
    assert last['response_status'] == ('uncommitted-unknown' if pending else 'committed-receipt')
    assert last['attempted_tool'] == (None if pending else 'finish')
    assert last['observed_successful_document_change'] is (None if pending else False)
    assert not result['full_native_or_transport_audit']


def test_changed_original_intent_chain_stops_visibility_reading(tmp_path):
    journal(tmp_path); path = tmp_path / 'step-01.started.json'
    path.write_text(path.read_text() + '\n')
    with pytest.raises(ValueError): read_visibility(tmp_path)


def all8(tmp_path):
    journal(tmp_path); result = read_visibility(tmp_path)
    rows = []; extra = []
    for i in range(8):
        session = {'completed_steps': result['completed_steps'], 'terminal_status': result['terminal_status'],
            'terminal_record_present': result['terminal_record_present'], 'file_sha256': deepcopy(result['file_sha256'])}
        rows.append({'cell_id': 'SCRIPTED-cell-' + str(i), 'status': 'complete', 'loss': float(i),
            'request_sha256': result['request_sha256'], 'session': session})
        extra.append({'cell_id': rows[-1]['cell_id'], 'visibility': deepcopy(result)})
    report = {'schema': 'scienceutopia.native-priority-author-outcomes.v1',
        'scientific_source_commit': 'SCRIPTED-not-provenance', 'rows': rows}
    return report, extra


def sealed(value):
    value = {k: deepcopy(v) for k,v in value.items() if k != 'content_sha256'}
    return {**value, 'content_sha256': digest(value)}


def test_all8_join_preserves_adverse_losses_and_missing_generation_session_unknown(tmp_path):
    report, extra = all8(tmp_path); report['rows'][0].update(status='generation-null', loss=None, session=None)
    extra[0]['visibility'] = None; result = join_visibility(sealed(report), extra)
    assert len(result['rows']) == 8 and result['recorded_sessions'] == 7
    assert result['rows'][0]['loss'] is result['rows'][0]['visibility'] is None
    assert result['rows'][-1]['loss'] == 7. and not result['scientific_losses_rewritten']


@pytest.mark.parametrize('change', ['missing', 'reorder', 'request', 'count', 'files', 'session', 'fake-null'])
def test_join_requires_all8_original_cell_and_session_bindings(tmp_path, change):
    report, extra = all8(tmp_path)
    if change == 'missing': extra.pop()
    elif change == 'reorder': extra.reverse()
    elif change == 'request': extra[0]['visibility']['request_sha256'] = 'f' * 64
    elif change == 'count': extra[0]['visibility']['completed_steps'] += 1
    elif change == 'files': extra[0]['visibility']['file_sha256'] = {}
    elif change == 'session': extra[0]['visibility'] = None
    else: report['rows'][0]['session'] = extra[0]['visibility'] = None
    with pytest.raises(ValueError): join_visibility(sealed(report), extra)
