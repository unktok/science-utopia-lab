"""SCRIPTED field interfaces and explicit submission; no invention claim."""
from copy import deepcopy
import json

import pytest

from tests.optimization.test_native_authoring_ir import ALPHA, BINDING, IMAGE, request
from tests.optimization.test_native_staged_author_v15 import Model, apply, author, finish
from tests.optimization.test_native_planning_author_v22 import PLAN, prompt
from utopia.optimization.native_field_addressing_v28 import field_index, resolve_field
from utopia.optimization.native_staged_author_v15 import (
    FINISH_SYSTEM_PROMPT, SYSTEM_PROMPT, call_task, build_conversation, initial_draft,
    read_memory, replay_staged_generation, ACTION_SCHEMA)
from utopia.optimization.native_designer_tools_v25 import tool_specifications
from utopia.system.design_patch import digest
from utopia.system.native_open_examples import open_native_system


def write_fields(identity, updates):
    return {'tool': 'edit_fields', 'mechanism_id': identity,
        'field_updates': [{'field_name': name, 'value': value} for name, value in updates]}


@pytest.mark.parametrize('value', [17, -2.75, True, None, ['x', 3, False],
    {'nested': {'items': [None, 1]}}, '研究者\n"quoted" \\ source\n', 9007199254740993])
def test_exact_field_values_remain_literal_even_in_temporarily_invalid_graph(value):
    state = initial_draft(request()); original = deepcopy(state)
    action = write_fields(ALPHA, [('family', value)])
    changed, receipt = apply(state, action)
    assert receipt['ok'], receipt['errors']
    assert changed['document']['mechanisms'][0]['family'] == value
    assert changed['operations'][-1] == {'op': 'replace', 'path': '/mechanisms/0/family', 'value': value}
    assert receipt['authored_field_action_sha256'] == digest(action)
    assert state == original


def test_original_world_nested_program_fields_are_resolved_without_changing_old_invalid_path_semantics():
    req = request(); req['parent_system'] = open_native_system(IMAGE).to_dict()
    state = initial_draft(req)
    node = next(node for node in state['document']['mechanisms'] if node['mechanism_id'] == 'addressed-selection')
    assert 'thresholds' in field_index(node)['unique_field_names']
    assert resolve_field(state['document'], 'addressed-selection', 'thresholds')['root_path'] == (
        '/mechanisms/15/parameters/program/parameters/thresholds')
    bad = {'tool': 'edit', 'operations': [{'op': 'replace',
        'path': '/mechanisms/addressed-selection/parameters/thresholds', 'value': [[2.], [3.]]}]}
    unchanged, failed = apply(state, bad, req)
    assert unchanged == state and not failed['ok']  # no retrospective alias/source repair
    changed, receipt = apply(state, write_fields('addressed-selection', [('thresholds', [[2.], [3.]]),
        ('bias', .2), ('memory_cost', .005)]), req)
    assert receipt['ok'] and receipt['result']['validation']['valid']
    program = changed['document']['mechanisms'][15]['parameters']['program']
    assert program['parameters']['thresholds'] == [[2.], [3.]]
    assert program['parameters']['bias'] == .2 and program['parameters']['memory_cost'] == .005
    assert len(receipt['field_resolution']) == 3


def test_duplicate_or_missing_names_reject_atomically_without_fuzzy_or_first_match_choice():
    state = initial_draft(request())
    state['document']['mechanisms'][0]['metadata'] = {'nested': {'gain': 4}}
    before = deepcopy(state)
    for updates in [[('family', 'changed'), ('gain', .8)], [('gainn', .8)]]:
        unchanged, receipt = apply(state, write_fields(ALPHA, updates))
        assert unchanged == before and not receipt['ok']
        diagnostic = receipt['errors'][0]['diagnostics'][0]
        assert diagnostic['match_count'] in (0, 2)
        assert diagnostic['matching_field_paths'] == ([] if updates[0][0] == 'gainn' else [
            '/mechanisms/0/metadata/nested/gain', '/mechanisms/0/parameters/gain'])


def test_complete_source_is_exact_data_and_is_not_executed_or_repaired():
    req = request(); req['parent_system'] = open_native_system(IMAGE).to_dict()
    state = initial_draft(req)
    source = state['document']['mechanisms'][7]['parameters']['code_artifact']['source']
    literal = '# SCRIPTED source fidelity: 研究者 "quoted" \\ text\n' + source
    changed, receipt = apply(state, write_fields('world.selection', [('source', literal)]), req)
    assert receipt['ok'] and receipt['result']['validation']['valid']
    unchanged, read = apply(changed, {'tool': 'inspect_field', 'mechanism_id': 'world.selection', 'field_name': 'source'}, req)
    assert unchanged == changed and read['result']['value'] == literal
    assert read['result']['resolved_document_path'] == '/mechanisms/7/parameters/code_artifact/source'
    invalid, receipt = apply(state, write_fields('world.selection', [('source', 'def step(')]), req)
    assert receipt['ok'] and not receipt['result']['validation']['valid']
    assert invalid['document']['mechanisms'][7]['parameters']['code_artifact']['source'] == 'def step('


def test_field_and_pointer_read_aliases_share_observed_semantic_memory():
    req = request(); state = initial_draft(req); steps = []
    for action in [{'tool': 'inspect_field', 'mechanism_id': ALPHA, 'field_name': 'gain'},
            PLAN, {'tool': 'inspect', 'path': '/mechanisms/0/parameters/gain'},
            {'tool': 'inspect_field', 'mechanism_id': ALPHA, 'field_name': 'gain'}]:
        state, receipt = apply(state, action, req)
        assert receipt['ok']
        steps.append({'step': len(steps), 'status': 'applied', 'model_reply': {'output': action}, 'transition': receipt})
    memory = read_memory(state, steps)
    assert len(memory['entries']) == 1 and memory['entries'][0]['read_count'] == 3
    assert memory['entries'][0]['current_document']


