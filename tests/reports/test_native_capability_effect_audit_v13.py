"""Actual original-world SCRIPTED QA for read-only v13 capability joins."""
from copy import deepcopy
import json
from pathlib import Path
import shutil

import pytest

from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from scripts.native_capability_effect_audit_v13 import (
    annual_capability_proof, capability_effect_proof, origin_proof)
from utopia.runtime.checkpointing import read_portable_checkpoint
from utopia.system.code_mechanisms import DockerCodeExecutor, sha


def original_run(tmp_path, monkeypatch, reviews=1):
    from tests.system.test_native_review_routing_v13 import routed_system
    from tests.system.test_native_science_kernel import make_sim
    from utopia.optimization.native_factory import record_native_http
    from utopia.optimization.native_code_trace import RecordingCodeExecutor
    from utopia.system.native_kernel import NativeScienceKernel
    monkeypatch.setattr('time.time', lambda: 1234567890.)
    executor = DockerCodeExecutor()
    spec = routed_system(executor.image_id, reviews=reviews)
    recorded = RecordingCodeExecutor(executor, tmp_path/'code-contexts.jsonl', binding={
        'source_commit': 'scripted-software-QA', 'system_fingerprint': spec.fingerprint, 'run_id': 'unit-world'})
    sim, calls = make_sim(tmp_path, native=NativeScienceKernel(spec, code_executor=recorded))
    record_native_http(sim.llm, sim, tmp_path/'wire-requests.jsonl')
    sim.run()
    sim.llm.response_cache.close()
    # Test-only physical layout adapter; these are real SCRIPTED native replies,
    # never actual Qwen, reused experiments or published scientific evidence.
    (tmp_path/'replies').mkdir()
    shutil.copyfile(tmp_path/'cache/responses.sqlite', tmp_path/'replies/responses.sqlite')
    checkpoint = Path(sim.output_dir)/'portable_checkpoint_year_6.json.gz'
    saved = read_portable_checkpoint(checkpoint)
    rows = [json.loads(line) for line in (tmp_path/'code-contexts.jsonl').read_text().splitlines()]
    return spec, checkpoint, saved, rows, calls


@pytest.mark.parametrize('reviews', [0, 1])
def test_complete_native_routing_joins_original_submissions_source_tasks_integer_reviews_and_http(
        tmp_path, fixed_corpus, monkeypatch, reviews):
    spec, checkpoint, saved, rows, calls = original_run(tmp_path, monkeypatch, reviews)
    before = {str(p): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    result = capability_effect_proof(tmp_path, spec, checkpoint)
    repeated = capability_effect_proof(tmp_path, spec, checkpoint)
    assert result == repeated
    assert before == {str(p): p.read_bytes() for p in tmp_path.rglob('*') if p.is_file()}
    assert result['routing_event_count'] == 6 and result['complete_plan_effect_count'] == 0
    expected = sum(ctx[0] == 'phase3_reviews' for (ctx, _, _), payload in calls)
    assert result['routed_actual_review_count'] == expected
    assert bool(expected) == bool(reviews)
    for year in result['annual']:
        routing = year['review_routings'][0]
        assert routing['command_origin_proof']['generated_output_matches']
        assert len(routing['actual_review_transport']) == routing['actual_review_count']


@pytest.mark.parametrize('tamper', ['command-source', 'command-wire', 'snapshot', 'native-record',
    'source-output', 'input-lineage', 'input-paper', 'future-lineage'])
def test_rehashed_receipts_still_require_original_world_source_wire_and_archived_facts(
        tmp_path, fixed_corpus, monkeypatch, tamper):
    spec, checkpoint, saved, rows, _ = original_run(tmp_path, monkeypatch, reviews=1)
    saved, rows = deepcopy(saved), deepcopy(rows)
    routing = next(e for e in saved['native_system']['events']
        if e['event_type'] == 'native.system.review_routing_applied' and e['year'] == 6)
    value = routing['payload']
    if tamper == 'command-source': value['command_origin']['source_mechanism'] = 'missing'
    elif tamper == 'command-wire': value['command_origin']['source_port'] = 'unwired'
    elif tamper == 'snapshot':
        event = next(e for e in saved['native_system']['events'] if e['event_type'] == 'native.system.review_inputs_bound' and e['year'] == 6)
        event['payload']['batch']['papers'][0]['paper']['title'] = 'forged'
    elif tamper == 'native-record':
        task = value['native_tasks'][0]
        record = next(r for p in saved['paper_tracker']['papers'] if p['id'] == task['paper_id']
            for d in p['review_history'] if d['year'] == 6 for r in d['reviews'])
        record['overall_score'] = 9
    elif tamper == 'source-output':
        for row in rows:
            if row['context']['period'] == 6:
                row['result']['outputs']['routing'][0]['payload']['tasks'] = []
    elif tamper == 'input-lineage': value['command_origin']['input_event_ids'] = ['missing']
    elif tamper == 'future-lineage':
        events = {e['event_id']: e for e in saved['native_system']['events']}
        for identity in value['command_origin']['input_event_ids']:
            events[identity]['sequence'] = routing['sequence']+1
    else:
        value['batch']['papers'][0]['paper']['title'] = 'forged'
        value['batch_sha256'] = sha(value['batch'])
        value['command']['batch_sha256'] = value['batch_sha256']
        value['command_sha256'] = sha(value['command'])
    with pytest.raises((ValueError, RuntimeError)):
        annual_capability_proof(saved, spec, rows)


def test_full_original_plan_provenance_closes_without_recorded_tee_input(tmp_path, fixed_corpus):
    from tests.system.test_native_science_kernel import make_sim
    from utopia.system.native_activity_contracts import activity_world_system
    from utopia.system.native_kernel import NativeScienceKernel
    spec = activity_world_system()
    sim, _ = make_sim(tmp_path, native=NativeScienceKernel(spec))
    sim.run()
    sim.llm.response_cache.close()
    checkpoint = Path(sim.output_dir)/'portable_checkpoint_year_6.json.gz'
    result = capability_effect_proof(tmp_path, spec, checkpoint)
    assert result['complete_plan_effect_count'] == 6
    assert result['routing_event_count'] == 0
    for year in result['annual']:
        plan = year['complete_plan_effects'][0]
        assert plan['base_plan_sha256'] == plan['applied_plan_sha256']
        assert plan['base_plan'] == plan['applied_plan']
        assert plan['base_origin_proof']['source_event_sha256s']


def test_missing_historical_full_plan_is_not_recast_as_complete(tmp_path, fixed_corpus):
    from tests.system.test_native_science_kernel import make_sim
    from utopia.system.native_activity_contracts import activity_world_system
    from utopia.system.native_kernel import NativeScienceKernel
    spec = activity_world_system()
    sim, _ = make_sim(tmp_path, native=NativeScienceKernel(spec))
    sim.run()
    sim.llm.response_cache.close()
    saved = read_portable_checkpoint(Path(sim.output_dir)/'portable_checkpoint_year_6.json.gz')
    event = next(e for e in saved['native_system']['events']
        if e['event_type'] == 'native.system.research_plan_applied' and e['year'] == 6)
    event['payload'].pop('base_plan')
    with pytest.raises(ValueError, match='unavailable'):
        annual_capability_proof(saved, spec, [])
