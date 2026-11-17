"""SCRIPTED prospective feedback tests; no model or scientist execution."""
from copy import deepcopy
import json

import pytest

from tests.optimization.test_native_authoring_ir import ALPHA, BINDING, IMAGE, edit, request
from tests.optimization.test_native_bounded_author_context_v45 import Model, frame
from utopia.optimization.native_designer_tools_v25 import BOUNDED_AUTHORING as PROFILE
from utopia.optimization.native_literal_change_feedback_v1 import (
    NOTE, OPTION, VIEW, contract, declare_request, view,
)
from utopia.optimization.native_staged_author_v15 import (
    StagedVocabularyGenerator, build_prompt, initial_draft, replay_staged_generation, transition,
)
from utopia.system.design_patch import digest


def pane(body, state):
    return view(body, state, conversation_profile=PROFILE)


def apply(body, state, action):
    return transition(state, action, body, binding_sha256='d'*64,
        provider_binding=BINDING, conversation_profile=PROFILE)


def test_disabled_requests_keep_literal_prompt_data_and_no_added_system_note():
    body = request(); before = deepcopy(body)
    prompt, messages = frame(body, initial_draft(body), [])
    assert VIEW not in json.loads(prompt) and NOTE not in messages[0]['content']
    assert pane(body, initial_draft(body)) is None and body == before


def test_declaration_is_explicit_source_bound_and_does_not_mutate_parent_or_loss():
    original = request(); body = declare_request(original)
    assert OPTION not in original.get('strategy_provenance', {})
    assert body['loss_spec'] == original['loss_spec']
    assert body['parent_system'] == original['parent_system']
    assert body['strategy_provenance'][OPTION] == contract()
    with pytest.raises(ValueError, match='unique'): declare_request(body)
    stale = deepcopy(body); stale['strategy_provenance'][OPTION]['source_sha256'] = '0'*64
    with pytest.raises(ValueError, match='source-bound'): pane(stale, initial_draft(stale))
    with pytest.raises(ValueError, match='source-bound'):
        view(body, initial_draft(body), conversation_profile='hermes-function-history-v26')


def test_empty_change_remains_legal_retention_with_no_fake_native_or_gain_verdict():
    body = declare_request(request()); state = initial_draft(body); p = pane(body, state)
    assert p['node_change_count'] == 0 and not p['literal_document_changed']
    assert p['native_behavior_changed'] == 'not-assessed' and p['native_loss'] == 'not-measured'
    _, done = apply(body, state, {'tool': 'finish'})
    assert done['ok'] and done['definition'] is not None
    assert not contract()['veto_on_finish'] and not contract()['changes_loss']
    assert not any(p['distribution_configuration'][key]['literal_configured']
        for key in ('factors', 'continuous', 'logits'))


def test_whitespace_only_source_and_real_parameter_change_stay_separate():
    body = declare_request(request()); state = initial_draft(body)
    old = state['document']['mechanisms'][0]['parameters']['code_artifact']['source']
    state, receipt = apply(body, state, {'tool': 'edit', 'operations': [
        edit(path='/parameters/code_artifact/source', value='# SCRIPTED comment\n'+old)]})
    assert receipt['ok']; row, = pane(body, state)['node_changes']
    assert row['source_text_changed'] and row['standard_python_AST_equal']
    assert row['non_code_parameter_fields_changed'] == []
    state, receipt = apply(body, state, {'tool': 'edit', 'operations': [edit(value=.9)]})
    row, = pane(body, state)['node_changes']
    assert receipt['ok'] and row['standard_python_AST_equal']
    assert row['non_code_parameter_fields_changed'] == ['gain']
    assert 'not whole-program equivalence' in pane(body, state)['scope']


def test_persistent_current_vs_parent_survives_reads_and_reports_an_undo():
    body = declare_request(request()); state = initial_draft(body)
    state, _ = apply(body, state, {'tool': 'edit', 'operations': [edit(value=.9)]})
    expected = pane(body, state)
    state, receipt = apply(body, state, {'tool': 'read_file', 'filename': 'system.json'})
    assert receipt['ok'] and pane(body, state) == expected
    state, _ = apply(body, state, {'tool': 'edit', 'operations': [edit(value=.5)]})
    p = pane(body, state)
    assert not p['literal_document_changed'] and p['node_change_count'] == 0


