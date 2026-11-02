"""Conditional mixed-design likelihood-ratio gradients, not world derivatives.

Native losses are opaque. A frozen prior-only polynomial control variate is
subtracted from score terms and its exact conditional expectation derivative is
added back. Conditional discrete probabilities come from the caller's existing
policy, including its support restrictions; they are never re-normalized over
observed designs. This module performs no inference, sampling or parameter update.
"""
from __future__ import annotations

from dataclasses import dataclass
import json
import math

import torch


SCHEMA = 'scienceutopia.native-expectation-estimator.v11'


def _key(assignment):
    if (not isinstance(assignment, dict)
            or any(not isinstance(k, str) or not isinstance(v, str) for k, v in assignment.items())):
        raise ValueError('assignments must map string factor IDs to string choices')
    return json.dumps(assignment, sort_keys=True, separators=(',', ':'))


def _number(value):
    return type(value) in (int, float) and math.isfinite(value)


def _ids(values, count, label, *, unique=True):
    if (not isinstance(values, (list, tuple)) or len(values) != count
            or any(not isinstance(v, str) or not v for v in values)
            or unique and len(set(values)) != len(values)):
        raise ValueError(f'explicit {label} of matching length required')
    return tuple(values)


def _rows(draws, losses, assignment_keys, latent_dim):
    if not draws or len(draws) != len(losses):
        raise ValueError('nonempty aligned complete draws/losses required; failed draws cannot be dropped')
    result = []
    for draw, loss in zip(draws, losses):
        if (not isinstance(draw, dict) or not _number(loss)
                or draw.get('technical_error') is not None):
            raise ValueError('every loss/draw must be finite and technically complete')
        key = _key(draw.get('assignment'))
        latent = draw.get('latent')
        if (key not in assignment_keys or not isinstance(latent, (list, tuple))
                or len(latent) != latent_dim or any(not _number(z) for z in latent)):
            raise ValueError('draw lies outside declared assignment/latent support')
        result.append((key, tuple(float(z) for z in latent)))
    return result


@dataclass(frozen=True)
class FrozenDesignControlVariate:
    """Immutable prior-fitted c(a,z)=b + u.z + v.z² + w[a].

    Joint-assignment indicators support arbitrary conditional factor dependence.
    Exact enumeration is bounded by the upstream grammar's existing support cap.
    No claim is made that this fitted model is a faithful world representation.
    """

    assignment_keys: tuple[str, ...]
    latent_dim: int
    coefficients: tuple[float, ...]
    sample_ids: tuple[str, ...]
    batch_ids: tuple[str, ...]
    ridge: float

    def __post_init__(self):
        if (any(type(v) is not tuple for v in (self.assignment_keys, self.coefficients, self.sample_ids, self.batch_ids))
                or type(self.latent_dim) is not int or self.latent_dim < 0
                or not self.assignment_keys or len(set(self.assignment_keys)) != len(self.assignment_keys)
                or tuple(sorted(self.assignment_keys)) != self.assignment_keys
                or len(self.coefficients) != 1 + 2 * self.latent_dim + len(self.assignment_keys)
                or any(not _number(v) for v in self.coefficients)
                or not _number(self.ridge) or self.ridge <= 0):
            raise ValueError('invalid frozen control-variate definition')
        for key in self.assignment_keys:
            if _key(json.loads(key)) != key:
                raise ValueError('noncanonical assignment key')
        _ids(self.sample_ids, len(self.sample_ids), 'prior sample IDs')
        _ids(self.batch_ids, len(self.sample_ids), 'prior batch IDs', unique=False)
        if not self.sample_ids:
            raise ValueError('control variate requires prior training observations')

    @classmethod
    def fit(cls, prior_draws, prior_losses, *, sample_ids, batch_ids,
            assignments, latent_dim, ridge=1e-6):
        """Fit ONLY completed previous batches, never the batch being estimated.

        IDs enforce disjointness at use; causal prior-only provenance remains a
        caller obligation and must be verified by the durable campaign journal.
        """
        if (type(latent_dim) is not int or latent_dim < 0
                or not _number(ridge) or ridge <= 0):
            raise ValueError('nonnegative latent dimension and positive finite ridge required')
        keys = tuple(sorted(_key(a) for a in assignments))
        if not keys or len(set(keys)) != len(keys):
            raise ValueError('complete unique discrete support required')
        rows = _rows(prior_draws, prior_losses, keys, latent_dim)
        ids = _ids(sample_ids, len(rows), 'prior sample IDs')
        batches = _ids(batch_ids, len(rows), 'prior batch IDs', unique=False)
        features = torch.tensor([[1., *z, *(v*v for v in z),
            *(float(key == a) for a in keys)] for key, z in rows], dtype=torch.float64)
        targets = torch.tensor(prior_losses, dtype=torch.float64)
        # Ridge remains well-defined with one observation or missing categories.
        size = features.shape[1]
        augmented = torch.cat((features, math.sqrt(ridge) * torch.eye(size, dtype=torch.float64)))
        rhs = torch.cat((targets, torch.zeros(size, dtype=torch.float64)))
        if not torch.isfinite(augmented).all():
            raise ValueError('nonfinite prior control-variate features')
        coefficients = torch.linalg.lstsq(augmented, rhs, driver='gelsd').solution
        if not torch.isfinite(coefficients).all():
            raise ValueError('nonfinite prior control-variate fit')
        return cls(keys, latent_dim, tuple(coefficients.tolist()), ids, batches, float(ridge))

    def to_dict(self):
        return {'schema': SCHEMA + '.frozen-control', 'assignment_keys': list(self.assignment_keys),
            'latent_dim': self.latent_dim, 'coefficients': list(self.coefficients),
            'sample_ids': list(self.sample_ids), 'batch_ids': list(self.batch_ids), 'ridge': self.ridge}

    @classmethod
    def from_dict(cls, record):
        expected = {'schema', 'assignment_keys', 'latent_dim', 'coefficients', 'sample_ids', 'batch_ids', 'ridge'}
        if not isinstance(record, dict) or set(record) != expected or record['schema'] != SCHEMA + '.frozen-control':
            raise ValueError('invalid frozen control-variate record')
        return cls(tuple(record['assignment_keys']), record['latent_dim'], tuple(record['coefficients']),
            tuple(record['sample_ids']), tuple(record['batch_ids']), record['ridge'])

    def values(self, rows):
        d, c = self.latent_dim, self.coefficients
        return torch.tensor([c[0] + sum(c[1+i]*v + c[1+d+i]*v*v for i, v in enumerate(z))
            + c[1+2*d+self.assignment_keys.index(key)] for key, z in rows], dtype=torch.float64)

    def expectation(self, mean, sigma, joint_probabilities):
        d = self.latent_dim
        c = torch.tensor(self.coefficients, dtype=torch.float64)
        return (c[0] + (c[1:1+d] * mean).sum()
            + (c[1+d:1+2*d] * (mean.square() + sigma.square())).sum()
            + (c[1+2*d:] * joint_probabilities).sum())


