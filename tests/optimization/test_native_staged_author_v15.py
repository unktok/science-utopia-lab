"""SCRIPTED tool/replay/trace tests only; no Qwen or generated research claims."""
import json

import pytest

from tests.optimization.test_native_authoring_ir import (
    ALPHA, BINDING, IMAGE, code_node, coordinate, edit, request,
)
from tests.optimization.test_native_search_generator_v14 import Model
from utopia.optimization.native_adaptive_search import GeneratedMixedDesign
from utopia.optimization.native_staged_author_v15 import (
    StagedVocabularyGenerator, build_prompt, draft_summary, initial_draft,
    project_authoring_trace, protocol_binding, transition,
    replay_staged_generation,
)
from utopia.system.design_patch import clone, digest

HASH = 'd' * 64


def apply(state, action, body=None):
    return transition(state, action, body or request(), binding_sha256=HASH, provider_binding=BINDING)


def author(model, path, **kwargs):
    return StagedVocabularyGenerator(model, path, image_id=IMAGE, provider_binding=BINDING, **kwargs)


def finish():
    return {'tool': 'finish', 'rationale': 'SCRIPTED technical fixture, not a discovered institution'}


def result_path(path):
    return next(path.glob('generation-*/response.json'))


def load(path):
    return json.loads(path.read_text())


def rehash(path, edit_document):
    value = load(path)
    edit_document(value)
    value['content_sha256'] = digest({k: v for k, v in value.items() if k != 'content_sha256'})
    path.write_text(json.dumps(value))


def test_inspect_exact_selected_node_and_pointer_slice_without_parent_mutation():
    body = request(); state = initial_draft(body)
    same, outcome = apply(state, {'tool': 'inspect', 'selector': {'mechanism_id': ALPHA}, 'path': ''})
    assert outcome['ok'] and outcome['result']['value'] == body['parent_system']['mechanisms'][0]
    assert outcome['result']['path'] == '/mechanisms/0'
    assert same == state and body == request()
    same, outcome = apply(state, {'tool': 'inspect', 'selector': {'mechanism_id': ALPHA},
        'path': '/parameters/code_artifact/source', 'offset': 0, 'limit': 5})
    assert outcome['result']['value'] == 'raise'
    assert outcome['result']['selection']['slice_complete'] is False
    assert same == state


def test_invalid_path_transaction_is_rejected_atomically_with_exact_diagnostics():
    state = initial_draft(request())
    same, outcome = apply(state, {'tool': 'edit', 'operations': [edit(value=.9), edit(path='/absent/x')]})
    assert not outcome['ok'] and same == state
    assert outcome['draft_before_sha256'] == outcome['draft_after_sha256']
    diagnostic = outcome['errors'][0]['diagnostics'][0]
    assert diagnostic['first_missing_segment'] == 'absent' and diagnostic['operation_index'] == 1
    assert diagnostic['actual_owner_id'] == ALPHA


def test_intermediate_invalid_graph_can_be_built_then_repaired_and_finished():
    state = initial_draft(request())
    source = code_node('new-node-not-in-any-catalogue')
    source['outputs'] = [{'port_id': 'out', 'channel': 'artifact', 'artifact_type': 'brand-new', 'required': True}]
    source['parameters']['code_artifact']['outputs'] = {'out': {'type': 'object'}}
    # Missing artifact declaration: the literal JSON edit is valid, graph isn't.
    state, outcome = apply(state, {'tool': 'edit', 'operations': [
        {'op': 'add', 'path': '/mechanisms/-', 'value': source}]})
    assert outcome['ok'] and not outcome['result']['validation']['valid']
    assert state['document']['mechanisms'][-1] == source
    same, failed_finish = apply(state, finish())
    assert not failed_finish['ok'] and failed_finish['definition'] is None and same == state
    state, outcome = apply(state, {'tool': 'edit', 'operations': [
        {'op': 'add', 'path': '/artifact_types/-', 'value': {'artifact_type_id': 'brand-new', 'description': ''}},
        {'op': 'add', 'path': '/schedules/-', 'value': {'mechanism_id': source['mechanism_id'], 'phase': 50, 'trigger': 'annual'}}]})
    assert outcome['ok'] and outcome['result']['validation']['valid']
    _, finished = apply(state, finish())
    assert finished['ok'] and finished['definition']['provenance']['kind'] == 'automatic-local-LLM-staged-v15'
    assert finished['definition']['base_patch']['operations'][0]['value'] == source


