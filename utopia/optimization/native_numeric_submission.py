"""Literal coordinate submission, separate from the general code editor.

No clamp, projection, source repair, implicit retention or scientific veto.
The caller still applies the original campaign domain and native evaluator.
"""
from __future__ import annotations

import math

from utopia.optimization.native_design_space import _get, _set, validate_design_space, require_candidate_in_space
from utopia.optimization.native_objective_view import loss_arithmetic
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest, make_patch

SCHEMA = 'scienceutopia.native-numeric-submission.v1'


def numeric_context(request):
    contract = request.get('design_space')
    if not isinstance(contract, dict) or contract.get('kind') != 'parameters':
        raise ValueError('explicit parameter-only domain required')
    anchor = SystemSpec.from_dict(request['design_space_anchor'])
    validate_design_space(anchor, contract)
    parent = SystemSpec.from_dict(request['parent_system'])
    require_candidate_in_space(anchor, parent, contract)
    data = parent.to_dict()
    index = {n.mechanism_id: i for i, n in enumerate(parent.mechanisms)}
    coordinates = [{**clone(c), 'id': 'coordinate-'+str(i),
        'current_value': _get(data, '/mechanisms/'+str(index[c['mechanism_id']])+c['path'])}
        for i, c in enumerate(contract['numeric_coordinates'])]
    # Only existing own observations are exposed, never other methods' results.
    observations = []
    for saved in request.get('observations', []):
        observation = saved.get('observation') or {}
        suggestion = saved.get('suggestion') or {}
        prior = suggestion.get('candidate')
        values = None
        if isinstance(prior, dict):
            prior_index = {n['mechanism_id']:i for i,n in enumerate(prior['mechanisms'])}
            values = {c['id']:_get(prior, '/mechanisms/'+str(prior_index[c['mechanism_id']])+c['path'])
                      for c in coordinates}
        observations.append({'observation_id':observation.get('observation_id'),
            'status':observation.get('status'), 'loss':observation.get('loss'), 'coordinate_values':values,
            'measurements':clone((observation.get('metadata') or {}).get('measurements')),
            'technical_failures':clone((observation.get('metadata') or {}).get('technical_failures'))})
    consumer_ids = {c['mechanism_id'] for c in coordinates}
    return {'schema': SCHEMA+'.context', 'request_sha256': digest(request),
        'generation': request['generation'], 'loss_arithmetic': loss_arithmetic(request['loss_spec']),
        'coordinates': coordinates, 'own_observations': observations,
        'fixed_implementations': [clone(n) for n in data['mechanisms'] if n['mechanism_id'] in consumer_ids],
        'feedback_policy': clone(request.get('feedback_policy')),
        'retention': 'Explicitly returning every current value retains the parent; never an automatic fallback.',
        'output_contract': {'values': 'Object with exactly the coordinate IDs and literal numeric values.',
                            'rationale': 'Nonempty uninterpreted author note; not executable code.'}}


def submission_schema(context):
    return {'type': 'object', 'additionalProperties': False, 'required': ['values', 'rationale'],
        'properties': {'rationale': {'type': 'string', 'minLength': 1, 'maxLength': 8000},
            'values': {'type': 'object', 'additionalProperties': False,
                'required': [c['id'] for c in context['coordinates']],
                'properties': {c['id']: {'type': 'integer' if c['integer'] else 'number',
                    'minimum': c['lower'], 'maximum': c['upper']} for c in context['coordinates']}}}}


def compile_submission(request, submission):
    context = numeric_context(request)
    if (not isinstance(submission, dict) or set(submission) != {'values', 'rationale'}
            or not isinstance(submission['rationale'], str) or not submission['rationale'].strip()
            or len(submission['rationale']) > 8000 or not isinstance(submission['values'], dict)
            or set(submission['values']) != {c['id'] for c in context['coordinates']}):
        raise ValueError('exact literal numeric submission and author rationale required')
    parent = SystemSpec.from_dict(request['parent_system']); data = parent.to_dict()
    index = {n.mechanism_id: i for i, n in enumerate(parent.mechanisms)}
    operations = []
    for c in context['coordinates']:
        value = submission['values'][c['id']]
        if (type(value) not in (int, float) or not math.isfinite(value)
                or c['integer'] and type(value) is not int
                or not c['lower'] <= value <= c['upper']):
            raise ValueError('literal coordinate outside declared finite numeric domain: '+c['id'])
        path = '/mechanisms/'+str(index[c['mechanism_id']])+c['path']
        if value != c['current_value']:
            operations.append({'op': 'replace', 'path': path, 'value': clone(value)})
            _set(data, path, value)
    candidate = SystemSpec.from_dict(data)
    anchor = SystemSpec.from_dict(request['design_space_anchor'])
    require_candidate_in_space(anchor, candidate, request['design_space'])
    return {'base_patch': make_patch(parent, operations) if operations else None,
        'factors': [], 'continuous': [],
        'provenance': {'author': 'literal-local-numeric-submission', 'submission_sha256': digest(submission),
            'rationale': submission['rationale'], 'retained_parent_explicitly': not operations,
            'raw_values_changed_by_host': False, 'schema': SCHEMA}}
