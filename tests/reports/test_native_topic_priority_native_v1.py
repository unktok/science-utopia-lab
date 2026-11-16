"""Opt-in native factory/Docker/SDK/cold proof, with SCRIPTED corpus/replies.

This is not a new scientific optimization, a real-model capacity test, an outer
study CLI test or a proof of improved scientific outcomes.
"""
import json
import os
from pathlib import Path
import sqlite3

import httpx
from openai import OpenAI
import pytest

from utopia.optimization.blackbox import Observation
from utopia.optimization.native_parameter_space_v1 import NativeParameterOptimizer
from utopia.optimization.native_topic_priority_space_v1 import topic_priority_space
from scripts.reports.native_observed_request_classes_v1 import sequence
from tests.optimization.test_native_factory import capacity_conditions
from tests.reports.test_native_capacity_full_path_v1 import install_scripted_provider
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from utopia.optimization.native_factory import LocalQwenNativeFactory
from utopia.optimization.native_institution_workflow_domain_v6 import (
    institution_workflow_design_space, verify_institution_workflow_interval)
from utopia.optimization.native_design_space import require_candidate_in_space
from utopia.optimization.native_resource_cost import measure, METRIC
from utopia.optimization.native_scientist_transport_v1 import contract, configure_existing_client
from utopia.optimization.native_world import measure_native_world
from utopia.optimization.native_workflow_domain_v4 import post_funding_cost_control
from utopia.system import code_mechanisms
from utopia.system.design_patch import clone
from utopia.system.native_catalog_planning import catalog_contract
from utopia.system.native_legacy_topic_controls import legacy_topic_control
from utopia.system.native_legacy_topic_planning import EVENT
from utopia.system.native_planning_controls import planning_controls
from utopia.system.native_topic_priority_controls import topic_priority_control
from utopia.utils.data_utils import file_sha256, write_json_atomic

IMAGE = 'sha256:c5cd0ef1703ee77e4a056f51695d2d73b17d9bf07b167763058c0802105f8833'


@pytest.mark.skipif(os.environ.get('SCIENCE_UTOPIA_TOPIC_PRIORITY_NATIVE_QA') != '1',
                   reason='explicit clean-source hardware window; no real inference active')