def test_arbitrary_node_wire_protocol_and_process_edits_remain_literal_and_executable_boundary():
    state = initial_draft(request())
    first, second = code_node('unlisted-source'), code_node('unlisted-sink')
    first['outputs'] = [{'port_id': 'out', 'channel': 'artifact', 'artifact_type': 'custom-format', 'required': True}]
    second['inputs'] = [{'port_id': 'in', 'channel': 'artifact', 'artifact_type': 'custom-format', 'required': True}]
    first['parameters']['code_artifact']['outputs'] = {'out': {'type': 'object'}}
    second['parameters']['code_artifact']['inputs'] = {'in': {'type': 'object'}}
    operations = [
        {'op': 'add', 'path': '/artifact_types/-', 'value': {'artifact_type_id': 'custom-format', 'description': 'SCRIPTED'}},
        {'op': 'add', 'path': '/mechanisms/-', 'value': first},
        {'op': 'add', 'path': '/mechanisms/-', 'value': second},
        {'op': 'add', 'path': '/connections/-', 'value': {'source_mechanism': 'unlisted-source', 'source_port': 'out',
            'target_mechanism': 'unlisted-sink', 'target_port': 'in', 'channel': 'artifact', 'latency': 0}},
        {'op': 'add', 'path': '/schedules/-', 'value': {'mechanism_id': 'unlisted-source', 'phase': 10, 'trigger': 'annual'}},
        {'op': 'add', 'path': '/schedules/-', 'value': {'mechanism_id': 'unlisted-sink', 'phase': 20, 'trigger': 'annual'}},
        {'op': 'add', 'path': '/metadata/native_processes', 'value': {'custom-description': 'literal authored metadata'}},
    ]
    state, changed = apply(state, {'tool': 'edit', 'operations': operations})
    assert changed['ok'] and changed['result']['validation']['valid']
    _, done = apply(state, finish())
    assert done['definition']['base_patch']['operations'] == operations
    assert done['definition']['provenance']['staged_author']['source_execution_on_host'] is False
    assert done['definition']['provenance']['staged_author']['native_probes'] == 0


def test_incremental_source_splice_uses_unicode_offsets_and_never_executes_or_repairs():
    state = initial_draft(request())
    address = {'selector': {'mechanism_id': ALPHA}, 'path': '/parameters/code_artifact/source'}
    state, first = apply(state, {'tool': 'edit', 'operations': [edit(path=address['path'], value='def step(')]})
    assert first['ok'] and not first['result']['validation']['valid']
    state, second = apply(state, {'tool': 'splice', **address, 'offset': 9, 'delete': 0,
        'text': 'context):\n    # 日本語\n    raise RuntimeError("NEVER_ON_HOST")\n'})
    assert second['ok'] and second['result']['validation']['valid']
    expected = 'def step(context):\n    # 日本語\n    raise RuntimeError("NEVER_ON_HOST")\n'
    assert state['document']['mechanisms'][0]['parameters']['code_artifact']['source'] == expected
    _, outcome = apply(state, finish())
    assert outcome['definition']['base_patch']['operations'][-1]['value'] == expected


