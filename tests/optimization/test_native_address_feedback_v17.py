"""SCRIPTED address ergonomics, not autonomous-planning evidence."""
from tests.optimization.test_native_authoring_ir import BINDING, request
from utopia.optimization.native_staged_author_v15 import initial_draft, transition, read_memory


def apply(state, action):
    return transition(state, action, request(), binding_sha256='d' * 64, provider_binding=BINDING)


def test_inspection_exposes_reusable_literal_address_separate_from_absolute_result_path():
    state = initial_draft(request())
    node = state['document']['mechanisms'][0]['mechanism_id']
    target = {'selector': {'mechanism_id': node}, 'path': '/parameters/code_artifact/source'}
    state, receipt = apply(state, {'tool': 'inspect', **target})
    result = receipt['result']
    assert receipt['ok'] and result['reusable_address'] == target
    assert result['address_scope'] == 'mechanism-relative'
    assert result['resolved_document_path'] == result['path'] == '/mechanisms/0/parameters/code_artifact/source'
    same, edited = apply(state, {'tool': 'edit', 'operations': [
        {'op': 'replace', **result['reusable_address'], 'value': result['value']}]})
    assert edited['ok'] and same['document'] == state['document']
    global_state, global_read = apply(state, {'tool': 'inspect', 'path': result['resolved_document_path']})
    assert global_read['ok'] and global_read['result']['value'] == result['value']
    assert global_read['result']['address_scope'] == 'document-root'
    memory = read_memory(global_state, [{'step': 0, 'transition': receipt}, {'step': 1, 'transition': global_read}])
    assert len(memory['entries']) == 1 and memory['entries'][0]['read_count'] == 2
    assert memory['entries'][0]['reusable_address'] == target


def test_double_node_prefix_is_diagnosed_not_stripped_or_applied():
    state = initial_draft(request())
    node = state['document']['mechanisms'][0]['mechanism_id']
    malformed = {'selector': {'mechanism_id': node}, 'path': '/mechanisms/0/parameters/code_artifact/source'}
    after, receipt = apply(state, {'tool': 'edit', 'operations': [
        {'op': 'replace', **malformed, 'value': 'def step(context):\n    return {}\n'}]})
    assert not receipt['ok'] and after == state
    detail = receipt['errors'][0]['addressing']
    assert detail['authored_address'] == malformed
    assert detail['path_scope'] == 'mechanism-relative'
    assert not detail['authored_target_changed_by_host']
    assert 'omit selector' in detail['notice']
    assert receipt['errors'][0]['diagnostics'][0]['path'].startswith('/mechanisms/0/mechanisms/0/')


def test_capability_reusable_address_preserves_read_only_resource_instead_of_redirecting_to_draft():
    state = initial_draft(request())
    action = {'tool': 'inspect', 'resource': 'capabilities', 'path': '/index'}
    state, receipt = apply(state, action)
    assert receipt['ok'] and not receipt['result']['candidate_edit_target']
    assert receipt['result']['reusable_address'] == {'resource': 'capabilities', 'path': '/index'}
    _, reread = apply(state, {'tool': 'inspect', **receipt['result']['reusable_address']})
    assert reread['ok'] and reread['result']['value'] == receipt['result']['value']


def test_omitted_large_values_still_expose_exact_address(monkeypatch):
    from utopia.optimization import native_staged_author_v15 as module
    monkeypatch.setattr(module, 'MAX_RESULT_BYTES', 1)
    state = initial_draft(request())
    node = state['document']['mechanisms'][0]['mechanism_id']
    action = {'tool': 'inspect', 'selector': {'mechanism_id': node}, 'path': ''}
    _, receipt = apply(state, action)
    assert receipt['ok'] and not receipt['result']['value_included']
    assert receipt['result']['reusable_address'] == {'selector': {'mechanism_id': node}, 'path': ''}


def test_non_json_address_cannot_escape_error_handling():
    state = initial_draft(request())
    after, receipt = apply(state, {'tool': 'inspect', 'path': float('nan')})
    assert not receipt['ok'] and after == state
    assert 'addressing' not in receipt['errors'][0]


def test_actual_preflight_sequence_covers_relative_and_absolute_address_forms():
    from utopia.optimization.native_designer_preflight import sequence
    from utopia.optimization.native_staged_author_v15 import PLAN_CONTROL
    state = initial_draft(request())
    sequence_cases = sequence(state)
    assert [row['id'] for row in sequence_cases] == ['sequence-plan', 'sequence-inspect',
        'sequence-splice', 'sequence-reinspect', 'sequence-inspect-field',
        'sequence-edit-fields-source', 'sequence-validate', 'sequence-finish']
    cases = {row['id']: row['expected'] for row in sequence_cases}
    assert cases['sequence-plan'] == PLAN_CONTROL
    relative, splice, absolute = [cases[key] for key in (
        'sequence-inspect', 'sequence-splice', 'sequence-reinspect')]
    assert relative['selector']['mechanism_id'] == state['document']['mechanisms'][0]['mechanism_id']
    assert relative['path'] == '/parameters/code_artifact/source'
    assert splice['path'] == relative['path'] and splice['selector'] == relative['selector']
    assert absolute['path'] == '/mechanisms/0/parameters/code_artifact/source'
    assert 'selector' not in absolute
