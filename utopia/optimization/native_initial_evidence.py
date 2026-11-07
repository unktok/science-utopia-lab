"""Explicit historical warm starts for the existing native ask/tell campaign.

This is measurement rescoring, not a new optimizer, native execution cache,
source-equivalence proof, held-out test, or newly discovered improvement. Full
candidate JSON and original observations remain immutable data. Duplicate
programs/run identities and technical failures are deliberately not deduplicated.
"""
from __future__ import annotations

from .blackbox import Observation, Suggestion
from .loss import evaluate_loss, loss_spec_sha256, validate_loss_spec
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest

SCHEMA = 'scienceutopia.native-historical-initial-evidence.v1'
VIEW_SCHEMA = 'scienceutopia.native-historical-objective-view.v1'
COMPATIBILITY_FIELDS = ('model', 'model_digest', 'corpus_sha256', 'corpus_years',
                        'dataset_identity', 'image_id', 'years', 'population')
CLAIMS = {'historical_warm_start': True, 'new_native_executions': 0,
          'new_model_calls': 0, 'new_improvement_discovered': False,
          'source_equivalence_established': False, 'held_out_evidence': False,
          'physical_cache_reuse_allowed': False,
          'duplicates_and_all_ties_preserved': True}


def _hash_body(value):
    return digest({k: v for k, v in value.items() if k != 'content_sha256'})


def _check_pair(suggestion, observation, loss_spec, world, seeds):
    """Validate archived logical identity; do not reopen/run historical code."""
    proposed, observed = Suggestion.from_dict(suggestion), Observation.from_dict(observation)
    metadata = observed.metadata
    system = SystemSpec.from_dict(proposed.candidate)
    if (observed.suggestion_id != proposed.suggestion_id
            or observed.candidate != proposed.candidate
            or metadata.get('system_fingerprint') != system.fingerprint
            or metadata.get('world_backend') != 'native-research-world'
            or metadata.get('loss_spec_sha256') != loss_spec_sha256(loss_spec)):
        raise ValueError('historical suggestion/observation/source identity changed')
    measurements, runs = metadata.get('measurements'), metadata.get('runs')
    if not isinstance(measurements, list) or not isinstance(runs, list):
        raise ValueError('historical exact measurements and run receipts required')
    evaluated = evaluate_loss(loss_spec, measurements)
    if metadata.get('loss_evaluation') != evaluated:
        raise ValueError('historical canonical loss evaluation changed')
    if observed.status == 'complete':
        if (metadata.get('technical_failures') or evaluated['status'] != 'complete'
                or observed.loss != evaluated['loss']
                or sorted(r['seed'] for r in runs) != sorted(seeds)
                or {r['run_id'] for r in runs} != {m.get('run_id') for m in measurements}
                or any(r.get('system_fingerprint') != system.fingerprint for r in runs)
                or any(m.get('system_fingerprint') != system.fingerprint for m in measurements)):
            raise ValueError('historical complete native measurement/run binding changed')
    if not world.get('source_commit'):
        raise ValueError('historical source binding required')


def build_initial_evidence(audit, *, expected_audit_content_sha256, expected_source_commit):
    """Extract all slots from one explicitly pinned terminal full audit.

    The caller supplies an independently replayed full audit and its declared
    content identity. This function verifies its content hash; it does not
    authenticate a provider or substitute for that original-source audit.
    """
    if (audit.get('schema') != 'scienceutopia.native-staged-search-audit.v15'
            or audit.get('content_sha256') != expected_audit_content_sha256
            or _hash_body(audit) != expected_audit_content_sha256
            or audit.get('source_commit') != expected_source_commit
            or audit.get('queue_terminal') is not True or audit.get('budget_terminal') is not True
            or audit.get('audit', {}).get('exact_raw_tools_draft_source_definition_replayed') is not True
            or audit.get('audit', {}).get('own_history_loss_and_all_ties_replayed') is not True):
        raise ValueError('pinned complete independently replayed historical audit required')
    entries = []
    for arm, run in sorted(audit['runs'].items()):
        binding = run['binding']
        if binding['world']['source_commit'] != expected_source_commit or run['terminal'] is not True:
            raise ValueError('historical arm/source is not terminal and bound')
        for generation, record in enumerate(run['records']):
            if len(record['draws']) != len(record['observations']):
                raise ValueError('historical unfinished draw cannot be imported')
            # A generation failure still consumes its archived slot. It does
            # not acquire an invented candidate, measurement or numeric cost.
            rows = list(zip(record['draws'], record['observations'])) or [(None, None)]
            for draw_index, (draw, observation) in enumerate(rows):
                suggestion = draw['suggestion'] if draw is not None else None
                if (suggestion is None) != (observation is None):
                    raise ValueError('historical suggestion/observation presence differs')
                entries.append({'entry_id': f'{arm}:{generation}:{draw_index}',
                    'origin_arm': arm, 'generation': generation, 'draw_index': draw_index,
                    'suggestion': clone(suggestion), 'observation': clone(observation),
                    'original_loss_spec': clone(binding['loss_spec']),
                    'world_binding': clone(binding['world']), 'seeds': clone(binding['seeds']),
                    'provenance': {'request_sha256': record['request_sha256'],
                        'version_sha256': record['version_sha256'],
                        'record_sha256': digest(record),
                        'definition_sha256': digest(record['definition']),
                        'suggestion_sha256': digest(suggestion),
                        'observation_sha256': digest(observation),
                        'binding_sha256': digest({'world': binding['world'], 'seeds': binding['seeds'],
                                                  'loss_spec': binding['loss_spec']}),
                        'generation_error': clone(record['generation_error']),
                        'draw_technical_error': clone(draw.get('technical_error')) if draw else None}})
    bank = {'schema': SCHEMA, 'source_audit': {'content_sha256': expected_audit_content_sha256,
            'source_commit': expected_source_commit, 'role_bindings': clone(audit['role_bindings']),
            'raw_inventory_sha256': audit['audit'].get('raw_inventory_sha256'),
            'analysis_source_sha256': audit['audit'].get('analysis_source_sha256'),
            'original_source_audit_required': True}, 'entries': entries, 'claims': clone(CLAIMS)}
    bank['content_sha256'] = _hash_body(bank)
    return validate_initial_evidence(bank)


