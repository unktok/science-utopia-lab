"""Opt-in real native/Docker/cold path; HTTP/corpus scripted, not feasibility."""
from copy import deepcopy
import os
from pathlib import Path

import pytest

from tests.optimization.test_native_factory import capacity_conditions
from tests.reports.test_native_capacity_full_path_v1 import install_scripted_provider
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from utopia.optimization.native_factory import LocalQwenNativeFactory
from utopia.optimization.native_world import measure_native_world
from utopia.optimization.native_resource_cost import measure, METRIC
from utopia.optimization.native_design_space import require_candidate_in_space
from utopia.optimization.native_workflow_domain_v4 import post_funding_cost_control
from utopia.optimization.native_workflow_domain_v5 import legacy_topic_workflow_design_space
from utopia.runtime.checkpointing import read_portable_checkpoint
from utopia.system.native_legacy_topic_controls import legacy_topic_control
from utopia.system.native_legacy_topic_planning import ACTION, EVENT, eligible_topics
from utopia.system.native_catalog_planning import catalog_contract
from utopia.system.native_planning_controls import planning_controls
from utopia.utils.data_utils import file_sha256, write_json_atomic

IMAGE = 'sha256:c5cd0ef1703ee77e4a056f51695d2d73b17d9bf07b167763058c0802105f8833'


@pytest.mark.skipif(os.environ.get('SCIENCE_UTOPIA_LEGACY_TOPIC_QA') != '1',
                   reason='explicit clean-source shared-hardware QA window required')
def test_original_topic_actuation_two_native_worlds_and_cold_reconstruction(tmp_path, fixed_corpus, monkeypatch):
    calls = install_scripted_provider(tmp_path / 'provider', monkeypatch, 2)
    conditions = capacity_conditions(papers_per_project=2)
    experiment = {'protocol': 'scripted-legacy-topic-actuation-software-v1'}
    factory = LocalQwenNativeFactory(tmp_path / 'runs', tmp_path / 'cache', years=4, corpus_years=4,
        record_wire=True, record_code=True, maximum_http_attempts=1024,
        inference_lock=tmp_path / 'inference.lock', world_conditions=conditions, experiment_binding=experiment)
    core = post_funding_cost_control(planning_controls(IMAGE, seed=42)['assignment-reserve21-no-review-all'])
    domain = legacy_topic_workflow_design_space(core)
    summaries = []
    for policy in ('core-only', 'core-plus-related'):
        spec = legacy_topic_control(core, candidate_policy=policy)
        require_candidate_in_space(core, spec, domain)
        identity = 'scripted-legacy-topic-' + policy
        sim = factory(spec, 42, identity); sim.llm.sim = sim
        try:
            sim.run()
            measurement = measure_native_world(sim, run_id=identity)
            augmented = measure(sim, measurement)
            checkpoint = Path(sim.output_dir) / 'portable_checkpoint_year_4.json.gz'
            evidence = {'run_id': identity, 'seed': 42, 'system_fingerprint': spec.fingerprint,
                'checkpoint_path': str(checkpoint), 'checkpoint_sha256': file_sha256(checkpoint),
                'event_stream_hash': sim.native_system.to_dict()['event_stream_hash']}
            world = {k: getattr(factory, k) for k in ('model', 'model_digest', 'source_commit',
                'corpus_sha256', 'runtime_seed_binding')}
            world.update(experiment=experiment, world_conditions=conditions, image_id=IMAGE)
            from scripts.native_benchmark_physical import physical_proof
            proofs = [physical_proof(tmp_path / 'runs' / identity, spec,
                      world=world, seed=42, years=4, evidence=evidence) for _ in (1, 2)]
            assert proofs[0] == proofs[1] and proofs[0]['status'] == 'complete'
            assert proofs[0]['measurement'] == measurement
            assignments = proofs[0]['native_counts']['project_assignments_verified']
            events = [e for e in sim.native_system.events if e.event_type == EVENT]
            assert assignments and len(assignments) == len(events)
            assert proofs[0]['native_counts']['actions'][ACTION] == len(assignments)
            assert all(a['catalog_validation']['choice_domain'] == 'original-core-plus-direct-related' for a in assignments)
            assert all(e.payload['eligible_topics'] == eligible_topics(e.payload['eligible_actor_before'],
                       catalog=catalog_contract()) for e in events)
            outside = [e for e in events if e.payload['assignment']['direction']['topic']
                       not in e.payload['eligible_actor_before']['expertise']]
            assert bool(outside) == (policy == 'core-plus-related')
            assert all(e.payload['assignment']['project_end_year'] == e.year +
                e.payload['assignment']['direction']['years'] - 1 for e in events)
            from scripts.analyze_native_open_v7 import domain_proofs
            for mutation in ('catalog', 'eligible-topics', 'expertise', 'duration'):
                bad = deepcopy(read_portable_checkpoint(checkpoint))
                payload = next(e for e in bad['native_system']['events'] if e['event_type'] == EVENT)['payload']
                if mutation == 'catalog': payload['catalog_sha256'] = '0' * 64
                if mutation == 'eligible-topics': payload['eligible_topics'].append('invented-topic')
                if mutation == 'expertise': payload['eligible_actor_before']['expertise'].append('invented-topic')
                if mutation == 'duration': payload['assignment']['project_end_year'] += 1
                with pytest.raises((ValueError, RuntimeError)):
                    domain_proofs(bad, sim.native_system)
            summaries.append({'policy': policy, 'source_commit': factory.source_commit,
                'checkpoint_sha256': file_sha256(checkpoint), 'effects': len(events),
                'outside_core_effects': len(outside), 'resource_metric': augmented['metrics'][METRIC],
                'double_physical_proof_equal': True})
        finally:
            sim.llm.response_cache.close()
    write_json_atomic(tmp_path / 'verification.json', {
        'schema': 'scienceutopia.native-legacy-topic-software.v1',
        'classification': 'scripted-http-and-corpus-native-docker-cold-software-not-model-feasibility',
        'worlds': summaries, 'scientist_fixture_calls': len(calls),
        'new_real_model_calls': 0, 'scientific_gain_claimed': False, 'publication_ready': False}, sort_keys=True)
