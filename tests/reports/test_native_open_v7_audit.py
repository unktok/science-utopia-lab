"""Read-only evidence QA only: no model transport, Docker or new native world."""
from copy import deepcopy
import json
import hashlib
from pathlib import Path
import sqlite3
from types import SimpleNamespace

import pytest

from scripts.analyze_native_open_v7 import analyze, authoring_proofs, code_proofs, domain_proofs, _inventory, FIXTURE
from scripts.run_native_open_pilot_v7 import summarize
from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign, InboxVocabularyGenerator
from utopia.optimization.native_manifest_inbox import ManifestInbox, ExternalAuthoringPending
from utopia.system.code_mechanisms import sha
from utopia.system.design_patch import digest
from utopia.system.native_open_examples import joint_engineering_loss, open_native_system
from utopia.utils.data_utils import write_json_atomic
from utopia.runtime.checkpointing import canonical_json

IMAGE = 'sha256:' + 'a'*64
WORLD = {'source_commit': 'b'*40, 'model_digest': 'scripted-only-no-Qwen',
    'corpus_sha256': 'scripted-only-no-corpus', 'classification': FIXTURE}


def create(root):
    return NativeAdaptiveDesignCampaign(root/'campaign', initial_system=open_native_system(IMAGE),
        loss_spec=joint_engineering_loss(), seeds=[42], world_binding=WORLD,
        strategies={'invent': {'kind': 'scripted-software-QA'}})


def setup_pending(root):
    campaign = create(root)
    gen = InboxVocabularyGenerator(ManifestInbox(root/'authoring'), instructions='Scripted software QA; never research evidence.')
    with pytest.raises(ExternalAuthoringPending) as exc:
        campaign.advance(simulation_factory=lambda *a: pytest.fail('no native execution'), generators={'invent': gen})
    summarize(campaign, root)
    return campaign, gen, exc.value


def respond(waiting, definition=None):
    write_json_atomic(waiting.response_path, {'request_sha256': waiting.request_sha256,
        'manifest': definition or {'base_patch': None, 'factors': [], 'continuous': [],
            'provenance': {'kind': 'scripted-software-QA'}},
        'authoring': {'kind': 'external', 'identity': 'scripted QA; no provider'}})


def fail_world(*a):
    raise RuntimeError('intentional technical fixture failure, not a numerical loss')


def test_pending_authoring_is_read_only_incomplete_and_never_live(tmp_path):
    setup_pending(tmp_path)
    before = _inventory(tmp_path)
    report = analyze(tmp_path, expected_source=WORLD['source_commit'], require_complete=False)
    assert _inventory(tmp_path) == before
    assert report['classification'] == FIXTURE
    assert report['audit']['status'] == 'incomplete'
    assert report['audit']['new_model_calls'] == report['audit']['new_container_executions'] == 0
    assert report['audit']['physical_native_worlds'] == 0
    assert not report['claims']['live_fixed_Qwen_researchers']
    assert report['audit']['external_authoring_proofs'][0]['status'] == 'awaiting-external-consumption'
    with pytest.raises(ValueError, match='four complete'):
        analyze(tmp_path, expected_source=WORLD['source_commit'])


def test_exact_external_manifest_replay_two_failed_batches_preserves_null_and_updates(tmp_path):
    campaign, gen, waiting = setup_pending(tmp_path)
    for generation in range(2):
        respond(waiting)
        record = campaign.advance(simulation_factory=fail_world, generators={'invent': gen})
        assert all(o['loss'] is None for o in record['observations'])
        if generation == 0:
            with pytest.raises(ExternalAuthoringPending) as exc:
                campaign.advance(simulation_factory=fail_world, generators={'invent': gen})
            waiting = exc.value
    summarize(campaign, tmp_path)
    before = _inventory(tmp_path)
    result = analyze(tmp_path, expected_source=WORLD['source_commit'], require_complete=False)
    assert before == _inventory(tmp_path)
    assert result['status'] == 'budget-complete-with-failures'
    assert result['audit']['budget_terminal'] and result['audit']['status'] == 'incomplete'
    assert result['audit']['loss_path'] == [None]*4
    assert len(result['audit']['external_authoring_proofs']) == 2
    assert all(r['report']['mixed']['gradient'] is None for r in result['records'])


