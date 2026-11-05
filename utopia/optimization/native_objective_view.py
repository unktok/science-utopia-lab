"""Loss arithmetic for the institution author, never a candidate policy or veto.

This view is derived only from the supplied LossSpec, current draft and own
observations. It does not predict institutional effects, take a world/LLM
derivative, execute a system or turn a failed observation into a valid one.
"""
from .loss import evaluate_loss, loss_spec_sha256, validate_loss_spec
from utopia.system.design_patch import clone, digest

SCHEMA = 'scienceutopia.native-objective-view.v21'


def objective_view(request, state):
    spec = request['loss_spec']
    validate_loss_spec(spec)
    spec_hash = loss_spec_sha256(spec)
    terms = [{**clone(term),
        'per_run_loss_change_for_one_unit_increase_other_inputs_fixed': term['coefficient'],
        'metric_change_that_lowers_per_run_loss_other_inputs_fixed': (
            'increase' if term['coefficient'] < 0 else 'decrease' if term['coefficient'] > 0 else 'none')}
        for term in spec['per_run']['terms']]
    observations = []
    for item in request.get('observations', []):
        observation = item.get('observation') or {}
        metadata = observation.get('metadata') or {}
        binding = metadata.get('loss_spec_sha256')
        measurements = metadata.get('measurements')
        if binding != spec_hash:
            recomputed = {'status': 'loss-binding-unavailable' if binding is None else 'loss-binding-mismatch',
                'loss': None}
        elif not isinstance(measurements, list) or not all(isinstance(row, dict) for row in measurements):
            recomputed = {'status': 'measurement-objects-unavailable', 'loss': None}
        else:
            recomputed = evaluate_loss(spec, measurements)
        recorded_loss = observation.get('loss')
        observations.append({'observation_id': observation.get('observation_id'),
            'recorded_status': observation.get('status'), 'recorded_loss': recorded_loss,
            'technical_failures': clone(metadata.get('technical_failures', [])),
            'recomputed_from_recorded_measurements': recomputed,
            'recomputed_matches_recorded_loss': (recorded_loss == recomputed['loss']
                if recorded_loss is not None and recomputed['loss'] is not None else None)})
    return {'schema': SCHEMA, 'loss_spec_sha256': spec_hash,
        'direction': 'minimize', 'per_run_intercept': spec['per_run']['intercept'],
        'terms': terms, 'across_seeds': clone(spec['across_seeds']),
        'draft_document_changed_from_generation_parent': digest(state['document']) != digest(request['parent_system']),
        'sampling_distribution_declared': bool(state['factors'] or state['continuous']),
        'own_observation_breakdowns': observations,
        'scope': 'Exact affine per-run bookkeeping, not a world gradient or predicted effect of any edit. '
            'Directions hold other measured inputs fixed; aggregate dispersion and coupled institutional '
            'effects can change the result. Recorded failures and null losses remain unchanged. '
            'A literal document difference is not proof of behavioral change or improvement.',
        'candidate_policy_supplied': False, 'extra_eligibility_constraint': False,
        'new_measurements': 0, 'source_executions': 0}
