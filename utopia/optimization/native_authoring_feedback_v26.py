"""Own-trial facts, not a policy, merit gate or model-claim endorsement."""
from utopia.system.design_patch import clone, digest


def reference_duplicate_failures(feedback, history):
    """Editor-only exact references; all original failure fields stay visible once.

    First planners do not receive own_history, so their feedback is never
    passed through this projection. Unknown/unmatched fields keep the full body.
    """
    result = clone(feedback)
    records = history.get('generation_authoring_failures') or []
    for trial in result.get('all_own_trials', []):
        failure = trial.get('generation_failure')
        if not isinstance(failure, dict) or not failure:
            continue
        matches = [(index, item) for index, item in enumerate(records)
            if item.get('history_index') == trial.get('history_index')]
        if len(matches) != 1:
            continue
        index, record = matches[0]
        mapping = {key: ('failure_schema' if key == 'schema' else key) for key in failure}
        if (record.get('exact_generation_failure_sha256') != digest(failure)
                or any(target not in record or digest(record[target]) != digest(failure[key])
                    for key, target in mapping.items())):
            continue
        trial['generation_failure'] = {
            'exact_literal_reference': '/own_history/generation_authoring_failures/' + str(index),
            'referenced_field_map': mapping, 'original_failure_sha256': digest(failure),
            'scope': 'Every original failure field is present exactly at the reference, using the '
                'explicit field map. No failure, cause, step receipt or missing value is discarded.'}
    return result


def own_trial_feedback(request):
    """Project every own archived trial without reading another arm or source file.

    Literal submission facts are separate from untrusted design intent and
    native observations. Missing older provenance stays unknown, never zero.
    No candidate is generated, repaired or rejected by this projection.
    """
    trials = []
    if not request.get('history'):
        return {'schema': 'scienceutopia.own-authoring-feedback.v26', 'all_own_trials': []}
    parent_sha = digest(request['parent_system'])
    for index, record in enumerate(request.get('history', [])):
        definition = record.get('definition')
        definition = definition if isinstance(definition, dict) else {}
        provenance = definition.get('provenance') or {}
        staged = provenance.get('staged_author') or {}
        raw_ir = (provenance.get('authoring_compiler') or {}).get('raw_ir')
        operations = raw_ir.get('operations') if isinstance(raw_ir, dict) else None
        factors, continuous = definition.get('factors'), definition.get('continuous')
        valid_shape = ('base_patch' in definition and isinstance(operations, list)
            and isinstance(factors, list) and isinstance(continuous, list))
        no_intervention = (definition['base_patch'] is None and not operations
            and not factors and not continuous) if valid_shape else None
        observations = []
        draws = record.get('draws') or []
        for observation_index, observation in enumerate(record.get('observations') or []):
            draw = draws[observation_index] if observation_index < len(draws) else None
            suggestion = draw.get('suggestion') if isinstance(draw, dict) else None
            candidate = suggestion.get('candidate') if isinstance(suggestion, dict) else None
            candidate_sha = digest(candidate) if isinstance(candidate, dict) else None
            view = clone(observation)
            omitted = None
            if isinstance(view, dict) and 'candidate' in view:
                body = view.pop('candidate')
                omitted = {'field': 'candidate', 'body_sha256': digest(body),
                    'scope': 'Only the full prior candidate body is not repeated. The exact original '
                        'observation is archived; current literal draft bodies are supplied to the editor.'}
            item = {'observation_index': observation_index,
                'observation': view, 'candidate_sha256': candidate_sha,
                'is_current_parent': candidate_sha == parent_sha if candidate_sha else None}
            if omitted is not None:
                item.update(original_observation_sha256=digest(observation),
                    explicit_body_omission=omitted)
                if isinstance(body, dict):
                    item['archived_candidate_file'] = (
                        f'history/trial-{index:03d}/observation-{observation_index:03d}/system.json')
            observations.append(item)
        trials.append({'history_index': index,
            'request_sha256': record.get('request_sha256'), 'version_sha256': record.get('version_sha256'),
            'untrusted_model_authored_plan': clone(staged.get('untrusted_model_authored_plan')),
            'literal_submission': {
                'base_patch_is_null': definition['base_patch'] is None if 'base_patch' in definition else None,
                'authored_operation_count': len(operations) if isinstance(operations, list) else None,
                'factor_count': len(factors) if isinstance(factors, list) else None,
                'continuous_count': len(continuous) if isinstance(continuous, list) else None,
                'no_literal_intervention': no_intervention,
                'observed_session': clone(staged.get('observed_session'))},
            'generation_error': clone(record.get('generation_error')),
            'generation_failure': clone(definition.get('generation_failure')),
            'observations': observations, 'update_report': clone(record.get('report'))})
    return {'schema': 'scienceutopia.own-authoring-feedback.v26',
        'scope': 'Own archived plans, literal submission facts and native observations; '
            'a plan/finish claim is not evidence of implemented behavior or improvement.',
        'all_own_trials': trials, 'based_on_observation_id': request.get('based_on_observation_id'),
        'current_parent_sha256': parent_sha, 'foreign_arm_lookup': False,
        'silent_tail_truncation': False, 'missing_values_imputed': False}
