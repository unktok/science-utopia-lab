"""Offline input projection guards with SCRIPTED source, never model inference."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path

import pytest

from scripts.reports.native_parent_presentation_preparation_v1 import project
from tests.optimization.test_native_parent_evidence_v46 import body
from tests.optimization.test_native_bounded_author_context_v45 import Model
from tests.optimization.test_native_authoring_ir import BINDING, IMAGE
from utopia.optimization.native_designer_tools_v25 import BOUNDED_AUTHORING as PROFILE
from utopia.optimization.native_parent_evidence_v46 import OPTION
from utopia.optimization.native_staged_author_v15 import (
    StagedVocabularyGenerator, build_prompt, initial_draft,
)
from utopia.system.design_patch import digest


def inputs(tmp_path):
    request = body()
    del request['strategy_provenance'][OPTION]
    author = StagedVocabularyGenerator(Model([]), tmp_path, image_id=IMAGE,
        provider_binding=BINDING, max_steps=16, max_tokens=8192, conversation_profile=PROFILE)
    binding = author._binding(request)
    prompt = build_prompt(request, initial_draft(request), [], image_id=IMAGE,
        binding_sha256=binding['binding_sha256'], settings=binding['settings'])
    return binding, {'step': 0, 'prompt': prompt, 'prompt_sha256': digest(prompt)}


def test_offline_control_is_exact_and_treatment_changes_only_its_own_projection(tmp_path):
    binding, started = inputs(tmp_path)
    before = deepcopy((binding, started))
    result = project(binding, started, source='c'*40)
    assert result['control']['historical_control_prompt_identical']
    assert not result['control']['literal_parent_included']
    assert result['literal']['literal_parent_included']
    assert result['literal']['planning_parent_evidence']['selected_observation']['loss'] == -18.
    for arm in result.values():
        assert arm['capacity']['actual_wire_utf8_bytes'] <= arm['capacity']['maximum_wire_utf8_bytes']
        assert arm['capacity']['observed_prompt_eval_count'] is None
        assert arm['capacity']['full_output_reservation_fits_observed_prompt'] is None
    assert (binding, started) == before


@pytest.mark.parametrize('part', ['binding', 'request', 'prompt', 'stale-prompt', 'step'])
def test_changed_inputs_do_not_pass_as_historical_identity(tmp_path, part):
    binding, started = inputs(tmp_path)
    if part == 'binding': binding['binding_sha256'] = '0'*64
    if part == 'request':
        binding['request_sha256'] = '0'*64
        binding['binding_sha256'] = digest({k:v for k,v in binding.items() if k != 'binding_sha256'})
    if part == 'prompt': started['prompt_sha256'] = '0'*64
    if part == 'stale-prompt':
        started['prompt'] += 'stale'
        started['prompt_sha256'] = digest(started['prompt'])
    if part == 'step': started['step'] = 1
    with pytest.raises(ValueError):
        project(binding, started, source='c'*40)


def test_retained_actual_six_request_projections_are_not_backend_readiness():
    from utopia.optimization.native_numeric_designer import checked
    path = Path(__file__).resolve().parents[2]/'research/data/native-parent-presentation-preparation-v1/preparation.json'
    assert hashlib.sha256(path.read_bytes()).hexdigest() == '23e68351aba2b4e283f7ea81c8dca88a1f785fcc7a6c08dc4989ca740dd14ef6'
    value = checked(json.loads(path.read_text()))
    assert value['analysis_source_commit'] == 'bdfdb710582de4efd6bc81f30670e1b654631f9e'
    assert len(value['slots']) == 6
    assert {(r['objective'], r['generation']) for r in value['slots']} == {
        (o, g) for o in ('throughput', 'content-utility') for g in range(3)}
    for row in value['slots']:
        assert row['projections']['control']['historical_control_prompt_identical']
        treatment = row['projections']['literal']
        assert treatment['literal_parent_included']
        assert treatment['capacity']['observed_prompt_eval_count'] is None
        assert treatment['capacity']['full_output_reservation_fits_observed_prompt'] is None
        assert 159603 <= treatment['capacity']['actual_wire_utf8_bytes'] <= 166754
        expected = -18. if row['objective'] == 'throughput' else -13.333333333333332
        assert treatment['planning_parent_evidence']['selected_observation']['loss'] == expected
    for key in ('new_model_calls', 'new_code_executions', 'new_native_worlds',
                'backend_token_capacity_verified', 'actual_backend_readiness_verified',
                'new_experiment_dispatched', 'publication_ready'):
        assert not value[key]
