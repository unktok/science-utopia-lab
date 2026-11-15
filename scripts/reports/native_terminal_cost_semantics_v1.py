"""Accounting interpretation of the declared C loss, not a new optimization.

Pure arithmetic has no model, world or generated-program execution. Observed
losses remain literal; requested-cost scores below are report-only diagnostics.
"""
from copy import deepcopy
import math

SCHEMA = 'scienceutopia.native-terminal-cost-semantics.v1'


def number(value):
    return type(value) in (int, float) and math.isfinite(value)


def describe(worlds, *, coefficient):
    if not number(coefficient) or coefficient < 0:
        raise ValueError('explicit finite nonnegative original resource coefficient required')
    if not isinstance(worlds, list) or len(worlds) != 2 or any(not isinstance(w, dict) for w in worlds):
        raise ValueError('two ordered measured-world records required')
    missing = []
    fields = ('resource_cost', 'uncollected_activity_cost', 'requested_activity_cost')
    for i, world in enumerate(worlds):
        scores = world.get('scores')
        if scores is None:
            scores = {}
        if not isinstance(scores, dict):
            raise ValueError('literal score mapping or unknown measurement required')
        missing += [f'world[{i}].{key}' for key in fields if world.get(key) is None]
        missing += [f'world[{i}].scores.{key}' for key in ('content-utility', 'resource-aware-content')
                    if scores.get(key) is None]
    scope = ('The declared optimized C uses collected native activity cost. The requested-cost '
        'score is an accounting diagnostic, not a replacement loss, new search, adoption veto, '
        'real expenditure, scientific truth or welfare. No observed selection or loss is overwritten. '
        'The identity describes these recorded worlds, not a causal effect, global optimum or '
        'performance beyond the measured horizon.')
    if missing:
        return {'schema': SCHEMA, 'status': 'unavailable', 'missing': missing,
            'unknown_cost_or_loss_imputed': False, 'scope': scope, 'new_model_calls': 0,
            'new_native_worlds': 0, 'loss_or_selection_changed': False, 'publication_ready': False}
    rows = []
    for world in worlds:
        values = [world[key] for key in fields]
        u, c = [world['scores'][key] for key in ('content-utility', 'resource-aware-content')]
        if any(not number(v) for v in [*values, u, c]) or min(values) < 0:
            raise ValueError('literal finite losses and nonnegative measured native costs required')
        collected, unpaid, requested = values
        if not math.isclose(requested, collected + unpaid, rel_tol=0, abs_tol=1e-9):
            raise ValueError('original requested expense must reconcile with collected and unpaid costs')
        if not math.isclose(c, u + coefficient * collected, rel_tol=0, abs_tol=1e-9):
            raise ValueError('recorded C must use the original declared coefficient and collected K')
        requested_score = math.fsum((u, coefficient * requested))
        rows.append({'condition': world.get('condition'), 'reported_content_loss': u,
            'reported_C_loss': c, 'collected_activity_cost': collected,
            'uncollected_activity_cost': unpaid, 'requested_activity_cost': requested,
            'requested_cost_score_diagnostic_not_optimized': requested_score,
            'weighted_unpaid_cost': coefficient * unpaid})
    delta = lambda key: rows[1][key] - rows[0][key]
    contrast = {key: delta(key) for key in ('reported_content_loss', 'reported_C_loss',
        'collected_activity_cost', 'uncollected_activity_cost', 'requested_activity_cost',
        'requested_cost_score_diagnostic_not_optimized', 'weighted_unpaid_cost')}
    # Delta C_req = delta C_col + lambda delta unpaid. This does not add a veto
    # to the declared C optimization or relabel the measured outcome.
    residual = contrast['requested_cost_score_diagnostic_not_optimized'] - (
        contrast['reported_C_loss'] + contrast['weighted_unpaid_cost'])
    if not math.isclose(residual, 0, rel_tol=0, abs_tol=1e-9):
        raise ValueError('reported C contrast fails the original accounting identity')
    return {'schema': SCHEMA, 'status': 'measured-diagnostic', 'resource_coefficient': coefficient,
        'worlds': deepcopy(rows), 'contrast_control_minus_reference': contrast,
        'accounting_identity': 'delta C_requested = delta C_collected + coefficient * delta unpaid',
        'floating_identity_residual': residual, 'scope': scope,
        'new_model_calls': 0, 'new_native_worlds': 0, 'loss_or_selection_changed': False,
        'publication_ready': False}
