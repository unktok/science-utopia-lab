"""Light SCRIPTED handoff/runner/report checks, no native or model execution."""
import json
from types import SimpleNamespace

import pytest

from scripts import run_native_workflow_fixed_evaluation_v1 as driver
from scripts import run_native_objective_fixed_evaluation_v1 as common
from scripts.reports import native_objective_fixed_evaluation_v1 as report
from tests.reports.test_native_workflow_objective_loop_v1 import setup as workflow_plan
from tests.reports.test_native_planning_objective_loop_v1 import seal
from tests.reports.test_native_capacity_fixed_evaluation_v1 import usage
from utopia.optimization.common_content_observer import CommonContentObserver, ObserverCompletionUnknown
from utopia.system.design_patch import clone


def evidence(tmp_path, monkeypatch, *, all_null=False, transport=False, both=False, image_override=None):
    original, _, _, sources = workflow_plan(tmp_path, monkeypatch, image_override=image_override)
    # The new handoff compares against the workflow source, not the planning
    # source used to construct this explicitly SCRIPTED upstream fixture.
    sources = {**sources, 'original_source': original['source_commit']}
    if transport:
        from utopia.optimization.native_scientist_transport_v1 import contract, PROTOCOL
        from utopia.utils.data_utils import file_sha256
        original['scientist_transport'] = contract(read_seconds=900)
        original['operational_protocol'] = {'path': PROTOCOL, 'sha256': file_sha256(driver.ROOT / PROTOCOL)}
    seal(original)
    system = clone(original['initial_system'])
    worlds = [] if all_null else [
        {'identity': 'SCRIPTED-first', 'role': 'workflow-own-proposal', 'objective': 'throughput',
            'status': 'complete', 'system': clone(system), 'scores': {'throughput': -2., 'content-utility': -1.}},
        {'identity': 'SCRIPTED-second', 'role': 'workflow-own-proposal', 'objective': 'throughput',
            'status': 'complete', 'system': clone(system), 'scores': {'throughput': -2., 'content-utility': -1.}}]
    null = {'loss': None, 'all_tied_ids': [], 'selected_id': None, 'system': None}
    selected = seal({'schema': 'scienceutopia.native-workflow-objective-loop.v1.selection',
        'plan_sha256': original['content_sha256'], 'baseline_fallback': False, 'held_out_evaluation': False,
        'selected': {'throughput': clone(null) if all_null else {'loss': -2.,
            'all_tied_ids': ['SCRIPTED-first', 'SCRIPTED-second'], 'selected_id': 'SCRIPTED-first', 'system': system},
            'content-utility': clone(null)}})
    if both:
        assert not all_null
        system_u = clone(original['reference_systems']['post-funding-cost'])
        worlds.append({'identity': 'SCRIPTED-u', 'role': 'workflow-own-proposal', 'objective': 'content-utility',
            'status': 'complete', 'system': system_u, 'scores': {'throughput': -3., 'content-utility': -2.}})
        selected['selected']['content-utility'] = {'loss': -2., 'all_tied_ids': ['SCRIPTED-u'],
            'selected_id': 'SCRIPTED-u', 'system': clone(system_u)}
        seal(selected)
    audit = seal({'schema': 'scienceutopia.native-workflow-objective-loop-audit.v1',
        'source_commit': original['source_commit'], 'plan_sha256': original['content_sha256'],
        'closure': {'terminal': {'status': 'closed', 'consumed_slots': 6}},
        'source_proof': {'status': 'verified-exact-source-closure'}, 'selection': selected,
        'worlds': worlds, 'new_model_calls': 0, 'new_code_executions': 0, 'held_out_evaluation': False,
        'SCRIPTED': 'not a real closed study/source attestation'})
    seeds = [72101, 72107]; usages = [usage(seeds)]
    p = driver.build_plan(original, audit, source='e' * 40, origin={}, usages=usages, seeds=seeds,
        observer_backend=original['observer_contract']['backend'], source_proof=sources)
    return original, audit, seal(p), usages, sources


