"""Opt-in real native/Docker/SDK public-function software proof, not science.

Never run alongside real inference. HTTP, corpus, upstream history, child/exit
supervision and closure orchestration metadata are SCRIPTED. Scientific seeds
83003/83011 are not used: explicit software-only43003/43011 monkeypatch the two
in-process drivers/readers, as the upstream fixture uses42. Outer subprocess
CLI/import routing is not established by these in-process public API calls.
All native raw/cold/readout artifacts persist on failure; no temporary teardown.
"""
import json
import os
from pathlib import Path
from types import SimpleNamespace

from openai import OpenAI
import pytest

from scripts import run_native_priority_fixed_evaluation_v1 as driver
from scripts import run_native_objective_fixed_evaluation_v1 as shared
from scripts import audit_native_priority_fixed_evaluation_v1 as auditor
from scripts.analyze_native_open_v7 import _inventory
from scripts.finish_native_institution_loop_v1 import same_files
from scripts.reports import native_priority_method_readout_v1 as development_readout
from scripts.reports import native_priority_fixed_evaluation_v1 as evaluation_readout
from scripts.reports.pre_scale_costs_v1 import analyze as costs
from tests.reports.test_native_priority_method_public_v1 import public_mixed_operator_path
from tests.reports.test_native_legacy_choice_native_v1 import ScriptedCritic
from tests.runtime.test_portable_checkpoint_integration import fixed_corpus
from utopia.system import code_mechanisms
from utopia.system.design_patch import clone
from utopia.utils.data_utils import file_sha256, write_json_atomic

SOFTWARE_SEEDS = [43003, 43011]


@pytest.mark.skipif(os.environ.get('SCIENCE_UTOPIA_PRIORITY_FIXED_PUBLIC_QA') != '1',
                   reason='explicit clean-source hardware window, no real inference active')
