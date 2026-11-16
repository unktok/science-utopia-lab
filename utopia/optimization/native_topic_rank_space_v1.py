"""Prospective rank-local proposals in the existing native priority family.

This is an optional comparator adapter, not a new optimizer, simulator, default
method or dispatched experiment. The original numeric consumer and measured
anchor stay literal. A candidate's ordinal neighborhood is not a guarantee of
small native effects, changed behavior or improved loss.
"""
import math

from .native_parameter_space_v1 import NativeParameterSpace
from .native_topic_priority_space_v1 import topic_priority_space
from utopia.system.design_patch import digest

SCHEMA = 'scienceutopia.native-topic-rank-space.v1'


class NativeTopicRankSpace(NativeParameterSpace):
    """Existing numeric initial samples, then adjacent swaps of total rank.

    The supplied space remains all original bounded priority vectors. Exact
    ties are read using the existing lexical tie rule. Mutation emits dyadic
    rank weights; it does not replace or relabel a measured observation.
    NativeParameterOptimizer can persist/replay this explicit bound adapter.
    """
    def __init__(self, related_control):
        numeric = topic_priority_space(related_control)
        super().__init__(numeric.binding['anchor'], numeric.binding['design_space'])
        self._initial_numeric = numeric
        self._topics = [c['path'].removeprefix('/parameters/topic_priorities/').replace(
            '~1', '/').replace('~0', '~') for c in self._coordinates]
        if (len(set(self._topics)) != len(self._topics)
                or any(c['mechanism_id'] != 'developer-catalog-agenda'
                    or not c['path'].startswith('/parameters/topic_priorities/')
                    or c['integer'] or c['lower'] != -1. or c['upper'] != 1.
                    for c in self._coordinates)):
            raise ValueError('exact existing topic-priority coordinates required')
        self._binding = {**self._binding, 'schema': SCHEMA,
            'rank_kernel': {'initial_sampling': 'literal existing numeric uniform sampler',
                'initial_numeric_binding_sha256': numeric.binding_sha256,
                'order': 'decreasing priority, then lexical topic; original duration remains first',
                'mutation': 'k uniform adjacent-position swaps with replacement',
                'steps': 'max(1, floor(scale * (topic_count - 1)))',
                'encoding': 'dyadic strict rank values in the original [-1,1] bounds',
                'undo_and_same_order_allowed': True,
                'behavioral_change_or_merit_veto': False}}
        self._binding_sha256 = digest(self._binding)

    def order(self, candidate):
        values = self.values(candidate)
        priority = {topic: values[c['id']] for topic, c in zip(self._topics, self._coordinates, strict=True)}
        return sorted(self._topics, key=lambda topic: (-priority[topic], topic))

    def candidate_for_order(self, order):
        if (not isinstance(order, list) or len(order) != len(self._topics)
                or any(not isinstance(t, str) for t in order)
                or len(set(order)) != len(order) or set(order) != set(self._topics)):
            raise ValueError('one exact complete topic permutation required')
        # Binary-exact distinct weights, without rounding/coercing any received
        # model candidate. This is a declared trusted proposal operation only.
        denominator = 1 << max(1, len(order) - 1).bit_length()
        priorities = {topic: (len(order) - 1 - 2 * i) / denominator
                      for i, topic in enumerate(order)}
        return self.candidate({c['id']: priorities[topic] for topic, c in
                               zip(self._topics, self._coordinates, strict=True)})

    def sample(self, *, seed, proposal_index):
        # Paired initial literal programs are possible in a prospective finite
        # comparison; the separate rank binding does not change their RNG.
        return self._initial_numeric.sample(seed=seed, proposal_index=proposal_index)

    def rank_steps(self, scale):
        if type(scale) not in (int, float) or not math.isfinite(scale) or not 0 < scale <= 1:
            raise ValueError('finite mutation scale in (0,1] required')
        return max(1, math.floor(scale * (len(self._topics) - 1)))

    def mutate(self, incumbent, *, seed, proposal_index, scale):
        order = self.order(incumbent)
        count = self.rank_steps(scale)
        rng = self._rng(seed, proposal_index, 'adjacent-rank-mutate')
        if len(order) > 1:
            for _ in range(count):
                i = rng.randrange(len(order) - 1)
                order[i], order[i + 1] = order[i + 1], order[i]
        return self.candidate_for_order(order)


def rank_inversions(left, right):
    """Kendall inversion count, not native input/loss distance."""
    if (not isinstance(left, list) or not isinstance(right, list) or not left
            or any(not isinstance(t, str) for t in left + right)
            or len(set(left)) != len(left) or len(set(right)) != len(right)
            or set(left) != set(right)):
        raise ValueError('two exact nonempty permutations of the same topics required')
    positions = {topic: i for i, topic in enumerate(left)}
    values = [positions[topic] for topic in right]
    return sum(a > b for i, a in enumerate(values) for b in values[i + 1:])
