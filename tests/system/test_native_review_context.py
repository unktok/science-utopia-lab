"""Original-world review ingress, default-off bytes and cold-restart QA only."""
from copy import deepcopy
from dataclasses import replace
from types import SimpleNamespace
import sqlite3

import pytest

from tests.runtime.test_portable_checkpoint_integration import fixed_corpus, seed, science_snapshot
from tests.system.test_native_science_kernel import make_sim
from utopia.runtime.checkpointing import PortableStop
from utopia.system import ArtifactTypeSpec, ChannelKind, ConnectionSpec, MechanismFamily, MechanismSpec, PortSpec, ScheduleSpec
from utopia.system.native_kernel import NativeScienceKernel, add_context_receiver, legacy_world_system
from utopia.system.native_review_context import enable_review_context, register_review_context, RECEIVER, REVIEW, PORT
from utopia.system.runtime import (DeliveredValue, GraphRuntimeError, MechanismContext,
    MechanismEvent, MechanismRegistry, MechanismResult, MechanismValue)


def ingress_spec():
    base = legacy_world_system()
    producer = MechanismSpec('notice', MechanismFamily.COMMUNICATION, 'test.review.notice.v1',
        outputs=(PortSpec('messages', ChannelKind.ARTIFACT, 'review-notice'),))
    base = replace(base, mechanisms=(*base.mechanisms, producer),
        artifact_types=(*base.artifact_types, ArtifactTypeSpec('review-notice')),
        schedules=(*base.schedules, ScheduleSpec('notice', 10)))
    return enable_review_context(add_context_receiver(base, source='notice', source_port='messages',
        receiver='delivered', phase=15), receiver='delivered')


def register_notice(kernel, registry):
    register_review_context(kernel, registry)
    def notice(context):
        authors = tuple(a.id for a in kernel._simulation.ecosystem.agent_population.values() if a.can_author)
        return MechanismResult(outputs={'messages': (MechanismValue({'notice': 'ACTUAL_REVIEW_CONTEXT',
            'year': context.period}, actor_ids=authors),)}, events=(MechanismEvent('test.review.notice'),))
    registry.register('test.review.notice.v1', 1, notice)


@pytest.mark.parametrize('enabled', [False, True])
def test_original_six_year_default_off_payload_equivalence_and_opt_in_cold_restart(
        tmp_path, fixed_corpus, monkeypatch, enabled):
    """Two compatibility comparisons, not fidelity populations or new findings."""
    monkeypatch.setattr('time.time', lambda: 1234567890.)
    spec = ingress_spec() if enabled else legacy_world_system()
    extension = register_notice if enabled else register_review_context
    reference, old_calls = make_sim(tmp_path/'reference', native=NativeScienceKernel(spec,
        registry_extension=register_notice if enabled else None))
    reference.run()
    expected = science_snapshot(reference)
    seed()
    stopped, prefix_calls = make_sim(tmp_path/'resume', native=NativeScienceKernel(spec,
        registry_extension=extension), after_effects=True)
    with pytest.raises(PortableStop):
        stopped.run()
    stopped.llm.response_cache.close()
    resumed, suffix_calls = make_sim(tmp_path/'resume', native=NativeScienceKernel(spec,
        registry_extension=extension))
    resumed.run()
    assert science_snapshot(resumed) == expected
    assert resumed.native_system.to_dict() == reference.native_system.to_dict()
    assert resumed.llm.reused > 0
    # Every actual/replayed payload must belong to the continuous reference;
    # the retry prefix is not falsely counted as independent response evidence.
    original_payloads = [p for _, p in old_calls]
    assert all(p in original_payloads for _, p in [*prefix_calls, *suffix_calls])
    # Full completed request/reply identity, not just a sample of review texts.
    def completed(root):
        with sqlite3.connect(f'file:{root}/cache/responses.sqlite?mode=ro', uri=True) as db:
            return db.execute('SELECT payload_sha,outcome,data_sha FROM replies ORDER BY payload_sha').fetchall()
    assert completed(tmp_path/'reference') == completed(tmp_path/'resume')
    reviews = [p for (ctx, _, _), p in old_calls if ctx[0] == 'phase3_reviews']
    assert reviews
    assert all(('ACTUAL_REVIEW_CONTEXT' in str(p)) == enabled for p in reviews)
    assert all('get_review_prompt' not in vars(a) for a in resumed.ecosystem.agent_population.values())
    assert (RECEIVER, 1) in resumed.native_system._registry().registered
    assert (REVIEW, 1) in resumed.native_system._registry().registered
    if enabled:
        events = [e for e in reference.native_system.events if e.event_type == 'native.system.review_context_used']
        assert len(events) == 6 and all(e.payload['uses'] for e in events)
        assert all(e.provenance['input_event_ids'] for e in events)
    resumed.llm.response_cache.close()
    reference.llm.response_cache.close()


