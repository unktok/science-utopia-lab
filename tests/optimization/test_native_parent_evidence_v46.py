"""SCRIPTED parent-presentation treatment; no scientific model or world calls."""
from copy import deepcopy
import json

import pytest

from tests.optimization.test_native_authoring_ir import BINDING, IMAGE, request
from tests.optimization.test_native_bounded_author_context_v45 import Model, frame
from utopia.optimization.native_designer_tools_v25 import BOUNDED_AUTHORING as PROFILE
from utopia.optimization.native_parent_evidence_v46 import MODE, OPTION, describe, enabled
from utopia.optimization.native_staged_author_v15 import (
    StagedVocabularyGenerator, initial_draft, replay_staged_generation,
)
from utopia.system.design_patch import digest


def body():
    value = request()
    value.update(strategy_provenance={OPTION: MODE}, based_on_observation_id='actual-parent-observation')
    value['observations'] = [{
        'suggestion': {'suggestion_id': 'actual-parent', 'candidate': deepcopy(value['parent_system'])},
        'observation': {'observation_id': 'actual-parent-observation', 'status': 'complete',
            'candidate': deepcopy(value['parent_system']), 'loss': -18.,
            'metadata': {'measurements': [{'metrics': {'native.accepted_decisions':
                {'status': 'measured', 'value': 18}}}]}}}]
    return value


def test_planner_receives_exact_parent_and_join_without_host_source_interpretation():
    value = body()
    before = deepcopy(value)
    raw, messages = frame(value, initial_draft(value), [])
    data = json.loads(raw)
    assert data['literal_current_system'] == value['parent_system']
    evidence = data['planning_parent_evidence']
    assert evidence['parent_system_sha256'] == digest(value['parent_system'])
    assert evidence['selected_observation']['loss'] == -18.
    assert evidence['selected_observation']['suggestion_id'] == 'actual-parent'
    assert evidence['selected_observation']['observation_index'] == 0
    assert not evidence['new_code_executions'] and not evidence['parent_reselected']
    assert 'DO_NOT_EXECUTE_GENERATED_SOURCE' in messages[1]['content']
    assert 'DO_NOT_EXECUTE_GENERATED_SOURCE' not in messages[0]['content']
    assert data['000_current_turn']['authoring_workflow']['literal_current_system_included']
    assert value == before


def test_absent_treatment_keeps_legacy_structure_only_first_planner():
    value = body()
    del value['strategy_provenance'][OPTION]
    raw, _ = frame(value, initial_draft(value), [])
    data = json.loads(raw)
    assert data['literal_current_system'] is None
    assert 'planning_parent_evidence' not in data
    assert data['planning_system_structure']


@pytest.mark.parametrize('mutation', ['missing', 'duplicate', 'source', 'suggestion-source', 'null', 'withheld'])
def test_no_fabricated_or_ambiguous_parent_observation_join(mutation):
    value = body()
    row = value['observations'][0]
    if mutation == 'missing': value['based_on_observation_id'] = 'not-present'
    if mutation == 'duplicate': value['observations'].append(deepcopy(row))
    if mutation == 'source': row['observation']['candidate']['metadata']['unrelated'] = True
    if mutation == 'suggestion-source': row['suggestion']['candidate']['metadata']['unrelated'] = True
    if mutation == 'null': row['observation']['loss'] = None
    if mutation == 'withheld': row['observation']['loss_withheld'] = True
    with pytest.raises(ValueError, match='selected parent'):
        describe(value)


def test_unobserved_initial_parent_is_explicit_not_given_a_baseline_loss():
    value = request()
    info = describe(value)
    assert info['selected_observation'] is None and info['status'] == 'unobserved-initial-parent'


@pytest.mark.parametrize('mode', [False, True, None, 'unknown'])
def test_invalid_modes_do_not_silently_degrade_to_control(mode):
    value = body(); value['strategy_provenance'][OPTION] = mode
    with pytest.raises(ValueError, match='exact mode'):
        enabled(value, conversation_profile=PROFILE)


def test_oversized_treatment_is_not_silently_replaced_by_structure_only():
    value = body()
    value['parent_system']['metadata']['oversized'] = 'x' * 65537
    with pytest.raises(ValueError, match='no truncation or fallback'):
        frame(value, initial_draft(value), [])


def test_bounded_full_session_and_cold_replay_preserve_literal_edits(tmp_path):
    actions = [{'tool': 'plan', 'objective_reasoning': 'SCRIPTED unchanged loss',
                'design_intent': 'SCRIPTED retain or edit any legal institution'},
               {'tool': 'edit', 'operations': [{'op': 'add', 'path': '/metadata/own_literal', 'value': 7}]},
               {'tool': 'finish'}]
    # Four calls reserve a finish checkpoint at step1. Explicit retention is
    # legal; use a larger budget to exercise an actual editing call as well.
    model = Model(actions)
    generator = StagedVocabularyGenerator(model, tmp_path/'author', image_id=IMAGE,
        provider_binding=BINDING, max_steps=8, max_tokens=8192, conversation_profile=PROFILE)
    result = generator(body())
    assert 'generation_failure' not in result and len(model.calls) == 3
    folder = next((tmp_path/'author').glob('generation-*'))
    assert replay_staged_generation(folder) == result and len(model.calls) == 3
    assert result['base_patch']['operations'] == [{'op': 'add', 'path': '/metadata/own_literal', 'value': 7}]
    assert json.loads(model.calls[0]['prompt'])['planning_parent_evidence']['selected_observation']['loss'] == -18.
    assert 'planning_parent_evidence' not in json.loads(model.calls[1]['prompt'])


def test_unsupported_profile_rejects_before_any_model_call(tmp_path):
    value = body()
    with pytest.raises(ValueError, match='bounded author profile'):
        enabled(value, conversation_profile='plain-function-recovery-v44')


def test_actual_calibration_api_preserves_treatment_and_cold_certificate(tmp_path, monkeypatch):
    from tests.optimization.test_native_designer_contract_v16 import ScriptedSession
    from utopia.optimization import native_designer_preflight as preflight
    monkeypatch.setattr('requests.Session', ScriptedSession)
    ScriptedSession.calls = []
    value = body()
    certificate = preflight.run_calibration(tmp_path/'calibration', request=value,
        provider=BINDING, scope=preflight.EXECUTION_SCOPE, conversation_profile=PROFILE)
    assert certificate['all_controls_passed']
    assert certificate['plan']['request']['strategy_provenance'][OPTION] == MODE
    preflight.require_certificate(tmp_path/'calibration/certificate.json', BINDING,
        protocol='staged-v15', scope=preflight.EXECUTION_SCOPE, conversation_profile=PROFILE)