def test_arbitrary_factor_and_numeric_coordinate_configuration_is_supported():
    body = request(); body['count'] = 2
    state = initial_draft(body)
    factors = [{'id': 'unlisted-factor', 'kind': 'bernoulli', 'choices': [
        {'id': 'x', 'operations': [], 'provenance': {'author': 'SCRIPTED'}},
        {'id': 'y', 'operations': [edit(value=1.5)], 'provenance': {'author': 'SCRIPTED'}}]}]
    state, configured = apply(state, {'tool': 'configure', 'factors': factors,
        'continuous': [coordinate()], 'logits': {'unlisted-factor': [.3]}}, body)
    assert configured['ok'] and configured['result']['validation']['valid']
    _, completed = apply(state, finish(), body)
    definition = completed['definition']
    mixed = GeneratedMixedDesign(__import__('utopia.system', fromlist=['SystemSpec']).SystemSpec.from_dict(body['parent_system']),
        definition, loss_spec=body['loss_spec'], seed=42)
    draws = mixed.draw(2, version_sha256=digest(definition))
    assert len(draws) == 2 and definition['continuous'][0]['path'] == '/mechanisms/0/parameters/gain'


@pytest.mark.parametrize('action', [
    {'tool': 'edit', 'operations': []}, {'tool': 'finish'}, {'tool': 'configure'},
    {'tool': 'validate', 'path': ''}, {'tool': 'inspect', 'path': '/metadata', 'offset': 0},
    {'tool': 'inspect', 'selector': {'mechanism_id': 'fuzzy-alias'}, 'path': ''},
    {'tool': 'splice', 'path': '/system_id', 'offset': 1000, 'delete': 0, 'text': ''},
    {'tool': 'splice', 'path': '/initial_state', 'offset': 0, 'delete': 0, 'text': ''},
    {'tool': 'shell', 'command': 'not allowed'}, {'tool': 'inspect', 'path': '/metadata', 'host_file': '/etc/passwd'},
])
def test_bad_tools_never_mutate_draft(action):
    state = initial_draft(request())
    same, result = apply(state, action)
    assert same == state and not result['ok'] and result['definition'] is None


def test_pinned_image_violation_can_be_authored_but_never_finished():
    state = initial_draft(request())
    state, changed = apply(state, {'tool': 'edit', 'operations': [edit(path='/parameters/runtime_image_id',
        value='sha256:' + 'f' * 64)]})
    assert changed['ok'] and not changed['result']['validation']['valid']
    _, outcome = apply(state, finish())
    assert not outcome['ok'] and outcome['definition'] is None


def test_bounded_steps_finish_and_cold_replay_use_no_more_provider_calls(tmp_path):
    model = Model([{'tool': 'inspect', 'selector': {'mechanism_id': ALPHA}, 'path': ''},
        {'tool': 'edit', 'operations': [edit(value=1.2)]}, {'tool': 'validate'}, finish()])
    definition = author(model, tmp_path, max_steps=4)(request())
    assert definition['base_patch']['operations'][0]['value'] == 1.2
    assert len(model.calls) == 4
    assert author(Model([]), tmp_path, max_steps=4)(request()) == definition
    result = load(result_path(tmp_path))
    assert result['status'] == 'generated' and result['selected_step'] == 3
    assert [step['status'] for step in result['steps']] == ['applied', 'applied', 'applied', 'finished']


def test_explicit_retention_is_legal_but_not_automatic_failure_fallback(tmp_path):
    definition = author(Model([finish()]), tmp_path, max_steps=1)(request())
    assert definition['base_patch'] is None
    failed_path = tmp_path / 'failed'
    failed = author(Model([{'tool': 'validate'}]), failed_path, max_steps=1)(request())
    assert set(failed) == {'generation_failure'}
    assert 'without valid explicit finish' in failed['generation_failure']['reason']


def test_invalid_finish_returns_exact_errors_and_model_repairs_its_own_source(tmp_path):
    bad = {'tool': 'edit', 'operations': [edit(path='/parameters/code_artifact/source', value='not python : :')]}
    good = {'tool': 'edit', 'operations': [edit(path='/parameters/code_artifact/source', value='def step(context):\n    return {"outputs": {}, "state": {}}\n')]}
    model = Model([bad, finish(), good, finish()])
    definition = author(model, tmp_path, max_steps=4)(request())
    assert definition['base_patch']['operations'][0]['value'] == 'not python : :'
    assert definition['base_patch']['operations'][1]['value'] == good['operations'][0]['value']
    third_prompt = json.loads(model.calls[2]['prompt'])
    assert third_prompt['last_tool_response']['errors']
    assert third_prompt['remaining_calls_including_this_one'] == 2


