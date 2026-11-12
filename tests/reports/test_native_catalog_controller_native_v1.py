"""Production runner -> three original worlds -> cold audits/costs, SCRIPTED IO.

Scientist HTTP, corpus and role attestations are fixtures. Native phases,
Docker controls, frozen-source reconstruction, checkpoints and losses are real
software paths. This is not an actual-Qwen actuation result.
"""
from pathlib import Path
from types import SimpleNamespace

from scripts import run_native_catalog_actuation_v1 as driver
from scripts import audit_native_catalog_actuation_v1 as audit
from scripts.reports.pre_scale_costs_v1 import analyze as costs
from scripts.reports.native_catalog_actuation_v1 import export as choice_export
from scripts.reports.native_catalog_actuation_summary_v1 import summarize
from scripts.reports.native_institution_effect_trace_v1 import export as effect_export
from scripts.reports.native_observed_request_classes_v1 import export as request_export
from tests.reports.test_native_catalog_actuation_v1 import evidence, seal
from tests.reports.test_native_capacity_full_path_v1 import install_scripted_provider
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from utopia.optimization.native_factory import LocalQwenNativeFactory
from utopia.system.design_patch import clone

IMAGE = 'sha256:c5cd0ef1703ee77e4a056f51695d2d73b17d9bf07b167763058c0802105f8833'


def test_production_run_original_checkpoint_measurement_actual_auditor_and_costs(tmp_path, fixed_corpus, monkeypatch):
    original, origin_audit, _ = evidence(tmp_path, monkeypatch, IMAGE)
    install_scripted_provider(tmp_path / 'provider', monkeypatch, 2)
    probe = LocalQwenNativeFactory(tmp_path / 'probe', tmp_path / 'cache', years=4, corpus_years=4, allow_dirty=True)
    for key in ('model', 'model_digest', 'corpus_sha256', 'dataset_identity', 'runtime_seed_binding', 'source_commit'):
        original['world'][key] = clone(getattr(probe, key))
        if key in original['scientist']: original['scientist'][key] = clone(getattr(probe, key))
    original['source_commit'] = probe.source_commit
    original['measurement_contract']['source_commit'] = probe.source_commit
    original['world']['measurement_adapter_contract'] = clone(original['measurement_contract']); seal(original)
    origin = tmp_path / 'origin'; origin.mkdir(); (origin / 'writer.lock').touch()
    p = seal(driver.build_plan(original, origin_audit, source=probe.source_commit,
        origin={'run': str(origin), 'SCRIPTED': 'origin attestation is mocked'}))
    root = tmp_path / 'run'; root.mkdir()
    driver.save(root / 'plan.json', {k: v for k, v in p.items() if k != 'content_sha256'})
    monkeypatch.setattr(driver, 'origin_evidence', lambda origin: (original, origin_audit))
    monkeypatch.setattr(driver, 'require_environment', lambda: None)
    def factory(directory, p, root):
        f = LocalQwenNativeFactory(directory, tmp_path / 'cache', years=4, corpus_years=4,
            record_wire=True, record_code=True, maximum_http_attempts=1024, allow_dirty=True,
            inference_lock=root / 'inference.lock', world_conditions=p['world']['world_conditions'],
            experiment_binding=p['experiment'])
        def make(spec, seed, run_id):
            sim = f(spec, seed, run_id); sim.llm.sim = sim; return sim
        return make
    monkeypatch.setattr(driver, 'factory_for', factory)
    driver.run(root)
    assert driver.require_plan(root) == p
    assert driver.read(root / 'terminal.json')['completed_jobs'] == 3
    def loaded(*args, **kwargs):
        return {'confirmed': True, 'SCRIPTED': 'not a real role attestation',
            'context': str(Path(args[0]).parent / 'SCRIPTED-role-context.json')}
    monkeypatch.setattr('scripts.analyze_native_design_benchmark.loaded', loaded)
    paths = [tmp_path / 'audit-one.json', tmp_path / 'audit-two.json']
    for path in paths: audit.worker(root, path)
    assert paths[0].read_bytes() == paths[1].read_bytes()
    result = driver.read(paths[0]); assert len(result['worlds']) == 3
    assert result['source_proof']['status'] == 'verified-exact-source-closure'
    for world in result['worlds']:
        assert world['status'] == 'complete'
        assert [a['period'] for a in world['annual_agendas']] == [1, 2, 3, 4]
        assert len(world['physical_proof']['annual_checkpoints']) == 4
        assert world['physical_proof']['world_conditions_proof']['fixed_annual_slot_cap'] == 1
        assert world['scores']['throughput'] is not None and world['scores']['founder-activity'] is not None
    assert result['worlds'][0]['annual_agendas'][0] == result['worlds'][1]['annual_agendas'][0]
    assert result['worlds'][1]['annual_agendas'][0] == result['worlds'][2]['annual_agendas'][0]
    projected = costs(root, p, result)
    assert len(projected['scientist']['physical_response_caches']) == 3
    assert projected['scientist']['completed_responses'] > 0
    assert not projected['auxiliary']['events'] and 'common_content_observer' not in projected
    for label, export in [('choices', choice_export), ('effects', effect_export), ('requests', request_export)]:
        paths_out = [tmp_path / (label + '-one'), tmp_path / (label + '-two')]
        for out in paths_out:
            args = SimpleNamespace(run=root, audit_one=paths[0], audit_two=paths[1], output=out,
                frozen_source=driver.ROOT, scope='catalog-actuation-controls')
            export(args)
        assert {f.name: f.read_bytes() for f in paths_out[0].iterdir()} == {
            f.name: f.read_bytes() for f in paths_out[1].iterdir()}
        report = driver.read(paths_out[0] / 'report.json')
        assert len(report['worlds']) == 3
        if label == 'choices':
            summary = summarize(report)
            assert len(summary['annual_project_states']) == 60
            assert len(summary['founder_ids']) == 5
            assert report['worlds'][0]['direction_requests']
            assert not report['worlds'][2]['direction_requests']
            assert report['worlds'][2]['catalog_project_effects']
            assert all(r['literal_instruction_present'] for r in report['worlds'][1]['direction_requests'])
