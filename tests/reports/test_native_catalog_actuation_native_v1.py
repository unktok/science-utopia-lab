"""Three original four-year worlds, SCRIPTED scientist HTTP/corpus, real Docker.

This verifies the actual planning consumer, native law/measurement and cold
proof path, not local-model policy performance or automatic invention.
"""
from copy import deepcopy
import json
from pathlib import Path

import pytest

from tests.optimization.test_native_factory import capacity_conditions
from tests.reports.test_native_capacity_full_path_v1 import install_scripted_provider
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from utopia.optimization.native_active_founders import measure, measure_from_checkpoints
from utopia.optimization.native_benchmark_controls import selection_control
from utopia.optimization.native_factory import LocalQwenNativeFactory
from utopia.optimization.native_fixed_production_domain import allow_review_routing, allow_catalog_planning
from utopia.optimization.native_design_space import require_candidate_in_space
from utopia.optimization.native_world import measure_native_world
from utopia.runtime.checkpointing import read_portable_checkpoint
from utopia.system.native_capacity_controls import capacity_allocation_control
from utopia.system.native_catalog_planning import ACTION, EVENT, PROTOCOL, catalog_agenda_control
from utopia.system.native_information_institution import information_system, information_design_space
from utopia.utils.data_utils import file_sha256

IMAGE = 'sha256:c5cd0ef1703ee77e4a056f51695d2d73b17d9bf07b167763058c0802105f8833'


def test_three_actual_native_consumers_cold_catalog_proof_and_original_capacity(tmp_path, fixed_corpus, monkeypatch):
    calls = install_scripted_provider(tmp_path / 'provider', monkeypatch, 2)
    conditions = capacity_conditions(papers_per_project=2)
    experiment = {'protocol': 'SCRIPTED-native-catalog-actuation-full-path-v1'}
    factory = LocalQwenNativeFactory(tmp_path / 'runs', tmp_path / 'cache', years=4, corpus_years=4,
        record_wire=True, record_code=True, maximum_http_attempts=1024,
        inference_lock=tmp_path / 'inference.lock', allow_dirty=True,
        world_conditions=conditions, experiment_binding=experiment)
    anchor = capacity_allocation_control(
        selection_control(information_system(IMAGE, seed=61001), rule='accept-all'), IMAGE, rule='reserve-proximity')
    domain = allow_catalog_planning(anchor, allow_review_routing(anchor,
        information_design_space(anchor, 'code-and-graph', fixed_production=True)))
    agendas = []
    for mode in ('cut', 'information', 'project'):
        spec = catalog_agenda_control(anchor, IMAGE, actuation=mode)
        require_candidate_in_space(anchor, spec, domain)
        identity = 'SCRIPTED-catalog-' + mode
        sim = factory(spec, 61001, identity); sim.llm.sim = sim
        before_calls = len(calls)
        try:
            sim.run()
            assert len(sim.yearly_results) == 4 and sim.papers_per_project == 2
            assert all(b['total_slots'] == 1 for r in sim.yearly_results
                       if (b := r.get('funding_budget')))
            sim.resource_ledger.reconcile(4, sim.ecosystem.agent_population, require_closed=True)
            base = measure_native_world(sim, run_id=identity)
            measured = measure(sim, base)
            checkpoint = Path(sim.output_dir) / 'portable_checkpoint_year_4.json.gz'
            evidence = {'run_id': identity, 'seed': 61001, 'system_fingerprint': spec.fingerprint,
                'checkpoint_path': str(checkpoint), 'checkpoint_sha256': file_sha256(checkpoint),
                'event_stream_hash': sim.native_system.to_dict()['event_stream_hash']}
            world = {k: getattr(factory, k) for k in (
                'model', 'model_digest', 'source_commit', 'corpus_sha256', 'runtime_seed_binding')}
            world.update(experiment=experiment, world_conditions=conditions, image_id=IMAGE)
            from scripts.native_benchmark_physical import physical_proof
            proof = physical_proof(tmp_path / 'runs' / identity, spec, world=world, seed=61001, years=4, evidence=evidence)
            assert proof['status'] == 'complete' and proof['measurement'] == base
            paths = [checkpoint.parent / f'portable_checkpoint_year_{year}.json.gz' for year in range(5)]
            assert measure_from_checkpoints(base, paths) == measured
            assert proof['world_conditions_proof']['fixed_annual_slot_cap'] == 1
            effects = [e for e in sim.native_system.events if e.event_type == EVENT]
            projects = proof['native_counts']['project_assignments_verified']
            assert len(effects) == len(projects)
            assert bool(effects) == (mode == 'project')
            assert all('catalog_validation' in row for row in projects)
            rows = [json.loads(line) for line in (tmp_path / 'runs' / identity / 'code-contexts.jsonl').read_text().splitlines()]
            producer = [r for r in rows if r['artifact']['source'] ==
                next(n for n in spec.mechanisms if n.mechanism_id == 'developer-catalog-agenda').parameters['code_artifact']['source']]
            assert len(producer) == 4
            agendas.append(producer[0]['result']['outputs']['agenda'])
            direction_calls = [(ctx, payload) for (ctx, _, _), payload in calls[before_calls:]
                               if ctx[0] == 'phase1_directions']
            if mode == 'project':
                assert not direction_calls  # Actual institution assignment, not simulated LLM obedience.
                assert proof['native_counts']['actions'][ACTION] == len(projects)
                for event in effects:
                    p = event.payload; before = p['eligible_actor_before']; assignment = p['assignment']
                    assert before['project_end_year'] < event.year
                    assert assignment['project_start_year'] == event.year
                    assert assignment['project_end_year'] == event.year + assignment['direction']['years'] - 1
                # Exercise the actual new cold-reader rejection, not only the
                # simulator's original runtime validation.
                from scripts.analyze_native_open_v7 import domain_proofs
                corrupted = deepcopy(read_portable_checkpoint(checkpoint))
                bad = next(e for e in corrupted['native_system']['events'] if e['event_type'] == EVENT)
                bad['payload']['catalog_sha256'] = '0' * 64
                with pytest.raises(ValueError, match='catalog validation'):
                    domain_proofs(corrupted, sim.native_system)
            else:
                assert direction_calls
                delivered = [payload for _, payload in direction_calls if PROTOCOL in json.dumps(payload)]
                assert bool(delivered) == (mode == 'information')
        finally:
            sim.llm.response_cache.close()
    assert agendas[0] == agendas[1] == agendas[2]  # Exact common pre-treatment agenda.
