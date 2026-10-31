"""Compositional autograd of a local representation fitted to native trajectories.

Native forward simulations are unchanged. These are approximate native-world
derivatives, exact only for the fitted representation, not token backprop or
whole-function finite differences disguised as a custom backward operation.
"""
from dataclasses import dataclass, asdict
import torch

DTYPE = torch.float64


class IdentificationError(ValueError):
    pass


class SupportError(ValueError):
    pass


def tensor(value):
    return torch.as_tensor(value, dtype=DTYPE)


def rank(value, rtol):
    values = torch.linalg.svdvals(value)
    return 0 if not values.numel() or float(values[0]) == 0 else int((values > values[0] * rtol).sum())


@dataclass(frozen=True)
class NativeBinding:
    source_commit: str
    model_digest: str
    corpus_sha256: str
    initial_world_sha256: str
    feature_schema_sha256: str
    state_names: tuple[str, ...]
    coordinate_names: tuple[str, ...]

    def validate(self):
        if any(not value for value in asdict(self).values()):
            raise ValueError('nonempty native identity/state/coordinate binding required')
        if len(set(self.state_names)) != len(self.state_names) or len(set(self.coordinate_names)) != len(self.coordinate_names):
            raise ValueError('duplicate native feature/coordinate names')


@dataclass(frozen=True)
class DeclaredLinearTerminalLoss:
    loss_id: str
    loss_spec_sha256: str
    state_names: tuple[str, ...]
    coefficients: tuple[float, ...]
    offset: float = 0.

    def __post_init__(self):
        if not self.loss_id or not self.loss_spec_sha256 or len(self.coefficients) != len(self.state_names) or not torch.isfinite(tensor([*self.coefficients, self.offset])).all():
            raise ValueError('finite exact declared terminal-loss binding required')

    def __call__(self, state):
        return (state * state.new_tensor(self.coefficients)).sum(-1) + self.offset


@dataclass(frozen=True)
class NativeTrajectory:
    run_id: str
    binding: NativeBinding
    states: tuple[tuple[float, ...], ...]
    controls: tuple[tuple[float, ...], ...]
    checkpoint_sha256: tuple[str, ...]
    declared_terminal_loss: float

    def validate(self, binding, loss):
        if self.binding != binding:
            raise ValueError('native model/corpus/source/world binding mismatch')
        if not self.run_id or len(self.states) != len(self.controls) + 1 or len(self.checkpoint_sha256) != len(self.states) or not all(self.checkpoint_sha256):
            raise ValueError('complete native state/control/checkpoint evidence required')
        x, u = tensor(self.states), tensor(self.controls)
        if x.ndim != 2 or x.shape[1] != len(binding.state_names) or u.ndim != 2 or u.shape[1] != len(binding.coordinate_names):
            raise ValueError('native state/control shapes do not match binding')
        if not torch.isfinite(x).all() or not torch.isfinite(u).all():
            raise ValueError('nonfinite native features/controls')
        if abs(float(loss(x[-1])) - self.declared_terminal_loss) > 1e-10:
            raise ValueError('tensor terminal loss differs from actual declared native loss')


@dataclass
class LocalYearModel:
    year: int
    state_center: torch.Tensor
    state_basis: torch.Tensor
    state_scale: torch.Tensor
    control_center: torch.Tensor
    control_scale: torch.Tensor
    weights: torch.Tensor
    max_training_radius: float
    max_state_residual: float
    diagnostics: dict

    def predict(self, state, control):
        centered = state - self.state_center
        projected = centered @ self.state_basis
        features = torch.cat((state.new_ones(1), projected / self.state_scale,
            (control - self.control_center) / self.control_scale))
        return features @ self.weights, {'year': self.year,
            'normalized_radius': float(torch.linalg.vector_norm(features[1:]).detach()),
            'training_max_radius': self.max_training_radius,
            'state_off_manifold_norm': float(torch.linalg.vector_norm(centered - projected @ self.state_basis.T).detach()),
            'training_max_state_residual': self.max_state_residual}


