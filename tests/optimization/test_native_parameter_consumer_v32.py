"""SCRIPTED adapter semantics/notice checks; not scientific outcomes or vetoes."""
from copy import deepcopy
from types import SimpleNamespace

import pytest

from tests.optimization.test_native_authoring_ir import IMAGE, request
from tests.optimization.test_native_staged_author_v15 import apply
from utopia.optimization.native_contract_notices import (
    STAGE_PARAMETER_RULE, contract_notices, notice_summary)
from utopia.optimization.native_staged_author_v15 import initial_draft


@pytest.mark.parametrize('identity,implementation,parameters', [
    ('world.review', 'native.phase.review.v1', {'required_reviewers': 3}),
    ('world.submission', 'native.activity.submission.v1', {'pre_screening_enabled': True})])
def test_actual_v31_metadata_edits_still_compile_finish_and_receive_nonveto_consumer_notice(identity, implementation, parameters):
    from utopia.system.native_open_examples import open_native_system
    body = request()
    body['parent_system'] = open_native_system(IMAGE).to_dict()
    original = deepcopy(body['parent_system'])
    draft, receipt = apply(initial_draft(body), {'tool': 'edit_fields',
        'mechanism_id': identity, 'field_updates': [{'field_name': 'parameters', 'value': parameters}]}, body)
    assert receipt['ok'] and receipt['result']['validation']['valid']
    node = next(n for n in draft['document']['mechanisms'] if n['mechanism_id'] == identity)
    assert node['implementation'] == implementation and node['parameters'] == parameters
    notices = receipt['result']['validation']['execution_contract_notices']
    assert notices['warning_is_not_a_veto']
    notice = next(n for n in notices['notices'] if n.get('mechanism_id') == identity)
    assert notice['code'] == 'original-stage-adapter-does-not-read-parameters'
    assert notice['parameter_names'] == sorted(parameters)
    assert notice['message'] == STAGE_PARAMETER_RULE
    assert not notice['changes_validity'] and not notice['authored_value_changed_by_host']
    _, finished = apply(draft, {'tool': 'finish', 'rationale': 'SCRIPTED inert data remains legal'}, body)
    assert finished['ok'] and finished['definition'] is not None
    assert body['parent_system'] == original


def test_known_adapter_set_is_exact_and_unknown_code_tensor_or_future_implementations_are_not_guessed():
    from utopia.system.native_kernel import STAGES
    names = ['native.phase.' + stage + '.v1' for stage, _ in STAGES]
    names += ['native.activity.' + stage + '.v1' for stage in
              ('resubmissions', 'research', 'collaboration', 'submission', 'funding')]
    unknown = [None, [], {}, 123, 'native.phase.unregistered.v1',
               'native.activity.unregistered.v1', 'program.tensor.v1', 'code.python.v1']
    nodes = [{'mechanism_id': 'SCRIPTED-' + str(i), 'implementation': impl,
              'parameters': {'arbitrary/policy~name': True}} for i, impl in enumerate(names + unknown)]
    notices = contract_notices({'mechanisms': nodes})
    assert len(notices) == len(names)
    assert [n['implementation'] for n in notices] == names
    assert all(n['parameter_names'] == ['arbitrary/policy~name'] for n in notices)
    for node in nodes:
        node['parameters'] = {}
    assert contract_notices({'mechanisms': nodes}) == []


def test_wrapped_adapter_notice_keeps_owner_delegate_path_and_explicit_omissions():
    inner = {'mechanism_id': 'SCRIPTED-review', 'implementation': 'native.phase.review.v1',
             'parameters': {'unconsumed': 42}}
    body = {'mechanisms': [{'mechanism_id': 'SCRIPTED-wrapper',
             'implementation': 'native.process.activity.v1', 'parameters': {'delegate': inner}}]}
    original = deepcopy(body)
    notice = contract_notices(body)[0]
    assert notice['mechanism_id'] == 'SCRIPTED-wrapper'
    assert notice['executed_mechanism_id'] == 'SCRIPTED-review'
    assert notice['path'] == '/mechanisms/0/parameters/delegate/parameters'
    assert body == original
    body['mechanisms'] *= 3
    summary = notice_summary(body, limit=1)
    assert summary['total_count'] == 3 and summary['omitted_count'] == 2
    assert not summary['complete'] and summary['warning_is_not_a_veto']


def test_original_review_handler_does_not_consume_mechanism_parameters():
    from utopia.system.native_kernel import NativeScienceKernel
    calls = []
    sim = SimpleNamespace(
        portable_safe_point=lambda: calls.append('safe-point'),
        _run_phase_3_peer_review=lambda year, result: calls.append(('review', year)),
        _apply_strategy_quality_adjustment=lambda year: calls.append(('quality', year)),
        wandb_logger=SimpleNamespace(log_phase=lambda *args: calls.append(('log', args[1]))))
    class Context:
        @property
        def mechanism(self):
            raise AssertionError('original review handler unexpectedly read mechanism configuration')
    kernel = SimpleNamespace(_simulation=sim, _frame={'year': 42, 'results': {}},
                             observation=lambda: {'SCRIPTED': 'same actual handler result'})
    result = NativeScienceKernel._stage(kernel, 'review', Context())
    assert calls == ['safe-point', ('review', 42), ('log', 3), ('quality', 42)]
    assert result.outputs['world'][0].payload == {'SCRIPTED': 'same actual handler result'}


def test_original_submission_handler_does_not_consume_mechanism_parameters(monkeypatch):
    import utopia.system.native_activity_contracts as adapters
    calls = []
    sim = SimpleNamespace(
        portable_safe_point=lambda: calls.append('safe-point'),
        _run_phase_2_submit_papers=lambda *args: calls.append('submit') or [],
        _record_paper_metadata_batch=lambda year: calls.append('metadata'),
        wandb_logger=SimpleNamespace(log_phase=lambda *args: calls.append('log')))
    monkeypatch.setattr(adapters, '_read_plan', lambda *args: ({}, {}, []))
    monkeypatch.setattr(adapters, '_read_papers', lambda *args: [])
    class Context:
        @property
        def mechanism(self):
            raise AssertionError('original submission adapter unexpectedly read mechanism configuration')
    kernel = SimpleNamespace(_simulation=sim, _frame={'year': 42, 'results': {}},
                             observation=lambda: {'SCRIPTED': 'same actual handler result'})
    result = adapters._stage(kernel, 'submission', Context())
    assert calls == ['safe-point', 'submit', 'metadata', 'log']
    assert result.outputs['world'][0].payload == {'SCRIPTED': 'same actual handler result'}


def test_parameter_contract_is_source_owned_in_editor_only():
    from tests.optimization.test_native_planning_author_v22 import prompt
    from utopia.optimization.native_staged_author_v15 import (
        ABI_CONTRACT, PLAN_SYSTEM_PROMPT, SYSTEM_PROMPT, build_conversation)
    body = request()
    body['parent_system']['metadata']['instruction'] = 'DO NOT ADD THIS TO SYSTEM'
    state = initial_draft(body)
    editor = build_conversation(prompt(body, state, []), SYSTEM_PROMPT, native_tools=True)
    planner = build_conversation(prompt(body, state, []), PLAN_SYSTEM_PROMPT, native_tools=True)
    assert STAGE_PARAMETER_RULE in ABI_CONTRACT and STAGE_PARAMETER_RULE in editor[0]['content']
    assert STAGE_PARAMETER_RULE not in planner[0]['content']
    assert 'DO NOT ADD THIS TO SYSTEM' not in editor[0]['content']