def unit_context(node, inputs, *, state=None):
    return MechanismContext('unit-only', 'unit-only', node, 1, 15, 'annual', inputs, {}, state or {})


def test_receiver_rejects_entire_duplicate_batch_before_mutating_and_review_checks_exact_delivery():
    spec = ingress_spec()
    kernel = NativeScienceKernel(spec)
    actor = SimpleNamespace(id='a', can_author=True)
    kernel._simulation = SimpleNamespace(ecosystem=SimpleNamespace(agent_population={'a': actor}))
    registry = MechanismRegistry()
    register_review_context(kernel, registry)
    receiver = next(n for n in spec.mechanisms if n.implementation == RECEIVER)
    review = next(n for n in spec.mechanisms if n.implementation == REVIEW)
    value = DeliveredValue(ChannelKind.ARTIFACT, 'review-notice', {'notice': 'real'}, ('a',), (),
        ('producer-event',), 'notice', 'messages', 1, 1)
    # Duplicate recipients in a later record must not leave the first delivered.
    bad = replace(value, actor_ids=('a', 'a'))
    with pytest.raises(GraphRuntimeError, match='addressed'):
        registry.resolve(receiver)(unit_context(receiver, {'messages': (value, bad)}))
    assert not hasattr(actor, 'institutional_context')
    result = registry.resolve(receiver)(unit_context(receiver, {'messages': (value,)}))
    token = result.outputs['authorization'][0]
    delivered = DeliveredValue(ChannelKind.ARTIFACT, token.payload['schema'], token.payload, (), (),
        (*token.lineage_event_ids, 'delivery-event'), receiver.mechanism_id, 'authorization', 1, 1)
    context = unit_context(review, {PORT: (delivered,)})
    forged = deepcopy(dict(delivered.payload))
    forged['records'][0]['message']['payload']['notice'] = 'forged'
    with pytest.raises(GraphRuntimeError, match='not delivered'):
        registry.resolve(review)(replace(context, inputs={PORT: (replace(delivered, payload=forged),)}))
    with pytest.raises(GraphRuntimeError, match='wrong source'):
        registry.resolve(review)(replace(context, inputs={PORT: (replace(delivered, source_mechanism='other'),)}))
    # No un-restored monkeypatch if the original native review raises.
    actor.get_review_prompt = lambda *a, **kw: ('original', {})
    original = actor.get_review_prompt
    def fail(stage, context):
        text, _ = actor.get_review_prompt({'id': 'p'})
        assert 'real' in text
        raise RuntimeError('original review failed')
    kernel._stage = fail
    with pytest.raises(RuntimeError, match='original review failed'):
        registry.resolve(review)(context)
    assert actor.get_review_prompt is original
    with pytest.raises(GraphRuntimeError, match='repeated'):
        registry.resolve(receiver)(unit_context(receiver, {'messages': (value,)}, state=dict(result.next_state)))


def test_review_capability_must_be_explicit_and_before_review():
    with pytest.raises(GraphRuntimeError, match='requires original'):
        enable_review_context(legacy_world_system(), receiver='absent')
    spec = ingress_spec()
    # No repeated wrapping or implicit broadening to another receiver.
    with pytest.raises(GraphRuntimeError, match='requires original'):
        enable_review_context(spec, receiver='delivered')