def test_raw_claim_or_hash_tampering_fails_closed(tmp_path):
    setup_pending(tmp_path)
    path = tmp_path/'evidence.json'
    raw = json.loads(path.read_text())
    raw['claims']['scientific_value'] = True
    write_json_atomic(path, raw)
    with pytest.raises(ValueError, match='content hash'):
        analyze(tmp_path, expected_source=WORLD['source_commit'], require_complete=False)
    raw.pop('content_sha256')
    raw['content_sha256'] = digest(raw)
    write_json_atomic(path, raw)
    with pytest.raises(ValueError, match='claims'):
        analyze(tmp_path, expected_source=WORLD['source_commit'], require_complete=False)


def test_wrong_source_and_orphan_external_file_are_not_ignored(tmp_path):
    campaign, _, waiting = setup_pending(tmp_path)
    with pytest.raises(ValueError, match='source'):
        analyze(tmp_path, expected_source='c'*40, require_complete=False)
    orphan = waiting.response_path.with_name('f'*64+'.json')
    write_json_atomic(orphan, {'orphan': True})
    with pytest.raises(ValueError, match='orphan'):
        authoring_proofs(tmp_path/'authoring', [campaign.state['pending']])


def test_consumed_manifest_cannot_change_after_generation(tmp_path):
    campaign, gen, waiting = setup_pending(tmp_path)
    respond(waiting)
    campaign.advance(simulation_factory=fail_world, generators={'invent': gen})
    summarize(campaign, tmp_path)
    response = json.loads(waiting.response_path.read_text())
    response['authoring']['identity'] = 'rewritten provenance'
    write_json_atomic(waiting.response_path, response)
    with pytest.raises(ValueError, match='changed'):
        analyze(tmp_path, expected_source=WORLD['source_commit'], require_complete=False)


def test_partial_failed_world_response_hashes_are_audited_without_fabricating_loss(tmp_path):
    campaign, gen, waiting = setup_pending(tmp_path)
    respond(waiting)
    record = campaign.advance(simulation_factory=fail_world, generators={'invent': gen})
    draw = record['draws'][0]
    sid = draw['suggestion']['suggestion_id']+'-s42'
    cell = tmp_path/'worlds'/sid
    (cell/'replies').mkdir(parents=True)
    spec = draw['suggestion']['candidate']
    from utopia.system import SystemSpec
    binding = {'cell': SystemSpec.from_dict(spec).fingerprint, 'seed': 42, 'model': 'fake-model',
        'model_revision': WORLD['model_digest'], 'corpus_sha256': WORLD['corpus_sha256'],
        'science_config': {'source_commit': WORLD['source_commit'], 'years': 2}}
    payload = {'model': 'fake-model', 'seed': 42, 'messages': []}
    payload_sha = hashlib.sha256(canonical_json(payload).encode()).hexdigest()
    data = canonical_json({'model': 'fake-model', 'id': 'fixture-only', 'object': 'chat.completion',
        'created': 0, 'choices': [{'index': 0, 'message': {'role': 'assistant', 'content': 'QA'}, 'finish_reason': 'stop'}]})
    sql = cell/'replies/responses.sqlite'
    with sqlite3.connect(sql) as db:
        db.execute('CREATE TABLE metadata(binding TEXT)')
        db.execute('INSERT INTO metadata VALUES (?)', (canonical_json(binding),))
        db.execute('CREATE TABLE replies(identity TEXT,payload_sha TEXT,outcome TEXT,data TEXT,data_sha TEXT)')
        db.execute('INSERT INTO replies VALUES (?,?,?,?,?)', ('a'*64, payload_sha, 'response', data,
            hashlib.sha256(data.encode()).hexdigest()))
    write_json_atomic(cell/'system.json', spec)
    (cell/'wire-requests.jsonl').write_text(json.dumps({'year': 1,'payload': payload,'payload_sha256': payload_sha})+'\n')
    summarize(campaign, tmp_path)
    result = analyze(tmp_path, expected_source=WORLD['source_commit'], require_complete=False)
    assert result['audit']['physical_native_worlds'] == 0
    partial, = result['audit']['partial_physical_run_proofs']
    assert partial['loss'] is None and partial['response_proof']['researcher_responses'] == 1
    with sqlite3.connect(sql) as db:
        db.execute("UPDATE replies SET data_sha='corrupt'")
    summarize(campaign, tmp_path)
    with pytest.raises(ValueError, match='content hash'):
        analyze(tmp_path, expected_source=WORLD['source_commit'], require_complete=False)


