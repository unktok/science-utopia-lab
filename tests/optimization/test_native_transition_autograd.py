from dataclasses import replace
import pytest
import torch
from utopia.optimization.native_transition_autograd import (NativeBinding, NativeTrajectory,
    DeclaredLinearTerminalLoss, NativeTransitionSurrogate, IdentificationError, SupportError, heldout_directional_check)

BINDING = NativeBinding('QA-source', 'QA-no-model', 'QA-no-corpus', 'QA-world', 'QA-schema', ('resource',), ('institution',))
LOSS = DeclaredLinearTerminalLoss('QA-loss', 'QA-loss-hash', ('resource',), (-1.,))


def trajectory(name, controls, binding=BINDING):
    # Explicit numerical fixture, NEVER evidence about the native world.
    states = [(1.,)]
    for control, in controls:
        states.append((2 * states[-1][0] + 3 * control + 1,))
    return NativeTrajectory(name, binding, tuple(states), tuple(controls), tuple(f'QA-{name}-{i}' for i in range(4)), -states[-1][0])


def training():
    return [trajectory('baseline', [(0.,)] * 3)] + [trajectory(f'pulse-{i}', [(float(j == i),) for j in range(3)]) for i in range(3)]


def fitted():
    return NativeTransitionSurrogate.fit(training(), LOSS, ridge=0.)


def test_backward_composes_actual_annual_transitions_instead_of_freezing_state():
    model = fitted()
    controls = torch.full((3, 1), .25, dtype=torch.float64, requires_grad=True)
    loss, states, diagnostics = model.evaluate(torch.tensor([1.], dtype=torch.float64), controls)
    loss.backward()
    assert torch.allclose(controls.grad, torch.tensor([[-12.], [-6.], [-3.]], dtype=torch.float64), atol=1e-9, rtol=0)
    assert states.shape == (4, 1) and len(diagnostics) == 3


def test_unused_design_and_real_secant_validation():
    model = fitted()
    minus = trajectory('unused-minus', [(.2,)] * 3)
    plus = trajectory('unused-plus', [(.3,)] * 3)
    assert abs(model.validate_heldout(plus)['loss_error']) < 1e-9
    check = heldout_directional_check(model, minus, plus)
    assert check['absolute_error'] < 1e-9 and check['sign_agreement']


def test_static_controls_are_confounding_not_evidence_for_composable_derivatives():
    with pytest.raises(IdentificationError, match='confounded'):
        NativeTransitionSurrogate.fit([trajectory(f'static-{x}', [(x,)] * 3) for x in (-1., 0., 1., 2.)], LOSS)


def test_no_control_variation_fails_identification():
    with pytest.raises(IdentificationError, match='no independent'):
        NativeTransitionSurrogate.fit([trajectory(str(i), [(0.,)] * 3) for i in range(4)], LOSS)


@pytest.mark.parametrize('change,match', [({'declared_terminal_loss': 123.}, 'actual declared'),
    ({'checkpoint_sha256': ('',) * 4}, 'checkpoint'), ({'binding': replace(BINDING, model_digest='other')}, 'binding mismatch')])
def test_exact_loss_checkpoint_and_model_bindings(change, match):
    runs = training()
    with pytest.raises(ValueError, match=match):
        NativeTransitionSurrogate.fit([replace(runs[0], **change), *runs[1:]], LOSS)


def test_unsupported_extrapolation_and_training_relabelled_validation_rejected():
    model = fitted()
    with pytest.raises(SupportError):
        model.evaluate(torch.tensor([1.]), torch.full((3, 1), 100.))
    with pytest.raises(ValueError, match='used for training'):
        model.validate_heldout(training()[0])
    assert not model.provenance['full_native_world_autograd']
