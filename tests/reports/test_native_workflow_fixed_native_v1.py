"""Committed-source native handoff, deferred until the hardware window.

Uses the existing seven-world SCRIPTED development proof, then the actual
selection-fixed evaluator, role/transport factory and double cold readers.
HTTP/corpus/upstream origin remain fixtures; no real model or scientific seed.
"""
import json
from pathlib import Path
import tempfile
import subprocess
import sys
from types import SimpleNamespace
import pytest

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
from utopia.system.design_patch import digest


@pytest.mark.parametrize('designer_profile', ['legacy', development.FEEDBACK_MODE, development.staged_author.MODE])
def test_real_native_workflow_handoff_known_null_and_double_cold_readers(tmp_path, fixed_corpus, monkeypatch,
        designer_profile, software_fixtures=False):
    prior = tmp_path / 'development'
    development_check(prior, fixed_corpus, monkeypatch, 'independent-numeric-v2', 'read900', designer_profile)
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
    policy = None; inventory_roots = [old_root]
    if software_fixtures:
        inventory_root = tmp_path / 'SCRIPTED-seed-inventory'
        inventory_root.mkdir(); file = inventory_root / 'responses.sqlite'
        file.write_bytes(b'SCRIPTED cache primitive')
        source_file = Path(__file__).resolve()
        policy = {'schema': 'scienceutopia.seed-software-fixture-policy.v1',
            'files': [{'root': str(inventory_root.resolve()), 'path': 'responses.sqlite',
                'file_sha256': file_sha256(file), 'reason': 'Explicit SCRIPTED non-production cache'}],
            'reviewed_fixture_sources': {str(source_file.relative_to(driver.ROOT)): file_sha256(source_file)}}
        policy['content_sha256'] = digest(policy)
        inventory_roots.append(inventory_root)
    usages = [usage_inventory(path, seeds, **({} if policy is None else {'software_exclusions': policy}))
        for path in inventory_roots]
    p = driver.build_plan(old_plan, old_audit, source=original['source_commit'], origin=origin,
        usages=usages, seeds=seeds, observer_backend=original['observer_contract']['backend'],
        source_proof=development.native_sources(original['source_commit']), software_exclusions=policy)
    root = tmp_path / 'evaluation'; root.mkdir()
    for i, usage in enumerate(usages):
        driver.save(root / f'seed-usage-{i:02}.json', {k: v for k, v in usage.items() if k != 'content_sha256'})
    driver.save(root / 'plan.json', p); p = driver.require_plan(root)
    expected_jobs = 3 if designer_profile in (development.OPEN_IR_MODE, development.staged_author.MODE) else 2
    assert len(p['jobs']) == expected_jobs  # Exact submitted policies alone share actual identities.
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
    assert end['status'] == 'closed' and end['completed_jobs'] == expected_jobs
    assert len(invoked) == expected_jobs
    assert len(list(root.rglob('scientist-transport.json'))) == expected_jobs
    external = Path(tempfile.mkdtemp(prefix='science-utopia-workflow-fixed-cold-', dir='/private/tmp'))
    audit_paths = [external / 'audit-one.json', external / 'audit-two.json']; before = _inventory(root)
    for path in audit_paths: auditor.worker(root, path)
    assert audit_paths[0].read_bytes() == audit_paths[1].read_bytes()
    proof = driver.read(audit_paths[0])
    assert [w['status'] for w in proof['worlds']] == ['failed'] + ['complete'] * (expected_jobs - 1)
    assert all(len(w['physical_proof']['annual_checkpoints']) == 4 for w in proof['worlds'])
    assert proof['fixed_selection'] == old_audit['selection']
    cost_reports = [costs(root, p, driver.read(path)) for path in audit_paths]
    assert cost_reports[0] == cost_reports[1]
    common_cost = cost_reports[0]['common_content_observer']
    assert common_cost['input_observer_audit_content_sha256'] == proof['observer']['content_sha256']
    assert common_cost['physical_requests'] == proof['observer']['dispatch_intents']
    assert common_cost['usage'] == proof['observer']['usage']
    assert not any(e['kind'] in ('workflow-readiness', 'workflow-proposal','editor-readiness','staged-proposal')
        for e in cost_reports[0]['auxiliary']['events'])
    for i in (1, 2):
        export(SimpleNamespace(run=root, audit_one=audit_paths[0], audit_two=audit_paths[1],
            output=external / ('report-' + str(i))))
    report_files = same_files(external / 'report-1', external / 'report-2')
    report = driver.read(external / 'report-1/report.json')
    assert len(report['logical_rows']) == 4 and len(report['paired_differences']) == 4
    assert len(report['objective_choice_differences']) == 1
    readout_files = {}
    for name, extra in (
            ('native_institution_effect_trace_v1', ('--frozen-source', str(driver.ROOT), '--scope', 'workflow-fixed-evaluation')),
            ('native_planning_choice_trace_v1', ('--frozen-source', str(driver.ROOT), '--study', 'workflow-fixed-evaluation')),
            ('native_observed_request_classes_v1', ())):
        for i in (1, 2):
            subprocess.run([sys.executable, '-m', 'scripts.reports.' + name,
                '--run', str(root), '--audit-one', str(audit_paths[0]), '--audit-two', str(audit_paths[1]),
                '--output', str(external / (name + '-' + str(i))), *extra], cwd=driver.ROOT,
                check=True, capture_output=True, text=True, timeout=1800)
        readout_files[name] = same_files(external / (name + '-1'), external / (name + '-2'))
        assert len(driver.read(external / (name + '-1') / 'report.json')['worlds']) == expected_jobs
    assert _inventory(root) == before
    write_json_atomic(tmp_path / 'verification.json', {
        'schema': 'scienceutopia.native-workflow-fixed-software-check.v1',
        'classification': 'SCRIPTED-HTTP-corpus-and-upstream-origin-not-scientific-evaluation',
        'source_commit': p['source_commit'], 'new_model_calls': 0,
        'designer_profile': designer_profile, 'explicit_software_fixture_policy': software_fixtures,
        'development_native_software_worlds': 7, 'additional_native_software_worlds': expected_jobs,
        'additional_annual_checkpoints': 4 * expected_jobs, 'transport_application_records': expected_jobs,
        'active_authored_scientist_input_change': verification.get('active_authored_scientist_input_change'),
        'known_nulls_preserved': 1, 'fixed_selection_unchanged': True,
        'original_cold_audit_directory': str(external),
        'matching_audit_sha256': file_sha256(audit_paths[0]),
        'matching_cost_content_sha256': cost_reports[0]['content_sha256'],
        'common_observer_physical_requests': common_cost['physical_requests'],
        'common_observer_cost_bound_to_original_audit': True,
        'matching_report_files': report_files, 'scientific_gain_claimed': False,
        'matching_mechanism_readout_files': readout_files,
        'publication_ready': False}, sort_keys=True)


def test_explicit_seed_software_policy_native_handoff_and_cold_audits(tmp_path, fixed_corpus, monkeypatch):
    test_real_native_workflow_handoff_known_null_and_double_cold_readers(tmp_path, fixed_corpus, monkeypatch,
        development.FEEDBACK_MODE, software_fixtures=True)


def test_open_institution_native_active_consumer_and_fixed_handoff(tmp_path, fixed_corpus, monkeypatch):
    test_real_native_workflow_handoff_known_null_and_double_cold_readers(tmp_path, fixed_corpus, monkeypatch,
        development.OPEN_IR_MODE)
