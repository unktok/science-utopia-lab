"""Explicit prospective native trajectory access; no inferred causal advice.

Raw scientific observations stay immutable. A scalar author receives no added
trajectory body, including through its exact request/history archive. A trace
author receives the selected parent's full fixed-field columnar projection
inline and all allowed completed own/reference projections in that archive.
Caller-owned campaign/reference provenance and a full physical cold audit are
still required; a digest or this view alone does not establish either.
"""
import hashlib
from pathlib import Path

from utopia.optimization import native_trajectory_columnar_v1 as codec
from utopia.optimization import native_trajectory_projection_v1 as projection
from utopia.optimization.native_numeric_designer import checked
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest

SCHEMA = 'scienceutopia.native-longitudinal-feedback.v1'
KEY = 'native_longitudinal_trajectory_v1'
VIEW = 'native_longitudinal_evidence_v1'
MODES = ('scalar', 'parent-trajectory')


def _sources():
    return {name: hashlib.sha256(Path(module.__file__).read_bytes()).hexdigest()
        for name, module in [('projection', projection), ('codec', codec)]} | {
            'access': hashlib.sha256(Path(__file__).read_bytes()).hexdigest()}


def contract(mode, *, source_commit, seeds, reference_ids):
    value = {'schema': SCHEMA + '.contract', 'mode': mode,
        'source_commit': source_commit, 'seeds': clone(seeds),
        'reference_ids': clone(reference_ids), 'component_sources': _sources(),
        'active_selection': 'all runs of exactly the loss-selected parent observation',
        'archive_access': 'R7/own records supplied by the enclosing declared campaign only',
        'automatic_truncation': False, 'loss_changed': False}
    value['content_sha256'] = digest(value)
    return validate_contract(value)


def validate_contract(value):
    checked(value)
    if (value.get('schema') != SCHEMA + '.contract' or value.get('mode') not in MODES
            or not isinstance(value.get('source_commit'), str) or not value['source_commit']
            or not isinstance(value.get('seeds'), list) or not value['seeds']
            or any(type(s) is not int or s < 0 for s in value['seeds'])
            or len(set(value['seeds'])) != len(value['seeds'])
            or not isinstance(value.get('reference_ids'), list)
            or any(not isinstance(s, str) or not s for s in value['reference_ids'])
            or len(set(value['reference_ids'])) != len(value['reference_ids'])
            or value.get('component_sources') != _sources()
            or value.get('active_selection') != 'all runs of exactly the loss-selected parent observation'
            or value.get('archive_access') != 'R7/own records supplied by the enclosing declared campaign only'
            or value.get('automatic_truncation') is not False or value.get('loss_changed') is not False
            or set(value) != {'schema', 'mode', 'source_commit', 'seeds', 'reference_ids',
                'component_sources', 'active_selection', 'archive_access',
                'automatic_truncation', 'loss_changed', 'content_sha256'}):
        raise ValueError('literal source-bound longitudinal access contract required')
    return clone(value)


def attach_projection(measurement, view, *, run):
    """Bind a projected completed checkpoint, without changing native metrics.

    The caller supplies the actual native physical run proof. This does not
    authenticate a fabricated proof or grant permission to disclose its data.
    """
    checked(view)
    if (KEY in measurement or view.get('schema') != projection.SCHEMA
            or measurement.get('run_id') != run.get('run_id')
            or measurement.get('system_fingerprint') != run.get('system_fingerprint')
            or view['system_fingerprint'] != run.get('system_fingerprint')
            or type(run.get('seed')) is not int or view['seed'] != run['seed']
            or view['checkpoint_file_sha256'] != run.get('checkpoint_sha256')):
        raise ValueError('literal measurement/checkpoint projection run binding differs')
    return {**clone(measurement), KEY: codec.encode(view)}


def measurement_adapter(measure, *, source_commit, years):
    """Optional real checkpoint collector for both future comparison arms.

    Enabled only by the explicit prospective longitudinal comparison runner.
    Its cold reader must reconstruct this metadata, not merely trust it.
    """
    if not callable(measure) or type(years) is not int or years < 1:
        raise ValueError('trusted measure callback and literal positive horizon required')
    def collect(sim, base):
        from utopia.runtime.checkpointing import read_portable_checkpoint
        from utopia.utils.data_utils import file_sha256
        checkpoint = Path(sim.output_dir) / f'portable_checkpoint_year_{years}.json.gz'
        if sim.num_years != years:
            raise ValueError('declared native horizon differs')
        before = file_sha256(checkpoint)
        view = projection.project_checkpoint(read_portable_checkpoint(checkpoint),
            source_commit=source_commit, system_fingerprint=base['system_fingerprint'],
            seed=sim.args.seed, years=years, checkpoint_file_sha256=before)
        if file_sha256(checkpoint) != before:
            raise ValueError('native checkpoint changed during trajectory collection')
        return attach_projection(measure(sim, clone(base)), view, run={
            'run_id': base['run_id'], 'system_fingerprint': base['system_fingerprint'],
            'seed': sim.args.seed, 'checkpoint_sha256': before})
    return collect