@dataclass
class NativeTransitionSurrogate:
    binding: NativeBinding
    loss: DeclaredLinearTerminalLoss
    years: list[LocalYearModel]
    provenance: dict

    @classmethod
    def fit(cls, trajectories, loss, *, rank_rtol=1e-9, ridge=1e-8):
        if len(trajectories) < 2:
            raise IdentificationError('at least two actual native interventions required')
        binding = trajectories[0].binding
        binding.validate()
        if loss.state_names != binding.state_names or ridge < 0 or not torch.isfinite(tensor(ridge)):
            raise ValueError('matching state/loss schema and finite nonnegative ridge required')
        if len({r.run_id for r in trajectories}) != len(trajectories):
            raise ValueError('duplicate trajectory identity')
        horizon = len(trajectories[0].controls)
        for run in trajectories:
            run.validate(binding, loss)
            if len(run.controls) != horizon or not torch.allclose(tensor(run.states[0]), tensor(trajectories[0].states[0]), atol=1e-12, rtol=0):
                raise ValueError('native intervention horizons/initial state differ')
        years = []
        for year in range(horizon):
            x = tensor([r.states[year] for r in trajectories])
            y = tensor([r.states[year + 1] for r in trajectories])
            u = tensor([r.controls[year] for r in trajectories])
            center = x.mean(0)
            centered = x - center
            _, _, vh = torch.linalg.svd(centered, full_matrices=False)
            state_rank = rank(centered, rank_rtol)
            basis = vh[:state_rank].T.contiguous()
            coordinates = centered @ basis
            scale = coordinates.square().mean(0).sqrt().clamp_min(1e-12)
            ucenter = u.mean(0)
            uscale = (u - ucenter).square().mean(0).sqrt()
            if bool((uscale <= 1e-12).any()):
                raise IdentificationError(f'year {year + 1}: no independent coordinate intervention')
            nuisance = torch.cat((x.new_ones(x.shape[0], 1), coordinates / scale), dim=1)
            su = (u - ucenter) / uscale
            residual = su - nuisance @ torch.linalg.lstsq(nuisance, su, driver='gelsd').solution
            control_rank = rank(residual, rank_rtol)
            if control_rank < u.shape[1] or float(torch.linalg.matrix_norm(residual)) <= 1e-8:
                raise IdentificationError(f'year {year + 1}: prior state and control confounded; use independent annual pulses')
            design = torch.cat((nuisance, su), dim=1)
            design_rank = rank(design, rank_rtol)
            if design_rank != design.shape[1] or x.shape[0] < design.shape[1]:
                raise IdentificationError(f'year {year + 1}: native transition design is rank deficient')
            regularizer = torch.eye(design.shape[1], dtype=DTYPE) * ridge
            regularizer[0, 0] = 0
            weights = torch.linalg.solve(design.T @ design + regularizer, design.T @ y)
            state_residual = centered - coordinates @ basis.T
            diagnostics = {'year': year + 1, 'native_transitions': x.shape[0], 'observed_state_rank': state_rank,
                'design_rank': design_rank, 'design_columns': design.shape[1], 'independent_control_rank': control_rank,
                'residual_control_norm': float(torch.linalg.matrix_norm(residual)),
                'training_rmse_per_state': (design @ weights - y).square().mean(0).sqrt().tolist(),
                'design_singular_values': torch.linalg.svdvals(design).tolist(), 'ridge': ridge}
            years.append(LocalYearModel(year + 1, center, basis, scale, ucenter, uscale, weights,
                float(torch.linalg.vector_norm(design[:, 1:], dim=1).max()),
                float(torch.linalg.vector_norm(state_residual, dim=1).max()), diagnostics))
        return cls(binding, loss, years, {'method': 'native-calibrated-local-transition-autograd',
            'derivative_semantics': 'exact autograd of fitted local representation; approximate native-world gradients, not native pathwise backprop',
            'binding': asdict(binding), 'loss': asdict(loss), 'training_runs': [asdict(r) for r in trajectories],
            'years': [m.diagnostics for m in years], 'full_native_world_autograd': False})

    def rollout(self, initial_state, controls, *, support_multiplier=2., state_residual_atol=1e-7, require_support=True):
        state, controls = tensor(initial_state), tensor(controls)
        if tuple(controls.shape) != (len(self.years), len(self.binding.coordinate_names)) or tuple(state.shape) != (len(self.binding.state_names),):
            raise ValueError('surrogate query dimension mismatch')
        if not torch.isfinite(state).all() or not torch.isfinite(controls).all() or not support_multiplier >= 1 or not state_residual_atol >= 0:
            raise ValueError('finite native query and explicit positive support settings required')
        # A radius test alone can accept points outside the control simplex.
        # Check whole schedules, not just independent per-year ranges.
        if require_support:
            from scipy.optimize import linprog
            schedules = tensor([r['controls'] for r in self.provenance['training_runs']]).reshape(len(self.provenance['training_runs']), -1)
            matrix = torch.cat((schedules.T, schedules.new_ones(1, len(schedules))), dim=0).numpy()
            target = torch.cat((controls.detach().flatten(), controls.new_ones(1))).numpy()
            hull = linprog([0.] * len(schedules), A_eq=matrix, b_eq=target, bounds=(0., None), method='highs')
            if not hull.success:
                raise SupportError('control schedule outside native calibration convex hull')
        states, diagnostics = [state], []
        for model, control in zip(self.years, controls):
            state, info = model.predict(state, control)
            info['within_radius'] = info['normalized_radius'] <= support_multiplier * max(model.max_training_radius, 1e-12)
            info['within_state_manifold'] = info['state_off_manifold_norm'] <= max(state_residual_atol, support_multiplier * model.max_state_residual)
            diagnostics.append(info)
            if require_support and not (info['within_radius'] and info['within_state_manifold']):
                raise SupportError(f'year {model.year}: query outside measured native calibration support')
            states.append(state)
        return torch.stack(states), diagnostics

    def evaluate(self, initial_state, controls, **kwargs):
        states, diagnostics = self.rollout(initial_state, controls, **kwargs)
        return self.loss(states[-1]), states, diagnostics

    def validate_heldout(self, run, **kwargs):
        run.validate(self.binding, self.loss)
        if run.run_id in {r['run_id'] for r in self.provenance['training_runs']}:
            raise ValueError('validation design was used for training')
        loss, states, support = self.evaluate(tensor(run.states[0]), tensor(run.controls), **kwargs)
        return {'run_id': run.run_id, 'checkpoint_sha256': list(run.checkpoint_sha256),
            'predicted_loss': float(loss.detach()), 'actual_native_loss': run.declared_terminal_loss,
            'loss_error': float(loss.detach()) - run.declared_terminal_loss,
            'state_rmse_per_year': (states.detach() - tensor(run.states)).square().mean(1).sqrt().tolist(), 'support': support}


