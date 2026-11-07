"""Loss arithmetic for the institution author, never a candidate policy or veto.

This view is derived only from the supplied LossSpec, current draft and own
observations. It does not predict institutional effects, take a world/LLM
derivative, execute a system or turn a failed observation into a valid one.
"""
from .loss import evaluate_loss, loss_spec_sha256, validate_loss_spec
from utopia.system.design_patch import clone, digest

SCHEMA = 'scienceutopia.native-objective-view.v21'

# Measurement definitions, not candidate institutions or extra objectives.
# These describe remeasure_native_endpoint's existing checkpoint arithmetic.
NATIVE_MEASUREMENT_DEFINITIONS = {
    'native.accepted_decisions': 'Count review-history decisions whose decision is accept.',
    'native.rejected_decisions': 'Count review-history decisions whose decision is reject.',
    'native.review_records': 'Count individual review records across all review-history decisions, not papers.',
    'native.accepted_peer_score_sum': 'For each accepted review-history decision, take the arithmetic mean '
        'of its original native reviewer overall_score values, then sum those means. An accepted decision '
        'with no reviews contributes zero. Missing or nonfinite original scores make this metric unavailable. '
        'Institution-written final_score is not an input to this measurement.',
    'native.accepted_unreviewed_decisions': 'Count accepted review-history decisions with no review records.',
    'native.final_active_authors': 'Count final author-capable agents whose is_active value is true.',
    'native.final_author_resources': 'Sum final resources of all author-capable agents.',
    'native.institutional_context_deliveries': 'Count native.system.context_delivered kernel events.',
}


def _terms(spec):
    return [{key: clone(term[key]) for key in ('metric_id', 'slice_id', 'coefficient') if key in term}
        for term in spec['per_run']['terms']]


def _across(spec):
    return {key: clone(spec['across_seeds'][key]) for key in
        ('aggregation', 'dispersion_weight', 'minimum_valid_runs')}


def _direction_terms(spec):
    """Algebra only: not a prediction of a coupled institution's effect."""
    return [{**term,
        'per_run_loss_change_for_one_unit_increase_other_inputs_fixed': term['coefficient'],
        'metric_change_that_lowers_per_run_loss_other_inputs_fixed': (
            'increase' if term['coefficient'] < 0 else 'decrease' if term['coefficient'] > 0 else 'none')}
        for term in _terms(spec)]


def loss_arithmetic(spec):
    """Exact computational projection; full LossSpec stays archived and evaluated.

    Registry commentary must not accidentally become a second optimization
    target. Whitelist the fields actually read by evaluate_loss; never rewrite
    a coefficient, hide a failure, invent a metric definition or supply a policy.
    """
    validate_loss_spec(spec)
    terms = _terms(spec)
    identities = sorted({term['metric_id'] for term in terms})
    return {'schema': 'scienceutopia.loss-arithmetic-view.v23',
        'archived_loss_spec_sha256': loss_spec_sha256(spec), 'direction': spec['direction'],
        'per_run': {'intercept': spec['per_run']['intercept'], 'terms': terms},
        'across_seeds': _across(spec),
        'quantity_to_minimize': 'the whole aggregate loss, not each input metric separately',
        'per_run_affine_directions': _direction_terms(spec),
        'direction_scope': 'Exact affine per-run arithmetic with other inputs fixed. Negative '
            'coefficients mean increasing that metric lowers per-run loss; positive coefficients '
            'mean decreasing it lowers per-run loss. Aggregate dispersion and coupled world '
            'changes must still be evaluated; this is not a predicted policy effect.',
        'measurement_definitions': {identity: NATIVE_MEASUREMENT_DEFINITIONS[identity]
            for identity in identities if identity in NATIVE_MEASUREMENT_DEFINITIONS},
        'metrics_without_text_definition': [identity for identity in identities
            if identity not in NATIVE_MEASUREMENT_DEFINITIONS],
        'registry_prose': 'Noncomputational registry annotations are retained in the archived LossSpec, '
            'not supplied as additional requirements in this author task.',
        'candidate_policy_supplied': False, 'extra_eligibility_constraint': False}


def wire_objective_view(view):
    """Omit registry labels in recomputed metadata, never numeric own feedback."""
    result = clone(view)
    for observation in result['own_observation_breakdowns']:
        recomputed = observation['recomputed_from_recorded_measurements']
        if isinstance(recomputed.get('loss_spec'), dict):
            recomputed['loss_spec'] = {'sha256': recomputed['loss_spec']['sha256']}
    return result


def objective_view(request, state):
    spec = request['loss_spec']
    validate_loss_spec(spec)
    spec_hash = loss_spec_sha256(spec)
    terms = _direction_terms(spec)
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
        'terms': terms, 'across_seeds': _across(spec),
        'draft_document_changed_from_generation_parent': digest(state['document']) != digest(request['parent_system']),
        'sampling_distribution_declared': bool(state['factors'] or state['continuous']),
        'own_observation_breakdowns': observations,
        'scope': 'Exact affine per-run bookkeeping, not a world gradient or predicted effect of any edit. '
            'Directions hold other measured inputs fixed; aggregate dispersion and coupled institutional '
            'effects can change the result. Recorded failures and null losses remain unchanged. '
            'A literal document difference is not proof of behavioral change or improvement.',
        'candidate_policy_supplied': False, 'extra_eligibility_constraint': False,
        'new_measurements': 0, 'source_executions': 0}
