"""Allowlisted proposal data for a technical-only native search control.

This is a prospective information boundary, not a rewrite of observations.
Full measurements, losses, errors and update reports remain in campaign state.
Conditioning on the same authored proposals and technical outcomes, changing
measured values, response IDs or loss-derived hashes cannot change this view.
Technical success/failure itself is intentionally visible; this is not a
claim of zero information about the world or a sandbox for trusted callbacks.
"""
from utopia.system.design_patch import clone, digest


def _error(value):
    # Exception messages/tracebacks can contain measured values or raw outputs.
    # Preserve them internally, not in this prospective proposal-side view.
    return None if value is None else {'type': value.get('type', value.get('error_type')),
        'message_withheld': True, 'loss_withheld': True}


def class_only_records(records):
    """Match native/compiler error detail in the loss-visible comparison arm.

    Losses, measurements and optimizer reports stay visible in this arm; the
    technical exception-class channel is identical to the technical-only arm.
    Caller-authored definitions/code remain literal in both policies.
    """
    result = clone(records)
    for record in result:
        record['generation_error'] = _error(record['generation_error'])
        for draw in record['draws']:
            draw['technical_error'] = _error(draw.get('technical_error'))
        for observation in record['observations']:
            if observation is not None:
                metadata = observation.setdefault('metadata', {})
                metadata['technical_failures'] = [_error(e) for e in metadata.get('technical_failures', [])]
    return result


def technical_history(records):
    history, observations = [], []
    for generation, record in enumerate(records):
        draws, outcomes = [], []
        for index, draw in enumerate(record['draws']):
            suggestion = draw.get('suggestion')
            identity = f'technical-only-{generation}-{index}'
            projected = None if suggestion is None else {
                'suggestion_id': identity, 'candidate': clone(suggestion['candidate']),
                'proposal_index': sum(len(r['draws']) for r in history) + index,
                'proposer': 'technical-only-history', 'based_on_observation_id': None}
            draws.append({'suggestion': projected,
                'technical_error': _error(draw.get('technical_error'))})
            raw = record['observations'][index] if index < len(record['observations']) else None
            outcome = None if raw is None else {
                'observation_id': identity, 'status': raw['status'],
                'suggestion_id': identity, 'candidate': clone(projected['candidate']),
                'loss_withheld': True,
                'metadata': {'measurements_withheld': True,
                    'technical_failures': [_error(e) for e in raw.get('metadata', {}).get('technical_failures', [])]}}
            outcomes.append(outcome)
            if projected is not None and outcome is not None:
                observations.append({'suggestion': clone(projected), 'observation': clone(outcome)})
        item = {'definition': clone(record['definition']),
            'generation_error': _error(record['generation_error']),
            'draws': draws, 'observations': outcomes, 'report': None}
        # Raw request/version/observation hashes can encode hidden measurements.
        # These are explicitly new view identities, never raw evidence IDs.
        identity = digest(item)
        history.append({**item, 'request_sha256': identity,
            'version_sha256': digest({'technical_view': identity, 'definition': item['definition']}),
            'identities_are_projected_not_raw_evidence': True})
    return history, observations


def technical_request(campaign, records, strategy_state, count, *, chosen,
                      probabilities, rng_seed):
    history, observations = technical_history(records)
    ids = sorted(campaign.binding['strategies'])
    return {'schema': 'scienceutopia.native-generated-vocabulary.v7',
        'generation': len(records), 'count': count,
        'parent_system': campaign.initial.to_dict(), 'based_on_observation_id': None,
        'history': history, 'observations': observations, 'loss_spec': clone(campaign.loss),
        'world_binding': clone(campaign.binding['world']), 'strategy_id': ids[chosen],
        'strategy_provenance': clone(campaign.binding['strategies'][ids[chosen]]),
        'strategy_state': clone(strategy_state), 'strategy_probabilities': probabilities.tolist(),
        'strategy_log_probability': float(probabilities[chosen].log()), 'rng_seed': rng_seed,
        'binding_sha256': digest(campaign.binding), 'history_sha256': digest(history),
        'feedback_policy': {'name': 'technical-only', 'objective_definition_visible': True,
            'parent': 'fixed-initial-system', 'proposal_order': 'chronological',
            'strategy_updates': False, 'measured_values_visible': False,
            'technical_outcomes_visible': True, 'native_error_messages_visible': False,
            'raw_evidence_available_to_proposer': False,
            'final_loss_only_selection_unchanged': True}}