def _observation(value, access, *, reference, entries):
    result = clone(value)
    if not isinstance(result, dict) or not isinstance(result.get('metadata'), dict):
        raise ValueError('literal native observation required for longitudinal projection')
    metadata = result['metadata']
    if reference and result.get('suggestion_id') not in access['reference_ids']:
        raise ValueError('reference is outside the declared optimizer-visible bank')
    measurements = metadata.get('measurements', [])
    runs = metadata.get('runs', [])
    if not isinstance(measurements, list) or not isinstance(runs, list):
        raise ValueError('literal native measurement/run lists required')
    lookup = {r['run_id']: r for r in runs}
    if len(lookup) != len(runs):
        raise ValueError('duplicate native run proof')
    fingerprint = SystemSpec.from_dict(result['candidate']).fingerprint
    for row in measurements:
        encoded = row.pop(KEY, None)
        if encoded is None:
            if result.get('status') == 'complete':
                raise ValueError('complete comparison observation is missing its trajectory')
            continue
        view = codec.decode(encoded)
        run = lookup.get(row.get('run_id'))
        if (run is None or type(run.get('seed')) is not int or run['seed'] not in access['seeds']
                or view['seed'] != run['seed'] or view['source_commit'] != access['source_commit']
                or view['system_fingerprint'] != fingerprint
                or run.get('system_fingerprint') != fingerprint
                or row.get('system_fingerprint') != fingerprint
                or view['checkpoint_file_sha256'] != run.get('checkpoint_sha256')):
            raise ValueError('trajectory source/seed/policy/physical-run binding differs')
        identity = (result['observation_id'], row['run_id'])
        entry = {'observation_id': result['observation_id'],
            'suggestion_id': result['suggestion_id'], 'run_id': row['run_id'],
            'reference': reference, 'columnar': clone(encoded)}
        if identity in entries and entries[identity] != entry:
            raise ValueError('different trajectories for one native observation/run')
        entries[identity] = entry
    if result.get('status') == 'complete' and (
            not measurements or len(measurements) != len(runs)
            or {r.get('run_id') for r in measurements} != set(lookup)
            or sorted(r['seed'] for r in runs) != sorted(access['seeds'])):
        raise ValueError('complete native trajectory coverage differs')
    return result


def request_view(request, access, *, reference_observation_ids):
    """Deterministic author projection, including its exact history archive.

    The enclosing campaign supplies the reference IDs from its validated bank;
    own observations must come from its own already-validated records. This
    helper does not authenticate a caller's arbitrary records as own evidence.
    """
    access = validate_contract(access)
    if request.get('world_binding', {}).get('source_commit') != access['source_commit']:
        raise ValueError('longitudinal request and campaign source differ')
    if VIEW in request:
        raise ValueError('longitudinal request is already projected')
    result = clone(request); entries = {}
    reference_observation_ids = set(reference_observation_ids)
    for wrapped in result.get('observations', []):
        observation = wrapped['observation']
        if observation['candidate'] != wrapped['suggestion']['candidate']:
            raise ValueError('wrapped observation policy differs')
        wrapped['observation'] = _observation(observation, access,
            reference=observation['observation_id'] in reference_observation_ids, entries=entries)
    for history in result.get('history', []):
        history['observations'] = [None if value is None else _observation(value,
            access, reference=False, entries=entries) for value in history['observations']]
    # Reject an unhandled duplicate evidence channel instead of silently
    # leaking a trace through a new nested report/initial-bank field.
    def reserved(value):
        if isinstance(value, dict):
            # Candidate JSON is an unrestricted authored institution, not a
            # trusted measurement channel. Never ban a legitimate policy field
            # merely because its name resembles this operational metadata key.
            return KEY in value or any(reserved(v) for k, v in value.items()
                if k not in {'candidate', 'parent_system', 'design_space_anchor', 'definition'})
        return isinstance(value, list) and any(reserved(v) for v in value)
    if reserved(result):
        raise ValueError('trajectory outside the declared observation/history channel')
    selected = request.get('based_on_observation_id')
    active = [entry for entry in entries.values() if entry['observation_id'] == selected]
    if selected is not None and not active:
        raise ValueError('selected parent has no complete bound trajectory')
    parent = SystemSpec.from_dict(request['parent_system']).fingerprint
    if any(codec.decode(entry['columnar'])['system_fingerprint'] != parent for entry in active):
        raise ValueError('selected trajectory is not the literal current parent policy')
    if access['mode'] == 'scalar':
        active, archived = [], []
    else:
        archived = list(entries.values())
    result[VIEW] = {'schema': SCHEMA + '.view', 'access_contract': access,
        'active_parent': clone(active), 'archive_items': clone(archived),
        'raw_scientific_observations_modified': False,
        'author_request_is_an_explicit_projection': True,
        'causal_advice_or_candidate_policy_supplied': False,
        'context_token_capacity_proved': False}
    return result


def active_view(request):
    value = request[VIEW]
    access = validate_contract(value['access_contract'])
    if access['mode'] == 'scalar' and (value['active_parent'] or value['archive_items']):
        raise ValueError('scalar author must not receive trajectory bodies')
    return {'schema': value['schema'], 'access_contract': access,
        'active_parent': clone(value['active_parent']),
        'exact_archive_filename': 'archive/request.json',
        'archive_items_json_pointer': '/' + VIEW + '/archive_items',
        'scope': 'Observed native records, not inferred causes, a policy recommendation or additional loss.'}