def code_fixture():
    system = open_native_system(IMAGE)
    node = next(n for n in system.mechanisms if n.mechanism_id == 'native-feature-extractor')
    context = {'period': 1, 'phase': 100, 'random_seed': 42, 'state': {}, 'parameters': {},
        'inputs': {'observations': [{'payload': {}}]}}
    result = {'outputs': {'features': [], 'world': []}, 'state': {}}
    receipt = {'image_id': IMAGE, 'artifact_sha256': sha(node.parameters['code_artifact']),
        'context_sha256': sha(context), 'result_sha256': sha(result), 'wall_seconds': .1}
    row = {'schema': 'scienceutopia.native-code-input.v1',
        'binding': {'source_commit': WORLD['source_commit'], 'system_fingerprint': system.fingerprint, 'run_id': 'fixture'},
        'artifact': deepcopy(node.parameters['code_artifact']), 'context': context, 'result': result, 'receipt': receipt}
    row['bundle_sha256'] = sha(row)
    event = {'event_id': 'event1', 'event_type': 'generated.code_executed', 'year': 1,
        'payload': {k: v for k, v in receipt.items() if k != 'wall_seconds'},
        'provenance': {'mechanism_id': node.mechanism_id}}
    return system, row, {'events': [event]}


def test_code_receipts_positive_and_duplicate_attempts_are_explicitly_ambiguous(tmp_path):
    system, row, native = code_fixture()
    path = tmp_path/'code-contexts.jsonl'
    path.write_text(json.dumps(row)+'\n')
    proof = code_proofs(tmp_path, system, native, WORLD, 'fixture', complete=True)
    assert proof['one_to_one_physical_execution_proven']
    assert proof['committed_events'] == proof['recorded_executions'] == 1
    path.write_text((json.dumps(row)+'\n')*2)
    proof = code_proofs(tmp_path, system, native, WORLD, 'fixture', complete=True)
    assert not proof['one_to_one_physical_execution_proven']
    assert proof['ambiguous_native_event_count'] == 1
    assert proof['committed_events'] == 1 and proof['recorded_executions'] == 2
    assert all(r['attribution'] == 'ambiguous-physical-attempt' for r in proof['physical_records'])


def test_code_source_or_committed_event_without_context_rejected(tmp_path):
    system, row, native = code_fixture()
    with pytest.raises(ValueError, match='lacks its actual'):
        code_proofs(tmp_path, system, native, WORLD, 'fixture', complete=True)
    row['artifact']['source'] += '\n# different source\n'
    row['receipt']['artifact_sha256'] = sha(row['artifact'])
    row['bundle_sha256'] = sha({k: v for k, v in row.items() if k != 'bundle_sha256'})
    (tmp_path/'code-contexts.jsonl').write_text(json.dumps(row)+'\n')
    with pytest.raises(ValueError, match='not active'):
        code_proofs(tmp_path, system, native, WORLD, 'fixture', complete=True)


def test_committed_code_memory_must_roundtrip_and_continue(tmp_path):
    system, row, native = code_fixture()
    native['graph_checkpoint'] = {'mechanism_states': {'native-feature-extractor': {}}}
    (tmp_path/'code-contexts.jsonl').write_text(json.dumps(row)+'\n')
    proof = code_proofs(tmp_path, system, native, WORLD, 'fixture', complete=True)
    assert proof['committed_memory_chains'][0]['committed_calls'] == 1
    native['graph_checkpoint']['mechanism_states']['native-feature-extractor'] = {'forged': 1}
    with pytest.raises(ValueError, match='durable kernel memory'):
        code_proofs(tmp_path, system, native, WORLD, 'fixture', complete=True)


def test_inventory_rejects_symlink_and_never_reads_outside_raw(tmp_path):
    target = tmp_path.parent/'outside-evidence.txt'
    target.write_text('not native evidence')
    (tmp_path/'bad').symlink_to(target)
    with pytest.raises(ValueError, match='symlinks'):
        _inventory(tmp_path)
