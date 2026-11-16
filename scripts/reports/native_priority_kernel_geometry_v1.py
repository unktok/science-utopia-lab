"""Read-only first-update geometry of the named native priority comparator.

This replays a trusted numeric ask, never a scientist, candidate program or
world. An expected ask without its original dispatch receipt is a diagnostic,
not an observed proposal, outcome or license to dispatch it.
"""
import math

from utopia.optimization.native_parameter_space_v1 import NativeParameterOptimizer, NativeParameterSpace
from utopia.system.design_patch import clone, digest
from utopia.system.native_topic_priority_controls import SOURCE


SCHEMA = 'scienceutopia.native-priority-first-update-geometry.v1'


def priority_order(values):
    """Descending priority, lexical exact ties; not whole-program equivalence."""
    if (not isinstance(values, dict) or not values
            or any(not isinstance(k, str) for k in values)
            or any(type(v) not in (int, float)
                or type(v) is float and not math.isfinite(v) for v in values.values())):
        raise ValueError('nonempty finite literal topic priorities required')
    return sorted(values, key=lambda topic: (-values[topic], topic))


def inspect_first_update(state, *, actual_started=None):
    """Project an exact saved post-tell state, optionally joining its actual ask.

    Restricted to this pilot's first update. The parameter optimizer itself and
    all historical contracts are unchanged. Returned values are diagnostics,
    not new fitness, a repaired candidate or an alternative frozen selection.
    """
    before = clone(state)
    if not isinstance(before, dict):
        raise ValueError('literal saved numeric optimizer state required')
    binding = before.get('space_binding', {})
    if not isinstance(binding, dict) or set(binding) != {'schema', 'anchor', 'design_space'}:
        raise ValueError('exact saved native priority space binding required')
    space = NativeParameterSpace(binding['anchor'], binding['design_space'])
    restored = NativeParameterOptimizer.from_state(space, before)
    optimizer = restored.state_dict()['optimizer']
    if (optimizer['proposal_index'] != 1 or optimizer['pending']
            or optimizer['config']['initial_random'] not in (1, 2)):
        raise ValueError('first completed numeric proposal before the second ask required')
    nodes = [n for n in binding['anchor']['mechanisms'] if n['mechanism_id'] == 'developer-catalog-agenda']
    if len(nodes) != 1:
        raise ValueError('named native priority producer required')
    parameters = nodes[0]['parameters']
    topics = sorted({d['topic'] for d in parameters['catalog']['directions']})
    expected_paths = {'/parameters/topic_priorities/' + t.replace('~', '~0').replace('/', '~1') for t in topics}
    coordinates = binding['design_space']['numeric_coordinates']
    if (parameters['code_artifact']['source'] != SOURCE or not topics
            or set(parameters['topic_priorities']) != set(topics)
            or any(parameters['topic_priorities'][t] != 0 for t in topics)
            or len(coordinates) != len(topics)
            or {c['path'] for c in coordinates} != expected_paths
            or any(c['mechanism_id'] != 'developer-catalog-agenda' or c['integer']
                or c['lower'] != -1 or c['upper'] != 1 for c in coordinates)):
        raise ValueError('literal zero-anchor equal-bound priority-only comparator required')
    suggestion, = restored.ask()
    after = restored.state_dict()
    if actual_started is not None:
        if (not isinstance(actual_started, dict)
                or actual_started.get('suggestion') != suggestion.to_dict()
                or actual_started.get('optimizer_after_ask') != after):
            raise ValueError('actual recorded suggestion/post-ask state differs from exact reconstruction')
    pool = [o for o in optimizer['observations'] if o['status'] == 'complete']
    parent = None
    scale = None
    intervals = None
    if suggestion.phase == 'adaptive':
        parent = min(pool, key=lambda o: (float(o['loss']), o['observation_id']))
        if parent['observation_id'] != suggestion.based_on_observation_id:
            raise ValueError('actual incumbent differs from loss/observation-id tie rule')
        count = max(0, suggestion.proposal_index - optimizer['config']['initial_random'])
        scale = max(.02, optimizer['config']['mutation_scale'] / math.sqrt(1 + count))
        parent_node = next(n for n in parent['candidate']['mechanisms']
                           if n['mechanism_id'] == 'developer-catalog-agenda')
        center = parent_node['parameters']['topic_priorities']
        radius = 2 * scale
        intervals = {t: [max(-1, center[t] - radius), min(1, center[t] + radius)] for t in topics}
    else:
        center = None
        radius = None
    proposed = next(n for n in suggestion.candidate['mechanisms']
                    if n['mechanism_id'] == 'developer-catalog-agenda')['parameters']['topic_priorities']
    zero = center is not None and all(center[t] == 0 for t in topics)
    iid_centered = zero and all(intervals[t] == [-radius, radius] for t in topics)
    if state != before:
        raise ValueError('read-only geometry analysis changed its input')
    return {'schema': SCHEMA, 'input_state_value_sha256': digest(state),
        'space_binding_sha256': space.binding_sha256,
        'config': clone(optimizer['config']), 'coordinate_count': len(topics),
        'expected_suggestion_id': suggestion.suggestion_id,
        'expected_program_sha256': digest(suggestion.candidate),
        'expected_post_ask_state_sha256': digest(after),
        'proposal_index': suggestion.proposal_index, 'phase': suggestion.phase,
        'actual_ask_receipt_supplied_and_matched': actual_started is not None,
        'parent_observation_id': None if parent is None else parent['observation_id'],
        'parent_assigned_loss': None if parent is None else parent['loss'],
        'parent_program_sha256': None if parent is None else digest(parent['candidate']),
        'parent_topic_priorities': None if center is None else clone(center),
        'effective_mutation_scale': scale, 'coordinate_radius': radius,
        'mutation_intervals': intervals, 'all_parent_priorities_zero': zero,
        'common_zero_centered_unclipped_intervals': iid_centered,
        'proposed_topic_priorities': clone(proposed),
        'proposed_descending_priority_order': priority_order(proposed),
        'scope': 'First-update trusted numeric reconstruction only. Common centered intervals '
            'describe the coordinate kernel; an ideal continuous ordering argument is not exact '
            'finite-PRNG equality, independence, whole-world/loss equivalence or evidence of '
            'adaptive benefit. Expected proposals without actual receipts remain unobserved. '
            'No candidate is repaired, dispatched, deduplicated or selected.',
        'new_model_calls': 0, 'new_native_worlds': 0, 'new_generated_code_executions': 0}
