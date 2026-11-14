"""Committed-source native handoff, deferred until the hardware window.

Uses the existing seven-world SCRIPTED development proof, then the actual
selection-fixed evaluator, role/transport factory and double cold readers.
HTTP/corpus/upstream origin remain fixtures; no real model or scientific seed.
"""
import json
from pathlib import Path
import tempfile
from types import SimpleNamespace

from scripts import run_native_workflow_objective_loop_v1 as development
from scripts import run_native_workflow_fixed_evaluation_v1 as driver
from scripts import run_native_objective_fixed_evaluation_v1 as common
from scripts import audit_native_workflow_fixed_evaluation_v1 as auditor
from scripts.analyze_native_open_v7 import _inventory
from scripts.finish_native_institution_loop_v1 import same_files
from scripts.native_benchmark_seed_usage import usage_inventory
from scripts.reports.native_workflow_fixed_evaluation_v1 import export
from scripts.reports.pre_scale_costs_v1 import analyze as costs
from tests.reports.test_native_workflow_objective_loop_native_v1 import (
    test_bounded_workflow_designer_seven_native_worlds_known_null_and_double_cold_audit as development_check)
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from utopia.utils.data_utils import file_sha256, write_json_atomic


def test_real_native_workflow_handoff_known_null_and_double_cold_readers(tmp_path, fixed_corpus, monkeypatch):
    prior = tmp_path / 'development'
    development_check(prior, fixed_corpus, monkeypatch, 'independent-numeric-v2', 'read900')
    old_root = prior / 'run'; original = development.read(old_root / 'plan.json')
    verification = json.loads((prior / 'verification.json').read_text())
    old_audits = [Path(verification['original_cold_audit_directory']) / name
        for name in ('audit-one.json', 'audit-two.json')]
    origin = {'run': str(old_root), 'source': str(driver.ROOT), 'source_commit': original['source_commit'],
        'audit_files': {str(path): file_sha256(path) for path in old_audits}}
    # The handoff itself uses actual normal closure/inventory/selection checks,
    # not a richer mock certificate or fabricated development audit.
    old_plan, old_audit = driver.origin_evidence(origin)
    seeds = [72101]  # SCRIPTED software fixture, not a chosen scientific seed.
    usage = usage_inventory(old_root, seeds)
    p = driver.build_plan(old_plan, old_audit, source=original['source_commit'], origin=origin,
        usages=[usage], seeds=seeds, observer_backend=original['observer_contract']['backend'],
        source_proof=development.native_sources(original['source_commit']))
    root = tmp_path / 'evaluation'; root.mkdir()
    driver.save(root / 'seed-usage-00.json', {k: v for k, v in usage.items() if k != 'content_sha256'})
    driver.save(root / 'plan.json', p); p = driver.require_plan(root)
    assert len(p['jobs']) == 2  # Two controls; exact submitted policies share their actual identities.
    monkeypatch.setattr(common, 'LocalObserverBackend', development.LocalObserverBackend)
    real_measure = driver.measure_with; invoked = []
    def measured(observer, contract):
        ordinary = real_measure(observer, contract)
        def apply(sim, base):
            value = ordinary(sim, base); invoked.append(sim.native_system.spec.fingerprint)
            if len(invoked) == 1:
                raise ValueError('SCRIPTED known measurement failure after original native completion')
            return value
        return apply
    monkeypatch.setattr(driver, 'measure_with', measured)
    driver.run(root)
    end = driver.read(root / 'terminal.json')
    assert end['status'] == 'closed' and end['completed_jobs'] == 2
    assert len(invoked) == 2
    assert len(list(root.rglob('scientist-transport.json'))) == 2
    external = Path(tempfile.mkdtemp(prefix='science-utopia-workflow-fixed-cold-', dir='/private/tmp'))
    audit_paths = [external / 'audit-one.json', external / 'audit-two.json']; before = _inventory(root)
    for path in audit_paths: auditor.worker(root, path)
    assert audit_paths[0].read_bytes() == audit_paths[1].read_bytes()
    proof = driver.read(audit_paths[0])
    assert [w['status'] for w in proof['worlds']] == ['failed', 'complete']
    assert all(len(w['physical_proof']['annual_checkpoints']) == 4 for w in proof['worlds'])
    assert proof['fixed_selection'] == old_audit['selection']
    cost_reports = [costs(root, p, driver.read(path)) for path in audit_paths]
    assert cost_reports[0] == cost_reports[1]
    assert not any(e['kind'] in ('workflow-readiness', 'workflow-proposal')
        for e in cost_reports[0]['auxiliary']['events'])
    for i in (1, 2):
        export(SimpleNamespace(run=root, audit_one=audit_paths[0], audit_two=audit_paths[1],
            output=external / ('report-' + str(i))))
    report_files = same_files(external / 'report-1', external / 'report-2')
    report = driver.read(external / 'report-1/report.json')
    assert len(report['logical_rows']) == 4 and len(report['paired_differences']) == 4
    assert len(report['objective_choice_differences']) == 1
    assert _inventory(root) == before
    write_json_atomic(tmp_path / 'verification.json', {
        'schema': 'scienceutopia.native-workflow-fixed-software-check.v1',
        'classification': 'SCRIPTED-HTTP-corpus-and-upstream-origin-not-scientific-evaluation',
        'source_commit': p['source_commit'], 'new_model_calls': 0,
        'development_native_software_worlds': 7, 'additional_native_software_worlds': 2,
        'additional_annual_checkpoints': 8, 'transport_application_records': 2,
        'known_nulls_preserved': 1, 'fixed_selection_unchanged': True,
        'original_cold_audit_directory': str(external),
        'matching_audit_sha256': file_sha256(audit_paths[0]),
        'matching_cost_content_sha256': cost_reports[0]['content_sha256'],
        'matching_report_files': report_files, 'scientific_gain_claimed': False,
        'publication_ready': False}, sort_keys=True)
