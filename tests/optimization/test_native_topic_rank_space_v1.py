"""Prospective native-family rank proposals; all losses explicitly SCRIPTED."""
from copy import deepcopy

import pytest

from tests.optimization.test_native_topic_priority_space_v1 import reference
from tests.system.test_native_topic_priority_controls import actors, output, producer
from utopia.system.native_catalog_planning import catalog_contract
from utopia.system.native_legacy_topic_planning import eligible_topics
from utopia.optimization.blackbox import Observation
from utopia.optimization.native_parameter_space_v1 import NativeParameterOptimizer
from utopia.optimization.native_topic_priority_space_v1 import topic_priority_space
from utopia.optimization.native_topic_rank_space_v1 import NativeTopicRankSpace, rank_inversions
from utopia.system import SystemSpec
from utopia.system.design_patch import digest
from utopia.system.native_topic_priority_controls import SOURCE


def test_literal_zero_initial_choice_barrier_exceeds_ten_global_adjacent_swaps():
    # The existing24-output component test already establishes the initial
    # choice tuples. This checks why global rank locality need not reach them.
    rank = NativeTopicRankSpace(reference()); anchor = rank.binding['anchor']
    order = rank.order(anchor); positions = {t: i for i, t in enumerate(order)}
    catalog = catalog_contract(); directions = {d['topic']: d for d in catalog['directions']}
    barriers = []
    for actor in actors():
        topics = eligible_topics(actor, catalog=catalog)
        minimum = min(directions[t]['years'] for t in topics)
        shortest = sorted(t for t in topics if directions[t]['years'] == minimum)
        barriers.append(None if len(shortest) == 1 else
            min(positions[t] - positions[shortest[0]] for t in shortest[1:]))
    assert len(order) == 53 and barriers == [None, 35, 27, 17, None]
    assert rank.rank_steps(.2) == 10 < min(v for v in barriers if v is not None)
    # At least that many adjacent swaps are needed to reverse an initial
    # winner/alternative pair. This is a fixed initial input, not all worlds.
    assert output(SOURCE, producer(SystemSpec.from_dict(anchor)).parameters, actors())[
        'outputs']['agenda'][0]['payload']['assignments'][3]['direction']['topic'] == 'deep_learning'


def test_seventeen_adjacent_swaps_can_cross_the_retained_initial_boundary():
    rank = NativeTopicRankSpace(reference()); anchor = rank.binding['anchor']
    order = rank.order(anchor); changed = order.copy()
    alternative = changed.index('meta-learning'); before = changed.index('deep_learning')
    assert alternative - before == 17
    # Explicit boundary witness, not a random proposal or a new loss result.
    for index in range(alternative, before, -1):
        changed[index], changed[index - 1] = changed[index - 1], changed[index]
    assert rank_inversions(order, changed) == 17
    candidate = rank.candidate_for_order(changed)
    assigned = output(SOURCE, producer(SystemSpec.from_dict(candidate)).parameters, actors())[
        'outputs']['agenda'][0]['payload']['assignments']
    assert assigned[3]['direction']['topic'] == 'meta-learning'
    assert assigned[3]['direction']['years'] == 1


def test_literal_anchor_initial_samples_and_native_consumer_remain_the_existing_family():
    related = reference(); numeric = topic_priority_space(related); rank = NativeTopicRankSpace(related)
    assert rank.binding['anchor'] == numeric.binding['anchor']
    assert rank.binding['design_space'] == numeric.binding['design_space']
    assert rank.binding_sha256 != numeric.binding_sha256
    assert rank.binding['rank_kernel']['initial_numeric_binding_sha256'] == numeric.binding_sha256
    assert rank.binding['rank_kernel']['undo_and_same_order_allowed']
    for i in range(3):
        assert rank.sample(seed=31, proposal_index=i) == numeric.sample(seed=31, proposal_index=i)
    anchor = rank.binding['anchor']; strict_lexical = rank.candidate_for_order(rank.order(anchor))
    assert anchor != strict_lexical  # Never assign a measured anchor loss to this new program.
    a, b = (producer(SystemSpec.from_dict(c)) for c in (anchor, strict_lexical))
    assert a.parameters['code_artifact']['source'] == b.parameters['code_artifact']['source'] == SOURCE
    assert output(SOURCE, a.parameters, actors()) == output(SOURCE, b.parameters, actors())


@pytest.mark.parametrize('scale', [.00001, .02, .2, 1.])
def test_mutations_bound_actual_rank_distance_and_preserve_all_noncoordinate_fields(scale):
    rank = NativeTopicRankSpace(reference()); anchor = rank.binding['anchor']; before = deepcopy(anchor)
    order = rank.order(anchor)
    for index in range(4):
        result = rank.mutate(anchor, seed=17, proposal_index=index, scale=scale)
        assert rank_inversions(order, rank.order(result)) <= rank.rank_steps(scale)
        if rank.rank_steps(scale) == 1: assert rank_inversions(order, rank.order(result)) == 1
        rank.validate(result)
        fixed = deepcopy(result)
        old = producer(SystemSpec.from_dict(anchor)).parameters['topic_priorities']
        next(n for n in fixed['mechanisms'] if n['mechanism_id'] == 'developer-catalog-agenda')[
            'parameters']['topic_priorities'] = old
        assert fixed == anchor
        values = list(producer(SystemSpec.from_dict(result)).parameters['topic_priorities'].values())
        assert len(set(values)) == len(values) == 53 and all(-1 <= v <= 1 for v in values)
    assert anchor == before