def estimate_expected_loss_gradient(draws, losses, *, logits, mean, sigma,
        discrete_log_probability=None, assignments=None, control_variate=None,
        sample_ids, batch_id):
    """Estimate d E[L(A,Z)] / d (factor logits, Gaussian means).

    ``draws`` retain existing assignment-dict/latent-list shape. ``logits`` and
    ``mean`` are the existing float64 CPU gradient-enabled policy tensors;
    ``sigma`` is fixed positive Gaussian scale. The discrete callback must give
    exact log probabilities on the COMPLETE declared conditional support and
    share those same logits. No selected-subset normalization is accepted.

    Returns null gradients on any invalid batch/numeric failure, never removes
    failures or assigns numeric penalties. Single-draw LR/control estimates are
    legal; the independent leave-one-out comparator is then unavailable.
    """
    report = {'schema': SCHEMA, 'status': 'invalid', 'gradient': None,
        'plain_gradient': None, 'loo_gradient': None,
        'pathwise_native_or_llm_or_source_derivative': False,
        'estimand': 'conditional current-vocabulary expected opaque native loss; fixed sigma and logistic pushforward',
        'unbiasedness_conditions': 'IID current draws; exact scores and support; finite expectations; prior-only frozen control independent of current draws; no direct loss dependence on policy parameters',
        'failures_filtered': False}
    try:
        if (not isinstance(logits, dict) or not isinstance(batch_id, str) or not batch_id
                or not isinstance(mean, torch.Tensor) or not isinstance(sigma, torch.Tensor)
                or mean.ndim != 1 or sigma.shape != mean.shape
                or mean.dtype != torch.float64 or sigma.dtype != torch.float64
                or mean.device.type != 'cpu' or sigma.device.type != 'cpu'
                or not torch.isfinite(mean).all() or not torch.isfinite(sigma).all()
                or not (sigma > 0).all() or sigma.requires_grad):
            raise ValueError('finite float64 CPU mean and fixed positive sigma vectors required')
        for key, tensor in logits.items():
            if (not isinstance(key, str) or not key or not isinstance(tensor, torch.Tensor)
                    or tensor.ndim != 1 or tensor.numel() == 0 or tensor.dtype != torch.float64
                    or tensor.device.type != 'cpu' or not tensor.requires_grad
                    or not torch.isfinite(tensor).all()):
                raise ValueError('finite float64 CPU gradient-enabled factor logits required')
        if mean.numel() and not mean.requires_grad:
            raise ValueError('continuous mean must require gradients')
        support = assignments if assignments is not None else [{}]
        keys = tuple(sorted(_key(a) for a in support))
        if not keys or len(set(keys)) != len(keys):
            raise ValueError('complete unique conditional discrete support required')
        support = [json.loads(k) for k in keys]
        if bool(logits) != (discrete_log_probability is not None):
            raise ValueError('exact discrete likelihood callback required iff factor logits exist')
        if not logits and keys != ('{}',):
            raise ValueError('no discrete assignments without factor logits')
        rows = _rows(draws, losses, keys, mean.numel())
        ids = _ids(sample_ids, len(rows), 'current sample IDs')
        if control_variate is not None:
            if not isinstance(control_variate, FrozenDesignControlVariate):
                raise ValueError('frozen prior-only control variate required')
            if (control_variate.assignment_keys != keys or control_variate.latent_dim != mean.numel()
                    or set(ids) & set(control_variate.sample_ids) or batch_id in control_variate.batch_ids):
                raise ValueError('control prior overlaps current batch or differs from current support/dimension')
        parameters = list(logits.values()) + ([mean] if mean.numel() else [])

        def gradient(value, *, require_all=False):
            if not parameters:
                return torch.zeros(0, dtype=torch.float64)
            if not value.requires_grad:
                raise ValueError('exact likelihood/correction must be connected to policy tensors')
            pieces = torch.autograd.grad(value, parameters, retain_graph=True, allow_unused=True)
            if require_all and any(g is None for g in pieces):
                raise ValueError('likelihood detached from one or more declared policy parameters')
            return torch.cat([(torch.zeros_like(p) if g is None else g).reshape(-1)
                for p, g in zip(parameters, pieces)])

        discrete = (discrete_log_probability([draw['assignment'] for draw in draws]) if logits
                    else torch.zeros(len(rows), dtype=torch.float64))
        log_support = (discrete_log_probability(support) if logits
                       else torch.zeros(1, dtype=torch.float64))
        if (not isinstance(discrete, torch.Tensor) or not isinstance(log_support, torch.Tensor)
                or discrete.dtype != torch.float64 or log_support.dtype != torch.float64
                or discrete.shape != (len(rows),) or log_support.shape != (len(keys),)
                or not torch.isfinite(discrete).all() or not torch.isfinite(log_support).all()):
            raise ValueError('nonfinite or malformed exact conditional likelihood')
        probabilities = log_support.exp()
        if not torch.isclose(probabilities.sum(), torch.tensor(1., dtype=torch.float64), atol=1e-10, rtol=1e-10):
            raise ValueError('complete conditional support must have total probability one')
        expected_discrete = torch.stack([log_support[keys.index(key)] for key, _ in rows])
        if not torch.allclose(discrete, expected_discrete, atol=1e-12, rtol=1e-12):
            raise ValueError('sample and full-support likelihood disagree')
        z = torch.tensor([v for _, v in rows], dtype=torch.float64).reshape(len(rows), mean.numel())
        logq = discrete + (torch.distributions.Normal(mean, sigma).log_prob(z).sum(-1)
            if mean.numel() else 0.)
        scores = torch.stack([gradient(v, require_all=True) for v in logq])
        costs = torch.tensor(losses, dtype=torch.float64)
        plain_terms = costs[:, None] * scores
        baseline = ((costs.sum()-costs)/(len(rows)-1)) if len(rows) > 1 else None
        loo_terms = (costs-baseline)[:, None]*scores if baseline is not None else None
        correction = torch.zeros(scores.shape[1], dtype=torch.float64)
        predictions = torch.zeros(len(rows), dtype=torch.float64)
        if control_variate is not None:
            predictions = control_variate.values(rows)
            correction = gradient(control_variate.expectation(mean, sigma, probabilities))
        terms = (costs-predictions)[:, None]*scores + correction[None, :]
        standard_error = terms.std(0, correction=1)/math.sqrt(len(rows)) if len(rows) > 1 else None
        checked = [logq, scores, plain_terms, predictions, correction, terms, costs.mean()]
        if loo_terms is not None:
            checked.extend((loo_terms, standard_error))
        if any(not torch.isfinite(v).all() for v in checked):
            raise ValueError('nonfinite estimator arithmetic; no update permitted')

        def unpack(vector):
            result, offset = {'logits': {}, 'continuous_mean': []}, 0
            for key, parameter in logits.items():
                result['logits'][key] = vector[offset:offset+parameter.numel()].tolist()
                offset += parameter.numel()
            result['continuous_mean'] = vector[offset:].tolist()
            return result

        report.update(status='valid', estimator='frozen-prior-control-variate-lr' if control_variate else 'plain-likelihood-ratio',
            gradient=unpack(terms.mean(0)), plain_gradient=unpack(plain_terms.mean(0)),
            loo_gradient=unpack(loo_terms.mean(0)) if loo_terms is not None else None,
            correction_gradient=unpack(correction), sample_gradients=[unpack(v) for v in terms],
            score_vectors=[unpack(v) for v in scores], control_predictions=predictions.tolist(),
            all_equal_costs=len(set(losses)) == 1, all_zero_costs=all(v == 0 for v in losses),
            sample_ids=list(ids), batch_id=batch_id,
            prior_sample_ids=list(control_variate.sample_ids) if control_variate else [],
            prior_batch_ids=list(control_variate.batch_ids) if control_variate else [],
            mean_loss=costs.mean().item(),
            estimated_gradient_standard_error=unpack(standard_error) if standard_error is not None else None,
            standard_error_note='within-batch Monte Carlo diagnostic, not a confidence claim or variance-reduction guarantee')
    except (ValueError, TypeError, KeyError, RuntimeError, OverflowError, AttributeError) as error:
        report.update(status='invalid', gradient=None, reason=f'{type(error).__name__}: {error}')
    return report