def test_interrupted_intent_consumes_step_without_redispatch_or_invented_cost(tmp_path):
    with pytest.raises(KeyboardInterrupt):
        author(Model([KeyboardInterrupt()]), tmp_path, max_steps=2)(request())
    pending = project_authoring_trace(tmp_path, allowed_requests=[request()], provider_binding=BINDING)
    step = pending['generations'][0]['steps'][0]
    assert step['tool'] is None and step['model_call_seconds'] is None and not step['completed']
    model = Model([finish()])
    definition = author(model, tmp_path, max_steps=2)(request())
    assert len(model.calls) == 1 and definition['base_patch'] is None
    result = load(result_path(tmp_path))
    assert result['steps'][0]['status'] == 'interrupted-response-unknown'
    assert result['steps'][0]['completed_sha256'] is None
    assert author(Model([]), tmp_path, max_steps=2)(request()) == definition


def test_raw_reply_mismatch_and_transport_error_are_charged_and_replayed(tmp_path):
    model = Model([(finish(), '{}'), ValueError('SCRIPTED transport unavailable'), finish()])
    definition = author(model, tmp_path, max_steps=3)(request())
    result = load(result_path(tmp_path))
    assert [v['status'] for v in result['steps']] == ['invalid-response', 'transport-error', 'finished']
    assert author(Model([]), tmp_path, max_steps=3)(request()) == definition


def test_numeric_lexical_types_in_raw_actions_are_not_silently_normalized(tmp_path):
    action = {'tool': 'edit', 'operations': [edit(value=1.)]}
    raw = json.dumps({'tool': 'edit', 'operations': [edit(value=1)]})
    model = Model([(action, raw), finish()])
    result = author(model, tmp_path, max_steps=2)(request())
    assert result['base_patch'] is None
    assert load(result_path(tmp_path))['steps'][0]['status'] == 'invalid-response'
    assert author(Model([]), tmp_path, max_steps=2)(request()) == result


def test_failed_generation_feedback_contains_all_step_errors_and_no_candidate(tmp_path):
    model = Model([{'tool': 'inspect', 'path': '/absent'}, {'tool': 'finish'}])
    result = author(model, tmp_path, max_steps=2)(request())
    assert set(result) == {'generation_failure'}
    assert len(result['generation_failure']['technical_errors']) == 2
    assert len(result['generation_failure']['step_receipts']) == 2
    assert author(Model([]), tmp_path, max_steps=2)(request()) == result


def test_prompt_uses_all_own_scalar_history_and_only_requested_literal_body(tmp_path):
    body = request()
    secret = 'SENTINEL_PARENT_LITERAL_BODY_NOT_INITIAL_PROMPT'
    body['parent_system']['metadata']['large'] = secret
    body['observations'] = [{'observation': {'observation_id': 'own', 'status': 'complete', 'loss': -3.,
        'metadata': {'measurements': {'native.accepted_count': 3}, 'technical_failures': []}},
        'suggestion': {'candidate': body['parent_system']}}]
    model = Model([{'tool': 'inspect', 'path': '/metadata/large'}, finish()])
    author(model, tmp_path, max_steps=2)(body)
    assert secret not in model.calls[0]['prompt']
    assert secret in model.calls[1]['prompt']
    prompt = json.loads(model.calls[0]['prompt'])
    assert prompt['own_history']['all_observations'][0]['loss'] == -3.
    assert prompt['draft_index']['complete_current_node_index']
    assert prompt['prompt_view']['silent_size_truncation'] is False
    assert 'Return JSON {operations' not in prompt['technical_ABI_and_distribution_contract']


