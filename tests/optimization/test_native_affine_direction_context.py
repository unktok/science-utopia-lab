"""Prospective arithmetic display, not proof of better model reasoning."""
from copy import deepcopy
import json

import pytest

from tests.optimization.test_native_objective_view_v21 import body
from tests.optimization.test_native_authoring_ir import BINDING
from utopia.optimization.loss import evaluate_loss,loss_spec_sha256
from utopia.optimization.native_objective_view import loss_arithmetic,objective_view
from utopia.optimization.native_staged_author_v15 import build_prompt,initial_draft
from utopia.optimization.native_designer_tools_v25 import BOUNDED_AUTHORING


@pytest.mark.parametrize('coefficient,direction',[(-2.5,'increase'),(0.,'none'),(3.,'decrease')])
def test_per_run_direction_is_exact_coefficient_algebra_not_a_new_objective(coefficient,direction):
    request=body('native-joint-v5-throughput');spec=request['loss_spec']
    spec['per_run']['terms'][0]['coefficient']=coefficient
    spec['across_seeds']['dispersion_weight']=2.
    before=deepcopy(spec)
    view=loss_arithmetic(spec);term=view['per_run_affine_directions'][0]
    assert term['per_run_loss_change_for_one_unit_increase_other_inputs_fixed']==coefficient
    assert term['metric_change_that_lowers_per_run_loss_other_inputs_fixed']==direction
    assert spec==before and view['per_run']==spec['per_run']
    assert view['across_seeds']==spec['across_seeds']
    assert view['archived_loss_spec_sha256']==loss_spec_sha256(spec)
    assert 'Aggregate dispersion' in view['direction_scope']
    assert 'not each input metric separately' in view['quantity_to_minimize']
    assert not view['candidate_policy_supplied'] and not view['extra_eligibility_constraint']


def test_bounded_first_planner_contains_sign_direction_and_does_not_touch_observations():
    request=body('native-joint-v5-throughput');before=deepcopy(request)
    prompt=build_prompt(request,initial_draft(request),[],image_id=BINDING['image_id'],
        binding_sha256='d'*64,settings={'max_steps':16,'conversation_profile':BOUNDED_AUTHORING})
    view=json.loads(prompt)['loss_arithmetic']
    assert view['per_run']['terms'][0]['coefficient']==-1.
    assert view['per_run_affine_directions'][0][
        'metric_change_that_lowers_per_run_loss_other_inputs_fixed']=='increase'
    assert view['per_run_affine_directions']==objective_view(request,initial_draft(request))['terms']
    assert request==before
    # Existing canonical measurement/loss remains the evaluator's result.
    original=evaluate_loss(request['loss_spec'],request['observations'][0]['observation']['metadata']['measurements'])
    reconstructed={**request['loss_spec'],'per_run':view['per_run'],'across_seeds':view['across_seeds']}
    assert evaluate_loss(reconstructed,request['observations'][0]['observation']['metadata']['measurements'])==original


def test_two_term_directions_are_not_both_minimized_and_preserve_slice_identity():
    request=body();spec=request['loss_spec'];spec['per_run']['terms'][0]['slice_id']='SCRIPTED-slice'
    view=loss_arithmetic(spec)
    assert [t['metric_change_that_lowers_per_run_loss_other_inputs_fixed']
        for t in view['per_run_affine_directions']]==['increase','decrease']
    assert view['per_run_affine_directions'][0]['slice_id']=='SCRIPTED-slice'