def heldout_directional_check(model, minus, plus):
    for run in (minus, plus):
        run.validate(model.binding, model.loss)
        if run.run_id in {r['run_id'] for r in model.provenance['training_runs']}:
            raise ValueError('directional check endpoint is a training design')
    left, right = tensor(minus.controls), tensor(plus.controls)
    delta = right - left
    distance = torch.linalg.vector_norm(delta)
    if float(distance) <= 0 or not torch.equal(tensor(minus.states[0]), tensor(plus.states[0])):
        raise ValueError('matched initial world and distinct controls required')
    midpoint = ((left + right) / 2).detach().requires_grad_(True)
    loss, _, support = model.evaluate(tensor(minus.states[0]), midpoint)
    gradient, = torch.autograd.grad(loss, midpoint)
    predicted = float((gradient * delta / distance).sum())
    actual = (plus.declared_terminal_loss - minus.declared_terminal_loss) / float(distance)
    return {'method': 'unused-native-secant-vs-composed-autograd', 'minus_run': minus.run_id, 'plus_run': plus.run_id,
        'predicted_directional_derivative': predicted, 'actual_native_secant': actual,
        'absolute_error': abs(predicted - actual), 'sign_agreement': None if abs(actual) < 1e-12 or abs(predicted) < 1e-12 else predicted * actual > 0,
        'gradient': gradient.tolist(), 'support': support}