def test_public_frozen_bank_prepare_native_run_cold_cost_and_paired_all_label_readouts(
        tmp_path, fixed_corpus, monkeypatch):
    if not os.environ.get('SCIENCE_UTOPIA_WORKFLOW_PLAN'):
        pytest.skip('explicit original world/provider/loss binding required')
    declared = os.environ.get('SCIENCE_UTOPIA_PRIORITY_FIXED_QA_EXTERNAL')
    if not declared:
        pytest.skip('explicit unused external output for retained native/cold/readout artifacts required')
    external = Path(declared).resolve()
    if (external.exists() or external.is_relative_to(driver.ROOT.resolve())
            or external.is_relative_to(tmp_path.resolve())):
        raise ValueError('fresh external output outside source/test raw required before any native QA')
    external.mkdir(parents=True)
    write_json_atomic(tmp_path / 'external-locations.json', {'external': str(external),
        'classification': 'SCRIPTED-software-only-not-scientific-evaluation',
        'software_seeds': SOFTWARE_SEEDS, 'scientific_reserved_seeds_consumed': False,
        'automatic_cleanup': False}, sort_keys=True)
    development = tmp_path / 'development'; development.mkdir()
    stage = 'development-public-path'
    try:
        evidence = public_mixed_operator_path(development, fixed_corpus, monkeypatch,
            closure_output=external / 'development-analysis')
        root, original, analysis = evidence['run'], evidence['plan'], evidence['closure']
        # These are declared orchestration fixtures, not a real PID/supervisor
        # closure test. The actual two native cold/cost files above are retained.
        write_json_atomic(analysis / 'started.json', {'schema': 'scienceutopia.native-priority-method-comparison.v1.finish',
            'scientific_source_commit': original['source_commit'],
            'plan_file_sha256': file_sha256(root / 'plan.json'), 'SCRIPTED': 'orchestration metadata only'}, sort_keys=True)
        write_json_atomic(analysis / 'ended.json', {'status': 'closed',
            'audit_file_sha256': file_sha256(analysis / 'audit-1.json'),
            'cost_file_sha256': file_sha256(analysis / 'costs-1.json'), 'new_model_calls': 0,
            'new_native_worlds': 0, 'SCRIPTED': 'orchestration metadata only'}, sort_keys=True)
        reports = external / 'development-readouts'; reports.mkdir()
        driver.save(reports / 'started.json', {
            'schema': 'scienceutopia.native-priority-method-comparison.v1.readout.finish',
            'scientific_source_commit': original['source_commit'], 'analysis_source_commit': original['source_commit'],
            'plan_file_sha256': file_sha256(root / 'plan.json'), 'preceding_analysis': str(analysis),
            'SCRIPTED': 'orchestration metadata only'})
        stage = 'development-readouts'
        for i in (1, 2):
            development_readout.export(SimpleNamespace(run=root, frozen_source=driver.ROOT,
                audit_one=analysis / 'audit-1.json', audit_two=analysis / 'audit-2.json',
                cost_one=analysis / 'costs-1.json', cost_two=analysis / 'costs-2.json',
                output=reports / ('report-' + str(i))))
        driver.save(reports / 'ended.json', {'status': 'closed', 'new_model_calls': 0, 'new_native_worlds': 0,
            'report_files': same_files(reports / 'report-1', reports / 'report-2'),
            'SCRIPTED': 'orchestration metadata only'})
        # Explicit test-only condition substitution; no production protocol,
        # actual scientific plan, reserved seed or running process is changed.
        monkeypatch.setattr(driver, 'SEEDS', clone(SOFTWARE_SEEDS))
        monkeypatch.setattr(evaluation_readout, 'SEEDS', clone(SOFTWARE_SEEDS))
        monkeypatch.setattr(shared, 'LocalObserverBackend', lambda **kw: ScriptedCritic())
        target = external / 'evaluation-raw'; stage = 'evaluation-public-prepare'
        before_posts = len(evidence['upstream']['scientist_requests'])
        driver.prepare(SimpleNamespace(output=target, origin_run=root, origin_source=driver.ROOT,
            origin_analysis=analysis, origin_readouts=reports, seed_usage_root=[tmp_path, external],
            seed_software_exclusions=None))
        p = driver.require_plan(target)
        assert p['evaluation']['seeds'] == SOFTWARE_SEEDS and p['evaluation']['logical_policy_labels'] == 15
        assert all(driver.read(target / ('seed-usage-' + str(i).zfill(2) + '.json'))['strict_path_coverage']
            for i in range(len(p['evaluation']['seed_usage'])))
        assert p['budget']['designer_generation_POSTs'] == 0
        stage = 'evaluation-public-run'; driver.run(target)
        end = driver.read(target / 'terminal.json')
        assert end['status'] == 'closed' and end['completed_jobs'] == len(p['jobs'])
        assert 2 <= len(p['jobs']) <= 30
        new_requests = evidence['upstream']['scientist_requests'][before_posts:]
        assert new_requests and all(v['read_header'] == '900' and v['retry_header'] == '0' for v in new_requests)
        for client in evidence['upstream']['clients']: client.close()
        before = _inventory(target); posts = len(evidence['upstream']['scientist_requests'])
        def forbidden(*a, **kw): pytest.fail('cold/readout cannot construct a model/client or execute source')
        monkeypatch.setattr(OpenAI, '__init__', forbidden)
        monkeypatch.setattr(code_mechanisms.DockerCodeExecutor, 'execute', forbidden)
        audits = external / 'evaluation-analysis'; audits.mkdir(); stage = 'evaluation-paired-cold-cost'
        for i in (1, 2):
            path = audits / ('audit-' + str(i) + '.json'); auditor.worker(target, path)
            value = costs(target, p, driver.read(path))
            assert driver.save(audits / ('costs-' + str(i) + '.json'),
                {k: v for k, v in value.items() if k != 'content_sha256'}) == value
        assert (audits / 'audit-1.json').read_bytes() == (audits / 'audit-2.json').read_bytes()
        assert (audits / 'costs-1.json').read_bytes() == (audits / 'costs-2.json').read_bytes()
        cold = driver.read(audits / 'audit-1.json')
        assert all(w['status'] == 'complete' and w['loaded']['confirmed'] for w in cold['worlds'])
        assert cold['fixed_selection'] == p['fixed_selection']
        readouts = external / 'evaluation-readouts'; readouts.mkdir(); stage = 'evaluation-paired-readouts'
        for i in (1, 2):
            evaluation_readout.export(SimpleNamespace(run=target, frozen_source=driver.ROOT,
                audit_one=audits / 'audit-1.json', audit_two=audits / 'audit-2.json',
                cost_one=audits / 'costs-1.json', cost_two=audits / 'costs-2.json',
                output=readouts / ('report-' + str(i))))
        matching = same_files(readouts / 'report-1', readouts / 'report-2')
        assert len(matching) == 4
        report = driver.read(readouts / 'report-1/report.json')
        assert len(report['logical_rows']) == 30 and len(report['fixed_policy_contrasts']) == 108
        assert report['coverage']['physical_worlds'] == len(p['jobs'])
        assert before == _inventory(target) and posts == len(evidence['upstream']['scientist_requests'])
        with pytest.raises(ValueError, match='no redispatch'): driver.run(target)
        write_json_atomic(external / 'verification.json', {'schema': 'scienceutopia.native-priority-fixed-public-software.v1',
            'source_commit': p['source_commit'], 'classification': 'SCRIPTED-HTTP-corpus-history-supervision-and-orchestration',
            'software_seed_override': SOFTWARE_SEEDS, 'scientific_reserved_seeds_consumed': False,
            'development_native_worlds': 27, 'upstream_native_worlds': 2, 'evaluation_native_worlds': len(p['jobs']),
            'evaluation_scientist_SDK_POSTs': len(new_requests), 'logical_policy_labels': 15, 'logical_rows': 30,
            'paired_rows': 108, 'matching_readout_files': matching, 'new_real_model_calls': 0,
            'outer_subprocess_CLI_routing_tested': False, 'visual_review_complete': False,
            'scientific_gain_or_publication_readiness_claimed': False}, sort_keys=True)
    except BaseException as error:
        write_json_atomic(external / 'stopped.json', {'stage': stage, 'error_type': type(error).__name__,
            'error': str(error), 'native_raw_and_external_artifacts_preserved': True,
            'new_real_model_calls': 0, 'science_restarted': False}, sort_keys=True)
        raise