def test_actual_open_native_parent_initial_context_is_small_without_dropping_loss_feedback():
    from utopia.system.native_open_examples import open_native_system
    body = request(); body['parent_system'] = open_native_system(IMAGE).to_dict()
    state = initial_draft(body)
    prompt = build_prompt(body, state, [], image_id=IMAGE, binding_sha256=HASH,
        settings={'max_steps': 16})
    assert len(prompt.encode()) < 40_000
    assert len(draft_summary(state)['mechanisms']) == len(body['parent_system']['mechanisms'])


@pytest.mark.parametrize('field', ['definition', 'status', 'draft_sha256', 'selected_step', 'steps'])
def test_rehashed_terminal_tamper_is_rejected_by_exact_replay(tmp_path, field):
    author(Model([finish()]), tmp_path, max_steps=1)(request())
    def tamper(value):
        if field == 'definition':
            value[field]['provenance']['kind'] = 'invented'
        elif field == 'steps':
            value[field][0]['completed_sha256'] = 'f' * 64
        else:
            value[field] = 'tampered'
    rehash(result_path(tmp_path), tamper)
    with pytest.raises(ValueError, match='exact replay'):
        author(Model([]), tmp_path, max_steps=1)(request())


@pytest.mark.parametrize('field', ['model_reply', 'transition', 'status'])
def test_rehashed_completed_step_tamper_is_rejected(tmp_path, field):
    author(Model([finish()]), tmp_path, max_steps=1)(request())
    path = next(tmp_path.glob('generation-*/step-00.completed.json'))
    def tamper(value):
        if field == 'model_reply':
            value[field]['output']['rationale'] = 'different rationale'
        elif field == 'transition':
            value[field]['definition']['provenance']['kind'] = 'tampered'
        else:
            value[field] = 'transport-error'
    rehash(path, tamper)
    with pytest.raises(ValueError):
        author(Model([]), tmp_path, max_steps=1)(request())


def test_changed_budgets_provider_and_source_are_not_reused(tmp_path, monkeypatch):
    author(Model([finish()]), tmp_path, max_steps=1)(request())
    with pytest.raises(ValueError, match='exact staged generation'):
        author(Model([]), tmp_path, max_steps=2)(request())
    generator = author(Model([]), tmp_path, max_steps=1)
    generator.provider_binding['model_digest'] = 'different'
    with pytest.raises(ValueError, match='exact staged generation'):
        generator(request())
    monkeypatch.setitem(generator.protocol, 'source_sha256', 'changed')
    with pytest.raises(ValueError, match='source/schema changed'):
        generator(request())


def test_projection_uses_explicit_binding_and_never_claims_independent_audit(tmp_path):
    author(Model([{'tool': 'edit', 'operations': [edit()]}, finish()]), tmp_path, max_steps=2)(request())
    projected = project_authoring_trace(tmp_path, allowed_requests=[request()], provider_binding=BINDING,
        settings={'max_steps': 2, 'max_tokens': 2048}, authoring_protocol=protocol_binding())
    assert projected['scope'] == 'observed-local-journals-not-independent-audit'
    assert projected['warnings'] == [] and projected['generations'][0]['status'] == 'generated'
    steps = projected['generations'][0]['steps']
    assert steps[0]['authored_output']['operations'] == [edit()]
    assert steps[0]['result']['applied_operations'][0]['value'] == 1.25
    assert steps[1]['tool'] == 'finish' and steps[1]['model_call_seconds'] >= 0
    foreign = project_authoring_trace(tmp_path, allowed_requests=[request()], provider_binding={'wrong': True})
    assert foreign['generations'] == [] and 'provider binding differs' in foreign['warnings'][0]
    assert project_authoring_trace(tmp_path, allowed_requests=[])['generations'] == []


