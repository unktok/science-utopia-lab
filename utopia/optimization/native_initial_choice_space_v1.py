"""Prospective initial-choice proposals in the unchanged53-priority family.

The declared initial eligible-topic groups, not measured losses/behavior, define
this proposal distribution. This is a standard categorical/rank move, not new
optimizer theory, a new institution or an adopted scientific protocol.
"""
import math

from .native_parameter_space_v1 import NativeParameterSpace
from .native_topic_rank_space_v1 import NativeTopicRankSpace
from utopia.system.design_patch import clone, digest
from utopia.system.native_legacy_topic_planning import eligible_topics

SCHEMA = 'scienceutopia.native-initial-choice-space.v1'


def initial_groups(parameters, actors, *, period):
    if type(period) is not int or period < 1 or not isinstance(actors, list) or not actors:
        raise ValueError('explicit positive initial period and actor projection required')
    if parameters.get('candidate_policy') != 'core-plus-related':
        raise ValueError('unchanged core-plus-related priority consumer required')
    identities = []
    for actor in actors:
        if (not isinstance(actor, dict) or not isinstance(actor.get('id'), str) or not actor['id']
                or type(actor.get('can_author')) is not bool or type(actor.get('is_active')) is not bool
                or type(actor.get('project_end_year')) is not int):
            raise ValueError('literal native actor identity/eligibility fields required')
        identities.append(actor['id'])
    if len(set(identities)) != len(identities): raise ValueError('distinct declared initial actors required')
    catalog = parameters['catalog']; directions = {d['topic']: d for d in catalog['directions']}; groups = []
    for actor in sorted(actors, key=lambda a: a['id']):
        if not actor['can_author'] or not actor['is_active'] or actor['project_end_year'] >= period: continue
        eligible = eligible_topics(actor, catalog=catalog)
        minimum = min(directions[t]['years'] for t in eligible)
        topics = [t for t in eligible if directions[t]['years'] == minimum]
        if len(topics) > 1:
            groups.append({'actor_id': actor['id'], 'topics': topics, 'original_duration': minimum})
    if not groups: raise ValueError('declared initial input has no nontrivial shortest-topic choices')
    return groups


class NativeInitialChoiceSpace(NativeParameterSpace):
    def __init__(self, related_control, actors, *, period=1):
        self._rank = NativeTopicRankSpace(related_control)
        super().__init__(self._rank.binding['anchor'], self._rank.binding['design_space'])
        parameters = next(n['parameters'] for n in self._binding['anchor']['mechanisms']
                          if n['mechanism_id'] == 'developer-catalog-agenda')
        self._groups = initial_groups(parameters, actors, period=period)
        self._binding = {**self._binding, 'schema': SCHEMA,
            'initial_choice_kernel': {'actor_projection': clone(actors), 'period': period,
                'groups': clone(self._groups), 'initial_sampling': 'literal existing numeric uniform sampler',
                'initial_numeric_binding_sha256': self._rank.binding['rank_kernel']['initial_numeric_binding_sha256'],
                'mutation': 'choose initial actor group uniformly, swap its current top topic with a uniform alternative',
                'steps': 'max(1, floor(scale * initial_nontrivial_group_count))',
                'encoding': 'existing dyadic global-rank encoding in original [-1,1] priorities',
                'groups_are_fixed_initial_inputs_not_new_rollouts': True,
                'repeated_groups_and_undo_allowed': True, 'behavioral_change_or_merit_veto': False,
                'scope': 'Initial group locality, not global-rank locality, later-world behavior or loss locality'}}
        self._binding_sha256 = digest(self._binding)

    def order(self, candidate):
        return self._rank.order(candidate)

    def sample(self, *, seed, proposal_index):
        return self._rank.sample(seed=seed, proposal_index=proposal_index)

    def choice_steps(self, scale):
        if type(scale) not in (int, float) or not math.isfinite(scale) or not 0 < scale <= 1:
            raise ValueError('finite mutation scale in (0,1] required')
        return max(1, math.floor(scale * len(self._groups)))

    def mutate(self, incumbent, *, seed, proposal_index, scale):
        order = self.order(incumbent); count = self.choice_steps(scale)
        rng = self._rng(seed, proposal_index, 'initial-choice-rank-mutate')
        for _ in range(count):
            topics = self._groups[rng.randrange(len(self._groups))]['topics']
            positions = {topic: i for i, topic in enumerate(order)}
            winner = min(topics, key=positions.__getitem__)
            alternative = rng.choice([t for t in topics if t != winner])
            a, b = positions[winner], positions[alternative]
            order[a], order[b] = order[b], order[a]
        return self._rank.candidate_for_order(order)