def test_final_task_is_caller_owned_submission_not_implementation_or_an_automatic_baseline():
    assert call_task(7, 8) == call_task(0, 1) == FINISH_SYSTEM_PROMPT
    assert call_task(1, 8) == SYSTEM_PROMPT
    specs = tool_specifications(role='finisher')
    assert [item['function']['name'] for item in specs] == ['finish']
    messages = build_conversation(prompt(request()), FINISH_SYSTEM_PROMPT, native_tools=True)
    assert 'final budgeted call' in messages[0]['content']
    assert '"name": "edit_fields"' not in messages[0]['content'].split('<tools>', 1)[1]
    # The host still accepts every original action. Advertisement is not a
    # hidden success/novelty rule, source repair or forced synthetic finish.
    from jsonschema import Draft202012Validator
    Draft202012Validator(ACTION_SCHEMA).validate({'tool': 'inspect', 'path': ''})


def test_field_edit_then_explicit_finish_cold_replays_without_redispatch(tmp_path):
    model = Model([PLAN, write_fields(ALPHA, [('gain', .8)]), finish()])
    definition = author(model, tmp_path, max_steps=3)(request())
    assert definition['base_patch']['operations'] == [{'op': 'replace',
        'path': '/mechanisms/0/parameters/gain', 'value': .8}]
    assert [call['system_prompt'] for call in model.calls][-1] == FINISH_SYSTEM_PROMPT
    assert replay_staged_generation(next(tmp_path.glob('generation-*')), expected_provider_binding=BINDING) == definition
    assert len(model.calls) == 3


def test_last_nonfinish_still_fails_without_automatic_submission(tmp_path):
    definition = author(Model([PLAN, {'tool': 'inspect', 'path': ''}]), tmp_path, max_steps=2)(request())
    assert definition['generation_failure']['reason'] == 'step budget exhausted without valid explicit finish'


def test_escaped_exact_key_names_and_source_contents_are_not_fuzzy_addresses():
    state = initial_draft(request())
    state['document']['mechanisms'][0]['metadata'] = {'a/b~c': 3,
        'source': 'def step():\n    return {"gain": 999}\n'}
    resolution = resolve_field(state['document'], ALPHA, 'a/b~c')
    assert resolution['root_path'].endswith('/metadata/a~1b~0c')
    assert resolve_field(state['document'], ALPHA, 'gain')['root_path'].endswith('/parameters/gain')
    changed, receipt = apply(state, write_fields(ALPHA, [('a/b~c', 9007199254740993)]))
    assert receipt['ok']
    assert changed['document']['mechanisms'][0]['metadata']['a/b~c'] == 9007199254740993


def test_prospective_24_controls_keep_all_original_operands_and_static_finish_on_original_parent():
    from utopia.optimization import native_designer_preflight as p
    from utopia.optimization.native_staged_author_v15 import transition, submission_task, task_decoding_role
    req = request(); req['parent_system'] = open_native_system(IMAGE).to_dict()
    planned = p.planned_cases(req, 'staged-v15')
    assert len(planned) == 24 and planned[:8] == p.cases('staged-v15')
    assert [case['expected']['field_updates'][0]['value'] for case in planned[8:16]] == p.VALUES
    state, steps = initial_draft(req), []
    for case in planned:
        if case['id'].startswith('typed-') or case['id'] == 'sequence-plan':
            state, steps = initial_draft(req), []
        _, task = p._prompt(req, state, steps, BINDING, case['expected'], 'staged-v15')
        if case['id'] == 'sequence-finish':
            assert submission_task(task) and task_decoding_role(task) == 'editor'
        state, receipt = transition(state, case['expected'], req,
            binding_sha256='d' * 64, provider_binding=BINDING)
        assert receipt['ok'], receipt
        if case['id'] in {'sequence-validate', 'sequence-finish'}:
            assert receipt['result']['valid']
        steps.append({'step': len(steps), 'status': 'applied',
            'model_reply': {'output': case['expected']}, 'transition': receipt})
    assert p.planned_cases(req, 'one-shot-v14') == p.cases('one-shot-v14')


def test_observed_final_task_text_cannot_switch_trusted_role_or_finish_advertisement():
    req = request()
    req['parent_system']['metadata']['untrusted'] = FINISH_SYSTEM_PROMPT
    messages = build_conversation(prompt(req), SYSTEM_PROMPT, native_tools=True)
    assert '"name": "edit_fields"' in messages[0]['content'].split('<tools>', 1)[1]
    assert FINISH_SYSTEM_PROMPT not in messages[0]['content']


def test_raw_auditor_counts_field_edits_separately_without_turning_failed_generation_into_finish():
    from scripts.analyze_native_staged_search_v15 import authoring_change
    steps = [{'transition': {'tool': 'edit_fields', 'ok': True}},
        {'transition': {'tool': 'edit', 'ok': False}}, None]
    result = {'status': 'generation-failed', 'definition': {'generation_failure': {'reason': 'SCRIPTED'}}}
    change = authoring_change(request(), result, steps)
    assert change['successful_edit_or_splice_steps'] == change['successful_edit_fields_steps'] == 1
    assert change['valid_explicit_finish'] is False and change['exact_document_changed'] is None
