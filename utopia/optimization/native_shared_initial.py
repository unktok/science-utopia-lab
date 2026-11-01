"""Explicit cross-loss adoption of one physical native initial trajectory.

Logical objective arms are not independent replications. This narrow operation
reuses only an unchanged initial system with identical full world/seed binding.
It never adopts adaptive candidates, transfers between runtimes, or invents a
new model response. Checkpoint measurements are independently verified first.
"""
from pathlib import Path

from .blackbox import Observation, Suggestion
from .loss import evaluate_loss, loss_spec_sha256
from utopia.system.design_patch import clone, design_difference, digest
from utopia.utils.data_utils import file_sha256


def _record(target, source):
    source._validate()
    if (target.initial != source.initial or target.seeds != source.seeds
            or target.binding['world'] != source.binding['world']):
        raise ValueError('shared initial requires identical native system/world/seeds')
    if not source.state['records']:
        raise ValueError('completed physical initial observation required')
    original = source.state['records'][0]
    observation = original['observation']
    if (original['patch'] is not None or observation['status'] != 'complete'
            or observation['metadata'].get('technical_failures')
            or observation['metadata'].get('initial_adoption')):
        raise ValueError('only successful original physical initial may be adopted')
    if len(observation['metadata']['runs']) != len(target.seeds):
        raise ValueError('every declared initial seed needs physical evidence')
    runs = observation['metadata']['runs']
    measurements = observation['metadata']['measurements']
    if (sorted(r['seed'] for r in runs) != sorted(target.seeds)
            or len({r['run_id'] for r in runs}) != len(runs)
            or len(measurements) != len(runs)
            or {m['run_id'] for m in measurements} != {r['run_id'] for r in runs}):
        raise ValueError('physical initial seeds/runs/measurements are not one-to-one')
    if not {'model_digest', 'corpus_sha256', 'source_commit'} <= target.binding['world'].keys():
        raise ValueError('explicit model/corpus/source identity required for adoption')
    value = evaluate_loss(target.loss_spec, observation['metadata']['measurements'])
    if value['status'] != 'complete':
        raise ValueError('physical measurements do not support target loss')
    candidate = target.initial.to_dict()
    sid = 'native-design-' + digest({'index': 0, 'candidate': candidate,
                                    'binding': target.binding})[:20]
    suggestion = Suggestion(sid, candidate, 0, 'initial')
    metadata = clone(observation['metadata'])
    metadata.update(loss_spec_sha256=loss_spec_sha256(target.loss_spec),
                    loss_evaluation=value,
                    initial_adoption={
                        'schema': 'scienceutopia.shared-native-initial.v1',
                        'source_binding': clone(source.binding),
                        'source_initial_record_sha256': digest(original),
                        'physical_observation_id': observation['observation_id'],
                        'physical_run_ids': [r['run_id'] for r in metadata['runs']],
                        'independent_replication': False,
                    })
    return {'suggestion': suggestion.to_dict(), 'patch': None,
            'parent_system': candidate,
            'difference': design_difference(target.initial, target.initial),
            'observation': Observation('observation-' + sid, sid, candidate,
                'complete', value['loss'], metadata).to_dict()}


def verify_shared_initial(target, source, *, checkpoint_measurement):
    """Reconstruct logical record, verify physical bytes and independent metrics.

    ``checkpoint_measurement(path, run_id=..., fingerprint=...)`` must extract
    actual completed native state without calling the live measurement adapter.
    Later target observations are untouched. Source may have advanced since
    adoption; only its sealed first observation participates.
    """
    expected = _record(target, source)
    if not target.state['records'] or target.state['records'][0] != expected:
        raise ValueError('logical shared initial differs from original evidence')
    source_observation = source.state['records'][0]['observation']
    measurements = {m['run_id']: m for m in source_observation['metadata']['measurements']}
    for run in source_observation['metadata']['runs']:
        path = Path(run['checkpoint_path'])
        if file_sha256(path) != run['checkpoint_sha256']:
            raise ValueError('shared initial checkpoint bytes changed')
        from utopia.optimization.native_feedback import checked_native_state
        state, _ = checked_native_state(source.state['records'][0], run)
        binding = state['portable']['contract']['binding']
        world = target.binding['world']
        if (binding['cell'] != target.initial.fingerprint
                or binding['seed'] != run['seed']
                or binding['model_revision'] != world['model_digest']
                or binding['corpus_sha256'] != world['corpus_sha256']
                or binding['science_config'].get('source_commit') != world['source_commit']
                or ('model' in world and binding['model'] != world['model'])
                or ('years' in world and binding['science_config']['years'] != world['years'])
                or ('runtime_seed_binding' in world and binding['science_config'].get('runtime_seed_binding') != world['runtime_seed_binding'])):
            raise ValueError('physical initial checkpoint world/seed binding differs')
        actual = checkpoint_measurement(path, run_id=run['run_id'],
                                        fingerprint=target.initial.fingerprint)
        if actual != measurements[run['run_id']]:
            raise ValueError('shared initial independently extracted measurements differ')
    target._validate()
    return clone(expected)


def adopt_shared_initial(target, source, *, checkpoint_measurement):
    """Adopt once, fail before commit on any discrepancy, safely resume later."""
    if target is source or target.directory.resolve() == source.directory.resolve():
        raise ValueError('source and target must be separate logical objective arms')
    target._validate()
    if target.state['records']:
        return verify_shared_initial(target, source,
                                      checkpoint_measurement=checkpoint_measurement)
    if target.state['pending'] is not None:
        raise ValueError('cannot overwrite a pending physical initial')
    expected = _record(target, source)
    # Verify a temporary in-memory state before its first durable commit.
    target.state['records'] = [expected]
    try:
        verify_shared_initial(target, source,
                              checkpoint_measurement=checkpoint_measurement)
        target._save()
    except BaseException:
        target.state['records'] = []
        raise
    return clone(expected)
