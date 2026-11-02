"""Synthetic transport tests only; no model/native-world execution.

The native checkpoint restorer/physical-state estimator are explicitly replaced
in this unit fixture. Actual production uses their real strict implementations.
Normal CompletedResponseCache.create/store is exercised, never cache rekeying.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

from openai.types.chat import ChatCompletion
import pytest

from utopia.agents.base_agent import PaperReview
from utopia.models.response_cache import CompletedResponseCache
from utopia.optimization.native_response_prefix import prepare_common_prefix, install_common_prefix
from utopia.runtime.checkpointing import PortableCheckpointError, canonical_json, write_portable_checkpoint
from utopia.system.design_patch import digest
from utopia.system.native_kernel import legacy_world_system
from utopia.utils.data_utils import file_sha256
from utopia.utils.seeding import derive_seed


def response(value, *, model='fixture-model'):
    return ChatCompletion.model_validate({'id': 'chatcmpl-synthetic-'+str(value), 'object': 'chat.completion',
        'created': 123, 'model': model, 'choices': [{'index': 0, 'finish_reason': 'stop',
            'message': {'role': 'assistant', 'content': json.dumps({'answer': value})}}]})


def payload(phase, year, *, text='ORIGINAL EXACT INPUT', review=False):
    value = {'model': 'fixture-model', 'seed': derive_seed(42, phase, year, 0, 0),
        'messages': [{'role': 'user', 'content': text}], 'temperature': .7}
    if review:
        value['response_format'] = {'type': 'json_schema', 'json_schema': {'schema': PaperReview.model_json_schema()}}
    return value


@pytest.fixture
def anchor(tmp_path, monkeypatch):
    import utopia.optimization.native_response_prefix as module
    monkeypatch.setattr(module, 'NativeScienceKernel', lambda spec, checkpoint: SimpleNamespace(
        last_year=checkpoint['last_year'], to_dict=lambda: {'event_stream_hash': checkpoint['event_stream_hash']}))
    monkeypatch.setattr(module, 'physical_initial_identity', lambda state: 'unit-physical-initial')
    root = tmp_path/'anchor'
    spec = legacy_world_system()
    binding = {'protocol': 'explicit-synthetic-prefix-test', 'cell': spec.fingerprint, 'seed': 42,
        'model': 'fixture-model', 'model_revision': 'fixture-revision', 'corpus_sha256': 'fixture-corpus',
        'science_config': {'source_commit': 'old-frozen-synthetic-source', 'years': 2, 'corpus_years': 4}}
    journal, wire = root/'replies/responses.sqlite', root/'wire-requests.jsonl'
    cache = CompletedResponseCache(journal, binding=binding)
    calls = [('phase1_directions', 1, payload('phase1_directions', 1)),
        ('phase2_intentions', 2, payload('phase2_intentions', 2)),
        ('phase3_reviews', 2, payload('phase3_reviews', 2, review=True, text='rubric .2')),
        ('phase5_funding_apps', 2, payload('phase5_funding_apps', 2))]
    for i, (phase, year, request) in enumerate(calls):
        cache.create(lambda **p: response(i), seed_ctx=(phase, year), item_index=0, attempt=0, **request)
    cache.close()
    wire.write_text(''.join(canonical_json({'year': year, 'payload_sha256': hashlib.sha256(canonical_json(request).encode()).hexdigest(),
        'payload': request})+'\n' for _, year, request in calls))
    checkpoints = root/'simulation/checkpoints/native-design'
    initial, final = checkpoints/'portable_checkpoint_year_0.json.gz', checkpoints/'portable_checkpoint_year_2.json.gz'
    write_portable_checkpoint(initial, {'year': 0, 'phase': 0,
        'portable': {'contract': {'binding': binding}, 'response_cache_count': 0}})
    write_portable_checkpoint(final, {'year': 2, 'phase': 5,
        'portable': {'contract': {'binding': binding}, 'response_cache_count': len(calls)},
        'native_system': {'last_year': 2, 'event_stream_hash': 'unit-native-event-stream'}})
    write_portable_checkpoint(checkpoints/'portable_checkpoint_year_1.json.gz', {'year': 1, 'phase': 5,
        'portable': {'contract': {'binding': binding}, 'response_cache_count': 1},
        'native_system': {'last_year': 1, 'event_stream_hash': 'unit-native-year1-events'}})
    contexts = root/'code-contexts.jsonl'
    contexts.write_text('{"unit_fixture_only":true}\n')
    endpoint = {'checkpoint': str(final), 'checkpoint_sha256': file_sha256(final),
        'initial_checkpoint_sha256': file_sha256(initial), 'code_contexts': str(contexts),
        'code_contexts_sha256': file_sha256(contexts), 'system': spec.to_dict(), 'system_fingerprint': spec.fingerprint,
        'physical_initial_identity': 'unit-physical-initial', 'response_cache_count': len(calls),
        'native_event_stream_hash': 'unit-native-event-stream',
        'world': {'source_commit': 'old-frozen-synthetic-source', 'model_digest': 'fixture-revision',
            'corpus_sha256': 'fixture-corpus', 'seed': 42}}
    return root, endpoint, binding, calls


def target(tmp_path, binding, *, root=None, concurrency=1):
    root = root or tmp_path/'target'
    checkpoint_dir = root/'simulation/checkpoints/native-design'
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    binding = deepcopy(binding)
    binding['science_config']['source_commit'] = 'new-coupled-synthetic-source'
    cache = CompletedResponseCache(root/'replies/responses.sqlite', binding=binding)
    fresh, wire = [], root/'wire-requests.jsonl'
    sim = SimpleNamespace(output_dir=str(checkpoint_dir), native_system=SimpleNamespace(spec=legacy_world_system(), _frame={'year': 1}))
    def physical(**request):
        fresh.append(deepcopy(request))
        with wire.open('a') as handle:
            handle.write(canonical_json({'year': sim.native_system._frame['year'],
                'payload_sha256': hashlib.sha256(canonical_json(request).encode()).hexdigest(), 'payload': request})+'\n')
        return response('NEW-FRESH-'+str(len(fresh)))
    model = SimpleNamespace(max_concurrent_requests=concurrency, response_cache=cache,
        client=SimpleNamespace(chat=SimpleNamespace(completions=SimpleNamespace(create=physical))))
    sim.llm = model
    return sim, wire, fresh


def request(sim, phase, year, data):
    sim.native_system._frame = {'year': year}
    return sim.llm.response_cache.create(sim.llm.client.chat.completions.create,
        seed_ctx=(phase, year), item_index=0, attempt=0, **data)


def test_replays_exact_actual_prefix_through_normal_new_binding_cache_then_uses_fresh_transport(tmp_path, anchor):
    root, endpoint, binding, calls = anchor
    prepared = prepare_common_prefix(root, endpoint)
    assert prepared['prefix_count'] == 2 and prepared['anchor_world'] == str(root)
    assert 'choices' not in json.dumps(prepared['calls'])
    sim, wire, fresh = target(tmp_path, binding)
    controller = install_common_prefix(sim, prepared, wire)
    try:
        for i, (phase, year, data) in enumerate(calls[:2]):
            actual = request(sim, phase, year, data)
            assert actual.model_dump(mode='json') == response(i).model_dump(mode='json')
        assert not fresh
        # Only the intervention payload changes; this response is genuinely
        # delegated to the original transport, not selected from the anchor.
        phase, year, original = calls[2]
        changed = deepcopy(original)
        changed['messages'][0]['content'] = 'rubric .8'
        request(sim, phase, year, changed)
        request(sim, *calls[3])
        result = controller.complete()
        assert result['replayed_response_count'] == 2
        assert result['fresh_physical_reply_count'] == 2
        assert result['logical_response_count'] == 4
        assert not result['independent_prefix_replication']
        records = [json.loads(line) for line in wire.read_text().splitlines()]
        assert all('replayed_from' in r for r in records[:2])
        assert all('replayed_from' not in r for r in records[2:])
        old_identity = prepared['calls'][0]['anchor_cache_identity']
        new_identity = sim.llm.response_cache._db.execute('SELECT identity FROM replies ORDER BY rowid LIMIT 1').fetchone()[0]
        assert old_identity != new_identity  # Normal native cache derives a NEW binding key.
    finally:
        sim.llm.response_cache.close()


@pytest.mark.parametrize('tamper', ['payload', 'seed', 'year'])
def test_mismatched_native_prefix_never_falls_back_to_fresh_inference(tmp_path, anchor, tamper):
    root, endpoint, binding, calls = anchor
    sim, wire, fresh = target(tmp_path, binding)
    controller = install_common_prefix(sim, prepare_common_prefix(root, endpoint), wire)
    phase, year, data = deepcopy(calls[0])
    if tamper == 'payload': data['messages'][0]['content'] += ' CHANGED'
    elif tamper == 'seed': data['seed'] += 1
    else: year += 1
    try:
        with pytest.raises(PortableCheckpointError, match='no fresh fallback'):
            request(sim, phase, year, data)
        assert not fresh and sim.llm.response_cache.committed_count() == 0
        assert controller.receipt()['used_prefix_count'] == 0
        with pytest.raises(ValueError, match='fully consumed'):
            controller.complete()
    finally:
        sim.llm.response_cache.close()


@pytest.mark.parametrize('tamper', ['year', 'schema', 'seed'])
def test_first_fresh_call_must_be_the_original_year2_review_boundary(tmp_path, anchor, tamper):
    root, endpoint, binding, calls = anchor
    sim, wire, fresh = target(tmp_path, binding)
    controller = install_common_prefix(sim, prepare_common_prefix(root, endpoint), wire)
    try:
        for call in calls[:2]: request(sim, *call)
        with pytest.raises(ValueError, match='fully consumed'): controller.complete()
        phase, year, data = deepcopy(calls[2])
        if tamper == 'year': year = 1
        elif tamper == 'schema': data.pop('response_format')
        else: data['seed'] += 1
        with pytest.raises(PortableCheckpointError, match='review boundary'):
            request(sim, phase, year, data)
        assert not fresh
    finally:
        sim.llm.response_cache.close()


@pytest.mark.parametrize('tamper', ['manifest', 'raw-wire', 'checkpoint', 'source', 'concurrency', 'binding', 'foreign-path'])
def test_installation_rejects_changed_anchor_or_wrong_target_without_any_transport_call(tmp_path, anchor, tamper):
    root, endpoint, binding, calls = anchor
    prepared = prepare_common_prefix(root, endpoint)
    sim, wire, fresh = target(tmp_path, binding, concurrency=2 if tamper == 'concurrency' else 1)
    if tamper == 'manifest': prepared['calls'][0]['seed'] += 1
    elif tamper == 'raw-wire': (root/'wire-requests.jsonl').write_text((root/'wire-requests.jsonl').read_text()+'\n')
    elif tamper == 'checkpoint': Path(endpoint['checkpoint']).write_bytes(b'changed')
    elif tamper == 'source': prepared['module_sha256'] = 'a'*64
    elif tamper == 'binding': sim.llm.response_cache.binding['model_revision'] = 'foreign-model'
    elif tamper == 'foreign-path': wire = tmp_path/'foreign.jsonl'
    try:
        with pytest.raises((ValueError, OSError, EOFError)):
            install_common_prefix(sim, prepared, wire)
        assert not fresh
    finally:
        sim.llm.response_cache.close()


def test_valid_resume_preserves_committed_replay_identity_and_rejects_origin_tampering(tmp_path, anchor):
    root, endpoint, binding, calls = anchor
    prepared = prepare_common_prefix(root, endpoint)
    sim, wire, fresh = target(tmp_path, binding)
    install_common_prefix(sim, prepared, wire)
    request(sim, *calls[0])
    sim.llm.response_cache.close()
    resumed, same_wire, resumed_fresh = target(tmp_path, binding)
    controller = install_common_prefix(resumed, prepared, same_wire)
    try:
        assert controller.receipt()['initially_committed_prefix_count'] == 1
        # A native re-execution's cache hit is ordinary, not new prefix inference.
        request(resumed, *calls[0])
        request(resumed, *calls[1])
        request(resumed, *calls[2])
        assert controller.complete()['fresh_physical_reply_count'] == 1
        assert not fresh and len(resumed_fresh) == 1
    finally:
        resumed.llm.response_cache.close()
    records = [json.loads(line) for line in wire.read_text().splitlines()]
    records[0]['replayed_from']['anchor_cache_identity'] = 'a'*64
    wire.write_text(''.join(canonical_json(row)+'\n' for row in records))
    broken, same_wire, no_fresh = target(tmp_path, binding)
    try:
        with pytest.raises(ValueError, match='provenance'):
            install_common_prefix(broken, prepared, same_wire)
        assert not no_fresh
    finally:
        broken.llm.response_cache.close()