@pytest.mark.parametrize('transport', [False, True])
@pytest.mark.parametrize('all_null', [False, True])
def test_literal_selected_ties_nulls_seed_only_changes_and_transport(tmp_path, monkeypatch, transport, all_null):
    original, audit, p, _, _ = evidence(tmp_path, monkeypatch, all_null=all_null, transport=transport)
    assert p['fixed_selection'] == audit['selection']
    assert 'completed_submissions' not in p['fixed_selection']['selected']['throughput']
    assert p['evaluation']['maximum_physical_worlds'] == 8 and len(p['jobs']) == 4
    assert p['budget']['designer_generation_POSTs'] == 0 and not p['budget']['replace_failed_slots']
    assert p['world']['world_conditions'] == original['world']['world_conditions']
    assert p['losses'] == original['losses']
    for job in p['jobs']:
        assert job['system']['initial_state']['seed'] == job['seed']
        assert job['seed'] not in (61001,)
        assert ('selected:throughput' in job['labels']) == (not all_null and 'reference:R7-original' in job['labels'])
        assert 'selected:content-utility' not in job['labels']
    assert ('scientist_transport' in p) == transport
    if transport:
        assert p['scientist_transport'] == original['scientist_transport']
        assert p['operational_protocol'] == original['operational_protocol']
    # Saving sorted JSON cannot alter dispatch order or shared-label order.
    assert common.jobs_for(json.loads(json.dumps(p, sort_keys=True))) == p['jobs']


@pytest.mark.parametrize('change', ['stopped', 'slots', 'source', 'tie', 'system', 'judge',
    'used', 'errors', 'empty', 'four', 'bool', 'development', 'duplicate', 'negative', 'graph'])
def test_changed_origin_policy_observer_or_unused_scope_rejected(tmp_path, monkeypatch, change):
    original, audit, p, usages, sources = evidence(tmp_path, monkeypatch)
    seeds = p['evaluation']['seeds']; backend = original['observer_contract']['backend']
    if change == 'stopped': audit['closure']['terminal']['status'] = 'stopped'
    elif change == 'slots': audit['closure']['terminal']['consumed_slots'] = 5
    elif change == 'source': sources['original_source'] = 'f' * 40
    elif change == 'tie': audit['selection']['selected']['throughput']['all_tied_ids'].pop()
    elif change == 'system': audit['selection']['selected']['throughput']['system']['initial_state']['SCRIPTED'] = True
    elif change == 'judge': backend = {**backend, 'ollama_version': 'SCRIPTED changed'}
    elif change == 'used': usages[0]['prior_matching_runs'] = [{'SCRIPTED': True}]
    elif change == 'errors': usages[0]['errors'] = ['SCRIPTED unknown journal']
    elif change == 'empty': seeds = []
    elif change == 'four': seeds = [72101, 72103, 72107, 72109]
    elif change == 'bool': seeds = [True]
    elif change == 'development': seeds = [61001]
    elif change == 'duplicate': seeds = [72101, 72101]
    elif change == 'negative': seeds = [-1]
    else: original['reference_systems']['post-funding-cost']['connections'] = []
    seal(audit['selection']); seal(audit); seal(original)
    audit['plan_sha256'] = original['content_sha256']; audit['selection']['plan_sha256'] = original['content_sha256']
    seal(audit['selection']); seal(audit)
    usages[0]['seeds'] = seeds; seal(usages[0])
    with pytest.raises(ValueError):
        driver.build_plan(original, audit, source='e' * 40, origin={}, usages=usages, seeds=seeds,
            observer_backend=backend, source_proof=sources)


def runner(tmp_path, monkeypatch):
    _, _, p, usages, _ = evidence(tmp_path / 'input', monkeypatch)
    root = tmp_path / 'run'; root.mkdir(); origin = tmp_path / 'origin'; origin.mkdir()
    (origin / 'writer.lock').touch(); inventory = tmp_path / 'inventory'; inventory.mkdir()
    u = usages[0]; u['root'] = str(inventory); seal(u)
    p['origin'] = {'run': str(origin)}; p['evaluation']['seed_usage'] = [u['content_sha256']]; seal(p)
    driver.save(root / 'plan.json', {k: v for k, v in p.items() if k != 'content_sha256'})
    driver.save(root / 'seed-usage-00.json', {k: v for k, v in u.items() if k != 'content_sha256'})
    monkeypatch.setattr(driver, 'require_plan', lambda root: p)
    monkeypatch.setattr(common, 'require_environment', lambda: None)
    monkeypatch.setattr(common, 'usage_inventory', lambda *args: u)
    monkeypatch.setattr(common, 'LocalObserverBackend', lambda **kwargs: None)
    return root, p, u