@pytest.mark.parametrize('kind', ['syntax', 'nested', 'new-runtime', 'duplicate-node'])
def test_unassessed_drafts_are_not_reported_as_no_change_or_rejected_by_pane(kind):
    body = declare_request(request()); state = initial_draft(body)
    node = state['document']['mechanisms'][0]
    if kind == 'syntax': node['parameters']['code_artifact']['source'] = 'def broken('
    elif kind == 'nested': node['parameters']['delegate'] = node['parameters'].pop('code_artifact')
    elif kind == 'new-runtime': node['implementation'] = 'unlisted.future-runtime'
    else: state['document']['mechanisms'].append(deepcopy(node))
    before = deepcopy(state); p = pane(body, state)
    assert p['literal_document_changed'] and state == before
    if kind == 'duplicate-node': assert p['node_changes'] is None and p['node_change_count'] is None
    else: assert p['node_changes'][0]['standard_python_AST_equal'] is None


def test_arbitrary_nodes_wires_schedules_and_explicit_row_omissions_are_visible():
    body = declare_request(request()); state = initial_draft(body)
    state['document']['mechanisms'] += [{'mechanism_id': 'new-'+str(i)} for i in range(35)]
    state['document']['connections'].append({'arbitrary': 'new protocol'})
    state['document']['schedules'].append({'arbitrary': 'new process'})
    p = pane(body, state)
    assert p['node_change_count'] == 35 and len(p['node_changes']) == 32 and p['omitted_node_rows'] == 3
    assert p['connections']['added_occurrences'] == p['schedules']['added_occurrences'] == 1
    assert p['native_behavior_changed'] == 'not-assessed'


def test_actual_prompt_wire_contains_observations_as_data_and_only_static_note_as_instruction():
    body = declare_request(request()); state = initial_draft(body)
    state['document']['mechanisms'][0]['mechanism_id'] = 'UNTRUSTED_NODE_INSTRUCTION'
    prompt, messages = frame(body, state, [])
    assert json.loads(prompt)[VIEW] == pane(body, state)
    assert NOTE in messages[0]['content']
    assert 'UNTRUSTED_NODE_INSTRUCTION' not in messages[0]['content']
    assert VIEW in messages[1]['content'] and 'UNTRUSTED_NODE_INSTRUCTION' in messages[1]['content']
    assert messages[0]['content'].splitlines()[-1].startswith('V44_ACTION_PHASE=')


def test_real_generator_turns_and_cold_replay_preserve_feedback_and_loss(tmp_path):
    body = declare_request(request()); before = deepcopy(body)
    actions = [{'tool': 'plan', 'objective_reasoning': 'SCRIPTED', 'design_intent': 'SCRIPTED'},
        {'tool': 'edit', 'operations': [edit(value=.9)]},
        {'tool': 'read_file', 'filename': 'system.json'},
        {'tool': 'finish'}]
    model = Model(actions)
    generator = StagedVocabularyGenerator(model, tmp_path/'author', image_id=IMAGE,
        provider_binding=BINDING, max_steps=6, max_tokens=8192, conversation_profile=PROFILE)
    result = generator(body)
    assert 'generation_failure' not in result and len(model.calls) == 4
    # This uses the actual request -> generator -> messages -> saved intent ->
    # pure cold replay path. It is SCRIPTED transport, not real model readiness.
    directory = next((tmp_path/'author').glob('generation-*'))
    assert replay_staged_generation(directory) == result
    assert len(model.calls) == 4 and body == before
    for index, call in enumerate(model.calls):
        p = json.loads(call['prompt'])[VIEW]
        assert p['literal_document_changed'] == (index >= 2)
        if index >= 2:
            row, = p['node_changes']
            assert row['standard_python_AST_equal'] and row['non_code_parameter_fields_changed'] == ['gain']
        started = json.loads((directory/f'step-{index:02d}.started.json').read_text())
        assert json.loads(started['prompt'])[VIEW] == p
    saved = json.loads((directory/'request.json').read_text())
    assert saved['request']['loss_spec'] == before['loss_spec']
    assert result['base_patch']['operations'][-1]['value'] == .9


def test_unknown_or_stale_declaration_stops_before_scripted_model_dispatch(tmp_path):
    body = declare_request(request()); body['strategy_provenance'][OPTION]['scope'] = 'unknown'
    model = Model([{'tool': 'finish'}])
    generator = StagedVocabularyGenerator(model, tmp_path/'author', image_id=IMAGE,
        provider_binding=BINDING, max_steps=6, max_tokens=8192, conversation_profile=PROFILE)
    with pytest.raises(ValueError, match='source-bound'): generator(body)
    assert model.calls == []