def test_read_only_terminal_replay_preserves_all_journal_bytes_and_rejects_nonterminal(tmp_path):
    definition = author(Model([finish()]), tmp_path, max_steps=1)(request())
    path = result_path(tmp_path).parent
    before = {file.name: file.read_bytes() for file in path.iterdir()}
    assert replay_staged_generation(path, expected_request=request(), expected_provider_binding=BINDING) == definition
    assert {file.name: file.read_bytes() for file in path.iterdir()} == before
    with pytest.raises(ValueError, match='provider differs'):
        replay_staged_generation(path, expected_provider_binding={'different': True})
    (path / 'response.json').unlink()
    with pytest.raises(ValueError, match='requires an existing terminal'):
        replay_staged_generation(path)
    # Worker recovery, unlike auditing, can seal a completed finish without a
    # second model call after a crash before response.json was persisted.
    assert author(Model([]), tmp_path, max_steps=1)(request()) == definition


def test_all_prior_invalid_draft_diagnostics_survive_intervening_tool_calls(tmp_path):
    model = Model([{'tool': 'edit', 'operations': [edit(path='/parameters/code_artifact/source', value='bad : :')]},
        {'tool': 'inspect', 'path': '/metadata'}, finish()])
    author(model, tmp_path, max_steps=3)(request())
    third_prompt = json.loads(model.calls[2]['prompt'])
    assert third_prompt['previous_steps'][0]['errors']
    assert third_prompt['previous_steps'][1]['errors'] == []
    projected = project_authoring_trace(tmp_path, allowed_requests=[request()])
    assert projected['generations'][0]['steps'][0]['errors']


def test_model_never_called_when_full_prompt_exceeds_explicit_byte_budget(tmp_path):
    body = request()
    body['history'] = [{'report': {'explicit-large-prior-report': 'x' * 250_000}}]
    model = Model([])
    failure = author(model, tmp_path, max_steps=3)(body)
    assert model.calls == []
    assert 'prompt byte budget exceeded' in failure['generation_failure']['reason']
    assert load(result_path(tmp_path))['steps'] == []
    assert author(Model([]), tmp_path, max_steps=3)(body) == failure


def test_unexpected_future_dispatch_and_orphan_completion_fail_before_provider_call(tmp_path):
    author(Model([finish()]), tmp_path, max_steps=2)(request())
    directory = result_path(tmp_path).parent
    (directory / 'step-01.completed.json').write_text('{}')
    with pytest.raises(ValueError, match='orphan'):
        author(Model([]), tmp_path, max_steps=2)(request())


def test_projector_fails_foreign_settings_protocol_and_corrupt_receipts_closed(tmp_path):
    author(Model([finish()]), tmp_path, max_steps=1)(request())
    for options in ({'settings': {'max_steps': 8}}, {'authoring_protocol': {'schema': 'other'}}):
        trace = project_authoring_trace(tmp_path, allowed_requests=[request()], **options)
        assert trace['generations'] == [] and trace['warnings']
    completed_path = next(tmp_path.glob('generation-*/step-00.completed.json'))
    completed_path.write_text('{broken')
    trace = project_authoring_trace(tmp_path, allowed_requests=[request()])
    assert trace['generations'] == [] and trace['warnings']


def test_large_inspection_is_explicitly_described_not_silently_truncated():
    body = request(); body['parent_system']['metadata']['huge'] = '日本語' * 40_000
    state = initial_draft(body)
    same, outcome = apply(state, {'tool': 'inspect', 'path': '/metadata/huge'}, body)
    assert same == state and outcome['ok']
    assert outcome['result']['value_included'] is False
    assert outcome['result']['descriptor']['length'] == 120_000
    assert outcome['result']['max_result_bytes'] == 96_000


def test_step_and_token_bounds_and_explicit_source_image_identity(tmp_path):
    for kwargs in ({'max_steps': True}, {'max_steps': 0}, {'max_steps': 65},
                   {'max_tokens': 511}, {'max_tokens': 8193}):
        with pytest.raises(ValueError):
            author(Model([]), tmp_path, **kwargs)
    with pytest.raises(ValueError, match='pinned model/provider/runtime'):
        StagedVocabularyGenerator(Model([]), tmp_path, image_id='wrong', provider_binding=BINDING)
