"""Opt-in original five-founder/Docker/cold construction check; SCRIPTED HTTP.

This is not scientific feasibility, model compliance or the future pilot's
operator-runner/900-second transport proof. Do not run during real inference.
"""
from contextlib import contextmanager
import json
import os
from pathlib import Path

import pytest

from tests.reports.test_native_capacity_full_path_v1 import install_scripted_provider
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from tests.system.test_native_legacy_choice_controls import anchor
from scripts.native_benchmark_physical import physical_proof
from utopia.optimization.common_content_observer import CommonContentObserver, make_contract
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_factory import LocalQwenNativeFactory
from utopia.optimization.native_numeric_designer import checked
from utopia.optimization.native_workflow_domain_v4 import post_funding_cost_control
from utopia.optimization.native_world import measure_native_world
from utopia.system import SystemSpec
from utopia.system.design_patch import digest
from utopia.system.native_legacy_choice_controls import controls, PRODUCER, PROTOCOL
from utopia.utils.data_utils import file_sha256, write_json_atomic


class ScriptedCritic:
    @contextmanager
    def lease(self, contract):
        yield self

    def __call__(self, wire, timeout):
        return {'http_status': 200, 'raw_http_response': json.dumps({
            'model': json.loads(wire)['model'], 'done': True, 'done_reason': 'stop',
            'prompt_eval_count': 71, 'eval_count': 9,
            'message': {'content': json.dumps({'score': 4, 'rationale': 'SCRIPTED software fixture'})}})}


@pytest.mark.skipif(os.environ.get('SCIENCE_UTOPIA_LEGACY_CHOICE_NATIVE_QA') != '1',
                    reason='opt-in committed-source hardware window required')
def test_three_original_world_controls_code_delivery_measurement_and_double_cold(
        tmp_path, fixed_corpus, monkeypatch):
    declared = os.environ.get('SCIENCE_UTOPIA_WORKFLOW_PLAN')
    if not declared:
        pytest.skip('explicit original world/loss binding required')
    original = checked(json.loads(Path(declared).read_text()))
    install_scripted_provider(tmp_path / 'provider', monkeypatch, 2)
    # Only the software fixture's seed changes. No reserved scientific seed is
    # used; the prospective pilot's seed remains as declared in its protocol.
    data = anchor().to_dict(); data['initial_state']['seed'] = 42
    systems = controls(post_funding_cost_control(SystemSpec.from_dict(data)))
    experiment = {'protocol': 'SCRIPTED-native-legacy-choice-construction-v1'}
    factory = LocalQwenNativeFactory(tmp_path / 'worlds', tmp_path / 'cache', years=4,
        corpus_years=4, record_wire=True, record_code=True, maximum_http_attempts=1024,
        inference_lock=tmp_path / 'inference.lock', experiment_binding=experiment,
        world_conditions=original['world']['world_conditions'])
    contract = make_contract(source_commit=factory.source_commit,
        provider={'model': factory.model, 'model_digest': factory.model_digest},
        backend={'model': factory.model, 'model_digest': factory.model_digest,
                 'ollama_version': 'SCRIPTED'}, maximum_posts=3000, critics=3)
    observer = CommonContentObserver(tmp_path / 'observer', contract, backend=ScriptedCritic())
    records = []
    for label, system in systems.items():
        run_id = 'SCRIPTED-legacy-choice-' + label
        cell = tmp_path / 'worlds' / run_id
        sim = factory(system, 42, run_id); sim.llm.sim = sim
        try:
            sim.run()
            assert len(sim.yearly_results) == 4 and sim.args.num_institutions == 5
            base = measure_native_world(sim, run_id=run_id)
            measured = observer.measure(sim, base)
            scores = {k: evaluate_loss(loss, [measured])['loss']
                      for k, loss in original['losses'].items()}
            events = sim.native_system.events
            deliveries = [e for e in events if e.event_type == 'native.system.context_delivered'
                          and e.payload['message']['source'] == PRODUCER]
            assert bool(deliveries) == (label == 'native-choice-advice')
            if label != 'core-assignment':
                assert not any(e.event_type == 'native.domain.catalog_project_validated' for e in events)
            for event in deliveries:
                payload = event.payload['message']['payload']
                assert payload['schema'] == PROTOCOL
                choices = payload['eligible_topics']
                best = min(choices, key=lambda d: (d['years'], d['topic']))
                assert (payload['recommended_topic'], payload['recommended_original_duration']) == (
                    best['topic'], best['years'])
            checkpoint = Path(sim.output_dir) / 'portable_checkpoint_year_4.json.gz'
            evidence = {'run_id': run_id, 'seed': 42, 'system_fingerprint': system.fingerprint,
                'checkpoint_path': str(checkpoint), 'checkpoint_sha256': file_sha256(checkpoint),
                'event_stream_hash': sim.native_system.to_dict()['event_stream_hash']}
        finally:
            sim.llm.response_cache.close()
        wires = [json.loads(line) for line in (cell / 'wire-requests.jsonl').read_text().splitlines()]
        directions = [w for w in wires if w['payload'].get('response_format', {}).get(
            'json_schema', {}).get('name') == 'research_direction_selection']
        assert bool(directions) == (label != 'core-assignment')
        if label == 'native-choice-advice':
            assert any(PROTOCOL in json.dumps(w['payload']['messages']) for w in directions)
        image = next(n.parameters['runtime_image_id'] for n in system.mechanisms
                     if n.implementation == 'code.python.v1')
        world = {'model': factory.model, 'model_digest': factory.model_digest,
            'source_commit': factory.source_commit, 'corpus_sha256': factory.corpus_sha256,
            'runtime_seed_binding': factory.runtime_seed_binding, 'experiment': experiment,
            'world_conditions': original['world']['world_conditions'], 'image_id': image}
        proofs = [physical_proof(cell, system, world=world, seed=42, years=4, evidence=evidence)
                  for _ in range(2)]
        assert proofs[0] == proofs[1] and proofs[0]['status'] == 'complete'
        assert proofs[0]['measurement'] == base
        assert len(proofs[0]['annual_checkpoints']) == 4
        records.append({'label': label, 'system_fingerprint': system.fingerprint,
            'scores': scores, 'direction_requests': len(directions), 'advice_deliveries': len(deliveries),
            'initial_physical_identity': proofs[0]['initial_identity'],
            'cold_proof_sha256': digest(proofs[0])})
    assert len({r['initial_physical_identity'] for r in records}) == 1
    audits = [observer.audit() for _ in range(2)]
    assert audits[0] == audits[1]
    write_json_atomic(tmp_path / 'verification.json', {
        'schema': 'scienceutopia.native-legacy-choice-construction-software.v1',
        'classification': 'SCRIPTED-HTTP-corpus-retrieval-and-critics-not-scientific-feasibility',
        'source_commit': factory.source_commit, 'software_worlds': records,
        'same_initial_physical_society_verified': True,
        'original_plan_file_sha256': file_sha256(declared),
        'observer_audit_content_sha256': audits[0]['content_sha256'],
        'new_real_model_calls': 0, 'policy_execution_on_host': False,
        'real_model_compliance_or_improvement_claimed': False,
        'operator_runner_and_scientist900_profile_verified': False,
        'publication_ready': False}, sort_keys=True)