def test_all_jobs_and_known_nulls_close_once_in_new_schema(tmp_path, monkeypatch):
    root, p, _ = runner(tmp_path, monkeypatch); calls = []
    def observed(root, plan, job, observer):
        calls.append(clone(job))
        driver.save(root / 'evaluation' / job['identity'] / 'observation.json',
            {'status': 'failed' if len(calls) == 1 else 'complete', 'SCRIPTED': 'not native results'})
    monkeypatch.setattr(driver, 'observe', observed)
    driver.run(root)
    assert calls == p['jobs']
    end = driver.read(root / 'terminal.json')
    assert end['status'] == 'closed' and end['completed_jobs'] == 4 and end['schema'] == driver.SCHEMA + '.terminal'
    assert driver.read(root / 'started.json')['schema'] == driver.SCHEMA + '.start'
    assert driver.read(root / 'observer-audit.json') == CommonContentObserver(root / 'observer', p['observer_contract'], backend=None).audit()
    with pytest.raises(ValueError, match='consumed'): driver.run(root)


def test_unknown_completion_stops_without_dispatching_later_jobs(tmp_path, monkeypatch):
    root, _, _ = runner(tmp_path, monkeypatch); calls = []
    def observed(*args): calls.append(1); raise ObserverCompletionUnknown('SCRIPTED unresolved')
    monkeypatch.setattr(driver, 'observe', observed)
    with pytest.raises(ObserverCompletionUnknown): driver.run(root)
    end = driver.read(root / 'terminal.json')
    assert calls == [1] and end['status'] == 'stopped' and end['completed_jobs'] == 0


def test_new_seed_consumption_stops_before_scientific_start(tmp_path, monkeypatch):
    root, _, u = runner(tmp_path, monkeypatch); u['valid'] = False; seal(u)
    monkeypatch.setattr(driver, 'observe', lambda *args: pytest.fail('no scientific dispatch permitted'))
    with pytest.raises(ValueError, match='consumed after preparation'): driver.run(root)
    assert not (root / 'started.json').exists()


def test_workflow_continuations_bind_exact_runner_audit_and_report(monkeypatch):
    from scripts import finish_native_workflow_fixed_evaluation_v1 as audit_finish
    from scripts import finish_native_workflow_fixed_report_v1 as report_finish
    from scripts.reports import pre_scale_costs_v1 as costs
    seen = {}; monkeypatch.setattr(audit_finish, 'finish', lambda args, **kw: seen.update(kw))
    audit_finish.run(SimpleNamespace())
    assert seen['plan_schema'] == driver.SCHEMA + '.plan'
    assert seen['audit_module'] == 'scripts.audit_native_workflow_fixed_evaluation_v1'
    assert 'scienceutopia.native-workflow-fixed-evaluation-audit.v1' in costs.AUDITS
    seen.clear(); monkeypatch.setattr(report_finish, 'finish', lambda args, **kw: seen.update(kw))
    report_finish.run(SimpleNamespace())
    assert seen['preceding_schema'] == 'scienceutopia.native-workflow-fixed-evaluation-finish.v1'
    assert seen['report_module'] == 'scripts.reports.native_workflow_fixed_evaluation_v1'


def test_json_reconstruction_keeps_both_selection_labels_and_rejects_budget_edit(tmp_path, monkeypatch):
    original, audit, p, usages, sources = evidence(tmp_path / 'input', monkeypatch, both=True)
    root = tmp_path / 'prepared'; root.mkdir()
    driver.save(root / 'plan.json', {k: v for k, v in p.items() if k != 'content_sha256'})
    for i, u in enumerate(usages): driver.save(root / f'seed-usage-{i:02d}.json', {k: v for k, v in u.items() if k != 'content_sha256'})
    monkeypatch.setattr(driver, 'pinned_revision', lambda root: p['source_commit'])
    monkeypatch.setattr(driver, 'origin_evidence', lambda origin: (original, audit))
    monkeypatch.setattr(driver, 'native_sources', lambda source: sources)
    assert driver.require_plan(root) == p
    assert common.jobs_for(json.loads(json.dumps(p, sort_keys=True))) == p['jobs']
    assert any('selected:content-utility' in j['labels'] for j in p['jobs'])
    changed = clone(p); changed['budget']['designer_generation_POSTs'] = 1
    other = tmp_path / 'altered'; other.mkdir()
    driver.save(other / 'plan.json', {k: v for k, v in changed.items() if k != 'content_sha256'})
    for i, u in enumerate(usages): driver.save(other / f'seed-usage-{i:02d}.json', {k: v for k, v in u.items() if k != 'content_sha256'})
    with pytest.raises(ValueError, match='reconstruction'): driver.require_plan(other)
