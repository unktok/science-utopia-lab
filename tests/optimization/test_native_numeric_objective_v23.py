"""SCRIPTED arithmetic/prose separation; no model or new scientific world."""
from copy import deepcopy
import json

import pytest

from tests.optimization.test_native_authoring_ir import BINDING
from tests.optimization.test_native_objective_view_v21 import body
from utopia.optimization.loss import evaluate_loss, loss_spec_sha256
from utopia.optimization.native_objective_view import loss_arithmetic, objective_view, wire_objective_view
from utopia.optimization.native_staged_author_v15 import (
    build_conversation, build_prompt, call_task, initial_draft)


@pytest.mark.parametrize('budget', [1, 16])
def test_registry_prose_stays_archived_not_a_second_objective_in_actual_frames(budget):
    value = body()
    marker = 'SCRIPTED_NONCOMPUTATIONAL_PROSE_MARKER'
    spec = value['loss_spec']
    spec['interpretation'] = marker
    for field in ('id', 'version', 'status', 'optimization_seed_role'):
        spec[field] += marker
    spec['per_run']['commentary'] = marker
    spec['per_run']['terms'][0]['description'] = marker
    spec['across_seeds']['annotation'] = marker
    metadata = value['observations'][0]['observation']['metadata']
    metadata['loss_spec_sha256'] = loss_spec_sha256(spec)
    before = deepcopy(value)
    prompt = build_prompt(value, initial_draft(value), [], image_id=BINDING['image_id'],
        binding_sha256='d' * 64, settings={'max_steps': budget})
    # Source request and host prompt retain the full original, with no repair.
    assert json.loads(prompt)['exact_loss_spec'] == spec
    assert marker in prompt
    messages = build_conversation(prompt, call_task(0, budget))
    assert marker not in json.dumps(messages)
    assert 'loss_arithmetic' in json.dumps(messages)
    assert loss_spec_sha256(spec) in json.dumps(messages)
    assert value == before
    breakdown = objective_view(value, initial_draft(value))['own_observation_breakdowns'][0]
    assert breakdown['recorded_loss'] == breakdown['recomputed_from_recorded_measurements']['loss'] == 8.0
    assert breakdown['recomputed_matches_recorded_loss'] is True


@pytest.mark.parametrize('coefficient', [-2.5, 0.0, 3.0])
@pytest.mark.parametrize('dispersion', [0.0, 2.0])
def test_projection_preserves_exact_existing_loss_arithmetic_and_seed_aggregation(coefficient, dispersion):
    value = body('native-joint-v5-throughput')
    spec = value['loss_spec']
    spec['per_run']['intercept'] = 7.0
    spec['per_run']['terms'][0]['coefficient'] = coefficient
    spec['across_seeds'].update(dispersion_weight=dispersion, minimum_valid_runs=2)
    measurements = value['observations'][0]['observation']['metadata']['measurements']
    second = deepcopy(measurements[0])
    second['run_id'] = 'SCRIPTED-second-run'
    second['metrics']['native.accepted_decisions']['value'] = 3
    measurements.append(second)
    before = deepcopy(spec)
    projected = loss_arithmetic(spec)
    assert projected['archived_loss_spec_sha256'] == loss_spec_sha256(spec)
    assert projected['per_run'] == spec['per_run']
    assert projected['across_seeds'] == spec['across_seeds']
    reconstructed = {**spec, 'per_run': projected['per_run'], 'across_seeds': projected['across_seeds']}
    assert evaluate_loss(reconstructed, measurements) == evaluate_loss(spec, measurements)
    assert spec == before
    assert not projected['candidate_policy_supplied'] and not projected['extra_eligibility_constraint']


def test_term_slices_and_missing_measurements_are_preserved_not_filled():
    value = body('native-joint-v5-throughput')
    spec = value['loss_spec']
    spec['per_run']['terms'][0]['slice_id'] = 'SCRIPTED-slice'
    projected = loss_arithmetic(spec)
    assert projected['per_run']['terms'][0]['slice_id'] == 'SCRIPTED-slice'
    original = value['observations'][0]['observation']['metadata']['measurements']
    result = evaluate_loss(spec, original)
    assert result['loss'] is None and result['status'] == 'insufficient_valid_runs'
    reconstructed = {**spec, 'per_run': projected['per_run'], 'across_seeds': projected['across_seeds']}
    assert evaluate_loss(reconstructed, original) == result


def test_metric_definitions_describe_measurements_not_new_scores_or_candidate_rules():
    value = loss_arithmetic(body()['loss_spec'])
    definitions = value['measurement_definitions']
    assert set(definitions) == {'native.accepted_peer_score_sum', 'native.review_records'}
    assert 'original native reviewer overall_score' in definitions['native.accepted_peer_score_sum']
    assert 'final_score is not an input' in definitions['native.accepted_peer_score_sum']
    assert 'not papers' in definitions['native.review_records']
    assert value['metrics_without_text_definition'] == []
    spec = body()['loss_spec']
    spec['per_run']['terms'][0]['metric_id'] = 'SCRIPTED-unregistered-metric'
    unknown = loss_arithmetic(spec)
    assert unknown['metrics_without_text_definition'] == ['SCRIPTED-unregistered-metric']
    assert 'SCRIPTED-unregistered-metric' not in unknown['measurement_definitions']


def test_invalid_arithmetic_still_rejects_instead_of_normalizing_it():
    spec = body()['loss_spec']
    spec['per_run']['terms'][0]['coefficient'] = True
    with pytest.raises(ValueError, match='coefficient'):
        loss_arithmetic(spec)


@pytest.mark.parametrize('binding', ['correct', 'foreign', None])
def test_wire_feedback_keeps_every_scalar_failure_and_full_hash_without_mutating_original(binding):
    value = body()
    if binding != 'correct':
        value['observations'][0]['observation']['metadata']['loss_spec_sha256'] = binding
    view = objective_view(value, initial_draft(value))
    before = deepcopy(view)
    projected = wire_objective_view(view)
    assert view == before
    original = before['own_observation_breakdowns'][0]
    actual = projected['own_observation_breakdowns'][0]
    assert actual['recorded_loss'] == original['recorded_loss']
    assert actual['recorded_status'] == original['recorded_status']
    assert actual['technical_failures'] == original['technical_failures']
    expected = deepcopy(original['recomputed_from_recorded_measurements'])
    if 'loss_spec' in expected:
        expected['loss_spec'] = {'sha256': expected['loss_spec']['sha256']}
    assert actual['recomputed_from_recorded_measurements'] == expected