def test_adjacent_swaps_can_undo_without_behavioral_novelty_rejection(monkeypatch):
    rank = NativeTopicRankSpace(reference()); anchor = rank.binding['anchor']
    class SameEdge:
        def randrange(self, n): assert n == 52; return 0
    monkeypatch.setattr(rank, '_rng', lambda *args: SameEdge())
    assert rank.rank_steps(2 / 52) == 2
    result = rank.mutate(anchor, seed=1, proposal_index=1, scale=2 / 52)
    assert rank.order(result) == rank.order(anchor)
    assert rank_inversions(rank.order(anchor), rank.order(result)) == 0
    assert result != anchor  # Different legal weights; no unmeasured world equivalence is asserted.


def test_one_targeted_adjacent_move_can_reach_the_actual_initial_actor(monkeypatch):
    rank = NativeTopicRankSpace(reference()); order = rank.order(rank.binding['anchor'])
    # Put the real actor's two equal-duration eligible topics adjacent. This
    # uses the unchanged trusted comparator/retained native initial actors.
    first, second = 'artificial_intelligence', 'neural_symbolic_ai'
    order.remove(first); order.remove(second); order = [first, second, *order]
    candidate = rank.candidate_for_order(order)
    class FirstEdge:
        def randrange(self, n): return 0
    monkeypatch.setattr(rank, '_rng', lambda *args: FirstEdge())
    changed = rank.mutate(candidate, seed=0, proposal_index=0, scale=.0001)
    def topic(c):
        node = producer(SystemSpec.from_dict(c))
        rows = output(SOURCE, node.parameters, actors())['outputs']['agenda'][0]['payload']['assignments']
        return next(a['direction']['topic'] for a in rows if a['actor_id'] == 'institution_0001_researcher_0')
    assert topic(candidate) == first and topic(changed) == second
    assert rank_inversions(rank.order(candidate), rank.order(changed)) == 1


def test_existing_ask_tell_feedback_and_pending_state_replay_bind_the_rank_kernel():
    rank = NativeTopicRankSpace(reference()); anchor = rank.binding['anchor']
    opt = NativeParameterOptimizer(rank, seed=79011, initial_random=1)
    opt.warm_start(Observation('SCRIPTED-anchor', 'SCRIPTED-reference', anchor, 'complete', 0.))
    first, = opt.ask()
    saved = deepcopy(opt.state_dict())
    restored = NativeParameterOptimizer.from_state(NativeTopicRankSpace(reference()), saved)
    assert restored.state_dict() == saved
    failed = Observation('SCRIPTED-null', first.suggestion_id, first.candidate, 'failed', None)
    opt.tell([failed]); restored.tell([failed])
    second, = opt.ask(); replayed, = restored.ask()
    assert second.to_dict() == replayed.to_dict()
    assert second.phase == 'adaptive' and second.based_on_observation_id == 'SCRIPTED-anchor'
    assert rank_inversions(rank.order(anchor), rank.order(second.candidate)) <= rank.rank_steps(.2)
    assert opt.state_dict()['optimizer']['observations'][-1]['loss'] is None
    with pytest.raises(ValueError, match='exact expected native numeric space'):
        NativeParameterOptimizer.from_state(topic_priority_space(reference()), saved)
    wrong = deepcopy(saved); wrong['space_binding']['rank_kernel']['steps'] = 'SCRIPTED changed kernel'
    with pytest.raises(ValueError, match='exact expected native numeric space'):
        NativeParameterOptimizer.from_state(rank, wrong)
    assert digest(saved) == digest(NativeParameterOptimizer.from_state(rank, saved).state_dict())


def test_new_rank_representative_cannot_inherit_the_anchor_measurement():
    rank = NativeTopicRankSpace(reference()); anchor = rank.binding['anchor']
    strict = rank.candidate_for_order(rank.order(anchor))
    opt = NativeParameterOptimizer(rank, seed=1)
    with pytest.raises(ValueError, match='literal numeric-space anchor'):
        opt.warm_start(Observation('SCRIPTED-new-program', 'SCRIPTED-reference', strict, 'complete', 0.))


def test_rank_encoding_roundtrip_and_known_distance_are_exact():
    rank = NativeTopicRankSpace(reference()); order = rank.order(rank.binding['anchor'])
    reverse = order[::-1]
    assert rank.order(rank.candidate_for_order(reverse)) == reverse
    assert rank_inversions(order, reverse) == len(order) * (len(order) - 1) // 2
    assert rank_inversions(reverse, order) == rank_inversions(order, reverse)
    assert rank_inversions(order, order) == 0


@pytest.mark.parametrize('scale', [True, 0., -1., 1.01, float('nan'), float('inf'), '0.2'])
def test_invalid_scale_is_not_coerced(scale):
    rank = NativeTopicRankSpace(reference())
    with pytest.raises(ValueError): rank.mutate(rank.binding['anchor'], seed=0, proposal_index=0, scale=scale)


@pytest.mark.parametrize('case', ['missing', 'duplicate', 'foreign', 'nonlist', 'nonstring'])
def test_incomplete_or_malformed_permutations_are_not_repaired(case):
    rank = NativeTopicRankSpace(reference()); order = rank.order(rank.binding['anchor'])
    if case == 'missing': order.pop()
    elif case == 'duplicate': order[-1] = order[0]
    elif case == 'foreign': order[-1] = 'SCRIPTED-not-a-topic'
    elif case == 'nonlist': order = tuple(order)
    else: order[-1] = True
    with pytest.raises(ValueError): rank.candidate_for_order(order)


@pytest.mark.parametrize('left,right', [([], []), (['a', 'a'], ['a', 'b']),
    (['a'], ['b']), (['a'], [True]), (('a',), ['a'])])
def test_invalid_distance_inputs_are_not_coerced(left, right):
    with pytest.raises(ValueError): rank_inversions(left, right)