def validate_initial_evidence(bank, *, target_world=None, target_seeds=None):
    if (bank.get('schema') != SCHEMA or bank.get('claims') != CLAIMS
            or bank.get('content_sha256') != _hash_body(bank)
            or not bank.get('entries') or not bank.get('source_audit', {}).get('original_source_audit_required')):
        raise ValueError('immutable explicit historical evidence binding required')
    ids = set()
    for entry in bank['entries']:
        if entry['entry_id'] in ids:
            raise ValueError('historical entry identity repeated')
        ids.add(entry['entry_id'])
        world = entry['world_binding']
        if (entry['provenance']['suggestion_sha256'] != digest(entry['suggestion'])
                or entry['provenance']['observation_sha256'] != digest(entry['observation'])
                or entry['provenance']['binding_sha256'] != digest({'world': world,
                    'seeds': entry['seeds'], 'loss_spec': entry['original_loss_spec']})):
            raise ValueError('historical archived suggestion/observation/binding content changed')
        if world.get('source_commit') != bank['source_audit']['source_commit']:
            raise ValueError('historical source changed')
        if target_world is not None and any(world.get(k) != target_world.get(k) for k in COMPATIBILITY_FIELDS):
            raise ValueError('historical model/corpus/fidelity/population differs from declared target')
        if target_seeds is not None and entry['seeds'] != list(target_seeds):
            raise ValueError('historical development seeds differ from declared target')
        validate_loss_spec(entry['original_loss_spec'])
        if entry['suggestion'] is not None and entry['observation'] is not None:
            _check_pair(entry['suggestion'], entry['observation'], entry['original_loss_spec'], world, entry['seeds'])
        elif entry['suggestion'] is not None or entry['observation'] is not None:
            raise ValueError('historical incomplete suggestion/observation pair')
        elif not entry['provenance']['generation_error'] and not entry['provenance']['draw_technical_error']:
            raise ValueError('unobserved historical slot must retain its technical error')
    return clone(bank)


def select_incumbent(observations):
    """Loss-only selection, preserving all exact ties in stable arrival order."""
    valid = [pair for pair in observations if pair['observation']['status'] == 'complete'
             and not pair['observation']['metadata'].get('technical_failures')]
    if not valid:
        return {'loss': None, 'selected_observation_id': None, 'tied_observation_ids': []}
    best = min(pair['observation']['loss'] for pair in valid)
    tied = [p['observation']['observation_id'] for p in valid if p['observation']['loss'] == best]
    return {'loss': best, 'selected_observation_id': tied[0], 'tied_observation_ids': tied}


def objective_view(bank, loss_spec):
    """Re-score original measurements; never convert a technical failure to cost."""
    validate_initial_evidence(bank)
    validate_loss_spec(loss_spec)
    pairs, unobserved = [], []
    for entry in bank['entries']:
        original = entry['observation']
        if original is None:
            unobserved.append({'entry_id': entry['entry_id'], 'loss': None,
                               'provenance': clone(entry['provenance'])})
            continue
        evaluated = evaluate_loss(loss_spec, original['metadata']['measurements'])
        status = ('complete' if original['status'] == 'complete' and evaluated['status'] == 'complete'
                  else ('invalid' if original['status'] == 'complete' else original['status']))
        identity = digest({'initial_evidence_sha256': bank['content_sha256'],
                           'entry_id': entry['entry_id'], 'loss_spec_sha256': loss_spec_sha256(loss_spec)})
        metadata = {**clone(original['metadata']), 'loss_evaluation': evaluated,
            'loss_spec_sha256': loss_spec_sha256(loss_spec),
            'historical_initial_evidence': {'entry_id': entry['entry_id'],
                'bank_sha256': bank['content_sha256'], 'source_commit': entry['world_binding']['source_commit'],
                'original_observation_id': original['observation_id'], 'original_status': original['status'],
                'original_loss': original['loss'],
                'original_loss_evaluation': clone(original['metadata']['loss_evaluation']),
                'world_binding': clone(entry['world_binding']), 'seeds': clone(entry['seeds']),
                'provenance': clone(entry['provenance']),
                'source_equivalence_established': False, 'physical_cache_reuse_allowed': False}}
        observed = Observation('historical-rescore-' + identity, entry['suggestion']['suggestion_id'],
            clone(original['candidate']), status, evaluated['loss'] if status == 'complete' else None, metadata)
        pairs.append({'suggestion': clone(entry['suggestion']), 'observation': observed.to_dict()})
    return {'schema': VIEW_SCHEMA, 'bank_sha256': bank['content_sha256'],
        'loss_spec_sha256': loss_spec_sha256(loss_spec), 'observations': pairs,
        'unobserved_slots': unobserved, 'selection': select_incumbent(pairs)}