@pytest.mark.parametrize('search_mode', [False, True], ids=['constructor', 'ask-tell'])
def test_zero_priority_full_inputs_and_changed_priority_actuation_with_double_cold(
        tmp_path, fixed_corpus, monkeypatch, search_mode):
    calls = install_scripted_provider(tmp_path / 'provider', monkeypatch, 2)
    from utopia.models import models
    original_constructor = models.VLLMServerModel
    sent, clients = [], []
    transport_contract = contract(read_seconds=900)

    def model(name, **kwargs):
        value = original_constructor(name, **kwargs)

        def transport(request):
            payload = json.loads(request.content)
            sent.append({'body': clone(payload), 'timeout': clone(request.extensions['timeout']),
                         'retry_count': request.headers['x-stainless-retry-count']})
            return httpx.Response(200, json=value.reply(**payload).model_dump())

        value.client = OpenAI(api_key='SCRIPTED-not-a-real-key', base_url='http://127.0.0.1:11434/v1',
            max_retries=0, http_client=httpx.Client(transport=httpx.MockTransport(transport)))
        configure_existing_client(value.client, transport_contract)
        clients.append(value.client)
        return value

    monkeypatch.setattr(models, 'VLLMServerModel', model)
    conditions = capacity_conditions(papers_per_project=2)
    experiment = {'protocol': 'SCRIPTED-native-topic-priority-software-v1'}
    factory = LocalQwenNativeFactory(tmp_path / 'runs', tmp_path / 'cache', years=4, corpus_years=4,
        record_wire=True, record_code=True, maximum_http_attempts=1024,
        inference_lock=tmp_path / 'inference.lock', world_conditions=conditions, experiment_binding=experiment)
    core = post_funding_cost_control(planning_controls(IMAGE, seed=42)['assignment-reserve21-no-review-all'])
    reference = legacy_topic_control(core, candidate_policy='core-plus-related')
    domain = institution_workflow_design_space(core)
    priorities = {topic: i for i, topic in enumerate(sorted(
        d['topic'] for d in catalog_contract()['directions']))}
    systems = [('reference', reference),
               ('zero-priority', topic_priority_control(reference, priorities={})),
               ('reverse-tie-priority', topic_priority_control(reference, priorities=priorities))]
    space = topic_priority_space(reference) if search_mode else None
    optimizer = NativeParameterOptimizer(space, seed=17, initial_random=1) if search_mode else None
    suggestions, search_trace = {}, []
    if search_mode:
        # No inherited reference loss: evaluate the exact dense-zero anchor first.
        systems = [('reference', reference), ('zero-priority', SystemSpec.from_dict(space.binding['anchor']))]
    worlds = []
    try:
        for label, spec in systems:
            require_candidate_in_space(core, spec, domain)
            identity = 'SCRIPTED-topic-priority-' + label
            sim = factory(spec, 42, identity)
            sim.llm.sim = sim
            try:
                sim.run()
                interval = verify_institution_workflow_interval(core, spec, sim.native_system.events, years=4)
                assert interval['effect_witnesses'] == 48 and interval['institutional_work_events'] == 0
                measured = measure_native_world(sim, run_id=identity)
                augmented = measure(sim, measured)
                assert augmented['metrics'][METRIC] == {'status': 'measured', 'value': 200.0}
                checkpoint = Path(sim.output_dir) / 'portable_checkpoint_year_4.json.gz'
                evidence = {'run_id': identity, 'seed': 42, 'system_fingerprint': spec.fingerprint,
                    'checkpoint_path': str(checkpoint), 'checkpoint_sha256': file_sha256(checkpoint),
                    'event_stream_hash': sim.native_system.to_dict()['event_stream_hash']}
                world = {k: getattr(factory, k) for k in ('model', 'model_digest', 'source_commit',
                    'corpus_sha256', 'runtime_seed_binding')}
                world.update(experiment=experiment, world_conditions=conditions, image_id=IMAGE)
                assignments = [e.to_dict() for e in sim.native_system.events if e.event_type == EVENT]
                assert assignments
                if search_mode and label != 'reference':
                    score = -measured['metrics']['native.accepted_decisions']['value']
                    if label == 'zero-priority':
                        optimizer.warm_start(Observation('SCRIPTED-measured-zero', 'SCRIPTED-zero-reference',
                            spec.to_dict(), 'complete', score))
                    else:
                        suggestion = suggestions[label]
                        assert suggestion.candidate == spec.to_dict()
                        optimizer.tell([Observation('SCRIPTED-' + label, suggestion.suggestion_id,
                            suggestion.candidate, 'complete', score)])
                    state = optimizer.state_dict()
                    restored = NativeParameterOptimizer.from_state(space, state)
                    record = {'label': label, 'actual_native_SCRIPTED_loss': score, 'after_tell': state}
                    search_trace.append(record)
                    if label in ('zero-priority', 'ask-tell-0'):
                        next_suggestion, = optimizer.ask()
                        assert next_suggestion.to_dict() == restored.ask()[0].to_dict()
                        next_label = 'ask-tell-' + str(len(suggestions))
                        suggestions[next_label] = next_suggestion
                        record['next_suggestion'] = next_suggestion.to_dict()
                        systems.append((next_label, SystemSpec.from_dict(next_suggestion.candidate)))
                worlds.append({'label': label, 'identity': identity, 'spec': spec,
                    'cell': tmp_path / 'runs' / identity, 'world': world, 'evidence': evidence,
                    'measurement': measured, 'augmented': augmented, 'assignments': assignments})
            finally:
                sim.llm.response_cache.close()
    finally:
        for client in clients:
            client.close()

    assert sent and all(v['timeout'] == transport_contract['http_timeout_seconds'] for v in sent)
    assert all(v['retry_count'] == '0' and 'timeout' not in v['body'] for v in sent)
    # Neither a cold proof nor the observed input comparison may execute code,
    # construct a model client or send another scientific/observer request.
    def forbidden(*args, **kwargs):
        pytest.fail('cold evidence must not construct a model or execute institution code')
    monkeypatch.setattr(OpenAI, '__init__', forbidden)
    monkeypatch.setattr(models, 'VLLMServerModel', forbidden)
    monkeypatch.setattr(code_mechanisms.DockerCodeExecutor, 'execute', forbidden)
    from scripts.native_benchmark_physical import physical_proof
    summaries = []
    for row in worlds:
        proofs = [physical_proof(row['cell'], row['spec'], world=row['world'], seed=42,
                    years=4, evidence=row['evidence']) for _ in (1, 2)]
        assert proofs[0] == proofs[1] and proofs[0]['status'] == 'complete'
        assert proofs[0]['measurement'] == row['measurement']
        wires = [json.loads(line) for line in (row['cell'] / 'wire-requests.jsonl').read_text().splitlines()]
        with sqlite3.connect((row['cell'] / 'replies/responses.sqlite').as_uri() + '?mode=ro', uri=True) as db:
            replies = db.execute('SELECT payload_sha,outcome,data,data_sha FROM replies ORDER BY rowid').fetchall()
        summaries.append({'label': row['label'], 'sequence': sequence(wires, replies),
            'assignments': row['assignments'], 'physical_proof': proofs[0],
            'augmented_measurement': row['augmented']})
    left, zero, changed = summaries[:3]
    # Keep the raw envelopes; graph-bound audit ids are intentionally distinct.
    # Compare actual project facts rather than requiring those ids to match.
    assignment_facts = lambda rows: [(e['year'], e['phase'], e['actor_ids'],
        e['payload']['assignment'], e['payload']['eligible_actor_before'],
        e['payload']['eligible_topics']) for e in rows]
    assert assignment_facts(left['assignments']) == assignment_facts(zero['assignments'])
    for key in ('wire_requests', 'completed_responses', 'ordered_full_request_payload_sha256',
                'ordered_literal_response_choices_sha256'):
        assert left['sequence'][key] == zero['sequence'][key]
    # Prove operative original-world change, not merely a source fingerprint.
    topics = lambda rows: [(e['year'], e['payload']['assignment']['actor_id'],
                           e['payload']['assignment']['direction']['topic']) for e in rows]
    assert topics(left['assignments']) != topics(changed['assignments'])
    assert left['sequence']['ordered_full_request_payload_sha256'] != changed['sequence'][
        'ordered_full_request_payload_sha256']
    if search_mode:
        assert len(summaries) == 4 and len(search_trace) == 3 and len(suggestions) == 2
        assert [r['label'] for r in search_trace] == ['zero-priority', 'ask-tell-0', 'ask-tell-1']
        assert len(optimizer.state_dict()['optimizer']['observations']) == 3
        assert search_trace[1]['next_suggestion']['phase'] == 'adaptive'
        assert search_trace[1]['next_suggestion']['based_on_observation_id'] in {
            'SCRIPTED-measured-zero', 'SCRIPTED-ask-tell-0'}
    write_json_atomic(tmp_path / 'verification.json', {
        'schema': 'scienceutopia.native-topic-priority-native-software.v1',
        'source_commit': factory.source_commit, 'classification': 'SCRIPTED-native-Docker-SDK-cold-not-scientific-gain',
        'worlds': summaries, 'actual_mock_SDK_POSTs': len(sent), 'scientist_fixture_calls': len(calls),
        'cold_new_models_or_code_executions_allowed': False, 'new_real_model_calls': 0,
        'scientific_gain_claimed': False, 'outer_study_CLI_verified': False,
        'existing_blackbox_ask_tell_native_path_verified': search_mode,
        'search_trace': search_trace,
        'independent_replications': False, 'publication_ready': False}, sort_keys=True)
