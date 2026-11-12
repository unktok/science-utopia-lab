"""Explicit year-end founder activity instrument for fresh native trajectories.

Counts native flags at saved boundaries, not person-time, useful work, fairness
or scientific quality. No objective is adopted by importing this instrument.
"""
from copy import deepcopy
from pathlib import Path

from utopia.runtime.checkpointing import read_portable_checkpoint
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256

SCHEMA = 'scienceutopia.native-active-founder-boundaries.v1'
METRIC = 'native.active_founder_boundary_sum'


def from_states(states):
    """Original initial cohort; never count newly created actors as founders."""
    if not isinstance(states, list) or len(states) < 2:
        raise ValueError('initial and every completed annual native state required')
    initial = states[0]
    binding = initial['portable']['contract']['binding']
    spec = initial['native_system']['spec']
    by_year = []
    for year, state in enumerate(states):
        if (type(state['year']) is not int or state['year'] != year
                or type(state['phase']) is not int or state['phase'] != (0 if year == 0 else 5)
                or type(state['native_system']['last_year']) is not int or state['native_system']['last_year'] != year
                or state['native_system']['spec'] != spec
                or state['portable']['contract']['binding'] != binding):
            raise ValueError('complete fresh fixed-spec native trajectory and binding required')
        actors = state['ecosystem_data']['agents']
        if (not isinstance(actors, list) or any(not isinstance(a, dict) or not isinstance(a.get('id'), str)
                or not a['id'] or type(a.get('can_author')) is not bool
                or type(a.get('is_active')) is not bool for a in actors)
                or len({a['id'] for a in actors}) != len(actors)):
            raise ValueError('literal distinct native actor records and Boolean activity flags required')
        by_year.append({a['id']: a for a in actors})
    founders = sorted(a['id'] for a in by_year[0].values() if a['can_author'])
    rows = []
    for year, actors in enumerate(by_year[1:], 1):
        records = []
        for identity in founders:
            actual = actors.get(identity)
            records.append({'actor_id': identity, 'present': actual is not None,
                'can_author': None if actual is None else actual['can_author'],
                'is_active': None if actual is None else actual['is_active'],
                'counted_active': actual is not None and actual['can_author'] and actual['is_active']})
        rows.append({'year': year, 'founders': records,
                     'active_founders': sum(a['counted_active'] for a in records)})
    return {'schema': SCHEMA, 'initial_founder_ids': founders, 'annual': rows,
        'value': sum(r['active_founders'] for r in rows), 'maximum': len(founders)*len(rows),
        'world_binding_sha256': digest(binding), 'system_sha256': digest(spec),
        'scope': 'Sum of original founder author-capability and is_active indicators at years1..Y. '
            'Year0 is excluded. Newly created actors never enlarge this initial cohort. An absent '
            'founder is explicitly recorded and contributes zero by definition, not a missing '
            'scientific loss. Unknown flags, missing years or changed bindings do not receive '
            'substituted values. This is saved native activity, not continuous survival/person-time, '
            'actual useful research work, resource sufficiency, scientific truth or an adoption veto.',
        'new_model_calls': 0, 'new_code_executions': 0}


def measure(simulation, base):
    """Append this explicit metric to an already completed native measurement."""
    root = Path(simulation.output_dir)
    paths = [root/f'portable_checkpoint_year_{year}.json.gz' for year in range(simulation.num_years+1)]
    hashes = {p.name: file_sha256(p) for p in paths}
    states = [read_portable_checkpoint(p) for p in paths]
    result = from_states(states)
    if (simulation.native_system.last_year != simulation.num_years
            or simulation.native_system.spec.to_dict() != states[-1]['native_system']['spec']
            or base['system_fingerprint'] != simulation.native_system.spec.fingerprint
            or METRIC in base['metrics'] or 'active_founder_boundary_instrument' in base):
        raise ValueError('completed literal native system and new nonoverwriting instrument required')
    if hashes != {p.name: file_sha256(p) for p in paths}:
        raise ValueError('original native annual states changed during measurement')
    output = deepcopy(base)
    output['metrics'][METRIC] = {'status': 'measured', 'value': result['value']}
    output['active_founder_boundary_instrument'] = {**result, 'checkpoint_sha256s': hashes}
    return output
