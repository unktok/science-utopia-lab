"""SCRIPTED plan/process-boundary checks, not native execution or source proof."""
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import run_native_priority_fixed_evaluation_v1 as driver
from scripts import run_native_objective_fixed_evaluation_v1 as shared
from scripts.native_priority_fixed_bank_v1 import freeze_bank
from scripts.reports.native_priority_method_readout_v1 import analyze
from tests.reports.test_native_priority_fixed_bank_v1 import inputs
from tests.reports.test_native_priority_method_plan_v1 import plan as native_plan
from utopia.optimization.native_numeric_designer import save
from utopia.system.design_patch import clone, digest


def seal(value):
    value = {k: v for k, v in clone(value).items() if k != 'content_sha256'}
    return {**value, 'content_sha256': digest(value)}


def fixture(tmp_path, monkeypatch):
    native, _ = native_plan(tmp_path / 'native', monkeypatch)
    p, a, slots, refs = inputs(); system = clone(native['initial_system'])
    for k in ('source_commit', 'scientist', 'designer', 'data_cache', 'world', 'catalog',
              'initial_system', 'observer_contract', 'scientist_transport', 'operational_protocol'):
        p[k] = clone(native[k])
    for entry in slots:
        entry['suggestion']['candidate'] = clone(system); entry['observation']['candidate'] = clone(system)
        entry['parent_system'] = clone(system)
    for ref in refs.values(): ref['candidate'] = clone(system)
    for world in a['worlds']: world['system'] = clone(system)
    for method in a['selection']['selected'].values():
        for history in method.values():
            for entry in history.values(): entry['system'] = clone(system)
    p = seal(p); a.update(source_commit=p['source_commit'], plan_sha256=p['content_sha256'])
    a['selection'] = seal(a['selection']); a = seal(a)
    inventory_root = tmp_path / 'seed-root'; inventory_root.mkdir(parents=True)
    usage = driver.strict_inventory(inventory_root, clone(driver.SEEDS))
    bank = freeze_bank(p, a, slots, refs)
    return p, a, bank, usage, slots, refs


def build(tmp_path, monkeypatch):
    p, a, bank, u, slots, refs = fixture(tmp_path, monkeypatch)
    result = driver.build_plan(p, a, bank, source='e' * 40,
        origin={'run': str(tmp_path / 'origin'), 'SCRIPTED': 'not actual cold proof'}, usages=[u],
        observer_backend=p['observer_contract']['backend'], source_proof={'original_source': p['source_commit']})
    return seal(result), (p, a, bank, u, slots, refs)


def test_exact_native_world_v6_loss_transport_bank_and_two_conditions(tmp_path, monkeypatch):
    result, (p, a, bank, u, _, _) = build(tmp_path, monkeypatch)
    assert result['fixed_selection'] == bank and len(bank['entries']) == 15
    assert result['jobs'] and len(result['jobs']) == 2
    assert result['evaluation']['seeds'] == [83003, 83011]
    assert all(len(j['labels']) == 15 for j in result['jobs'])
    assert result['world']['world_conditions'] == p['world']['world_conditions']
    assert result['losses'] == p['losses'] and result['scientist_transport'] == p['scientist_transport']
    assert result['budget']['observer_POSTs_upper_bound'] == 6000
    assert result['budget']['designer_generation_POSTs'] == 0 and not result['budget']['replace_failed_slots']
    assert result['origin_selection_content_sha256'] == a['selection']['content_sha256']
    assert not result['claims']['candidate_reselection'] and not result['claims']['reference_fallback']
    assert driver.require_candidate.__module__ == 'scripts.run_native_topic_free_optimization_v1'
    assert driver.verify_interval.__module__.endswith('native_institution_workflow_domain_v6')


@pytest.mark.parametrize('edit', ['legacy-coverage', 'used', 'different-seed', 'skipped-directory',
                                'observer', 'bank-origin', 'source-origin', 'duplicate-root'])
def test_changed_bank_science_or_uncertain_seed_proof_rejected(tmp_path, monkeypatch, edit):
    p, a, bank, u, _, _ = fixture(tmp_path, monkeypatch); usages = [u]
    backend = clone(p['observer_contract']['backend']); proof = {'original_source': p['source_commit']}
    if edit == 'legacy-coverage': u['schema'] = 'scienceutopia.native-benchmark-seed-usage.v3'
    elif edit == 'used': u['prior_matching_runs'] = [{'seed': 83003, 'SCRIPTED': True}]
    elif edit == 'different-seed': u['seeds'] = [83003, 83017]
    elif edit == 'skipped-directory': u['excluded_software_verification_paths'] = ['pytest-hidden/responses.sqlite']
    elif edit == 'observer': backend['ollama_version'] = 'SCRIPTED changed backend'
    elif edit == 'bank-origin': bank['origin_selection_content_sha256'] = 'f' * 64
    elif edit == 'source-origin': proof['original_source'] = 'f' * 40
    else: usages.append(clone(u))
    p = seal(p); bank = seal(bank); usages = [seal(v) for v in usages]
    with pytest.raises(ValueError):
        driver.build_plan(p, a, bank, source='e' * 40, origin={}, usages=usages,
            observer_backend=backend, source_proof=proof)


def closed_origin(tmp_path, monkeypatch):
    p, a, _, _, slots, refs = fixture(tmp_path / 'inputs', monkeypatch)
    raw, analysis, reports = (tmp_path / name for name in ('raw', 'analysis', 'reports'))
    for directory in (raw, analysis, reports): directory.mkdir()
    save(raw / 'plan.json', {k: v for k, v in p.items() if k != 'content_sha256'})
    p = driver.read(raw / 'plan.json')
    a['closure']['started'] = save(raw / 'started.json', {'SCRIPTED': 'start'})
    a['closure']['terminal'] = save(raw / 'terminal.json', a['closure']['terminal'])
    save(raw / 'selection.json', {k: v for k, v in a['selection'].items() if k != 'content_sha256'})
    inventory = [{'SCRIPTED': 'not a native raw inventory'}]
    monkeypatch.setattr(driver, '_inventory', lambda root: inventory)
    monkeypatch.setattr(driver, 'pinned_revision', lambda root: p['source_commit'])
    monkeypatch.setattr(driver, 'collect', lambda root, plan: (slots, refs))
    a.update(raw_inventory_sha256=digest(inventory), raw_files=1); a = seal(a)
    for i in (1, 2):
        save(analysis / ('audit-' + str(i) + '.json'), {k: v for k, v in a.items() if k != 'content_sha256'})
        save(analysis / ('costs-' + str(i) + '.json'), {'input_audit_content_sha256': a['content_sha256'],
            'plan_sha256': p['content_sha256'], 'raw_inventory_sha256': a['raw_inventory_sha256'],
            'source_commit': p['source_commit']})
    # The actual preceding closure uses plain orchestration JSON, unlike the
    # sealed scientific/readout APIs. Exercise that public format literally.
    (analysis / 'started.json').write_text(json.dumps({'SCRIPTED': 'plain start'}))
    (analysis / 'ended.json').write_text(json.dumps({'status': 'closed',
        'audit_file_sha256': driver.file_sha256(analysis / 'audit-1.json'),
        'cost_file_sha256': driver.file_sha256(analysis / 'costs-1.json')}))
    report = analyze(p, a, slots, refs)
    for i in (1, 2):
        target = reports / ('report-' + str(i)); target.mkdir()
        save(target / 'report.json', report)
        (target / 'slots.csv').write_text('SCRIPTED,projection\n')
        save(target / 'manifest.json', {'SCRIPTED': 'manifest'})
    save(reports / 'started.json', {'scientific_source_commit': p['source_commit'],
        'plan_file_sha256': driver.file_sha256(raw / 'plan.json'), 'preceding_analysis': str(analysis.resolve())})
    save(reports / 'ended.json', {'status': 'closed', 'new_model_calls': 0, 'new_native_worlds': 0,
        'report_files': {name: driver.file_sha256(reports / 'report-1' / name)
            for name in ('report.json', 'slots.csv', 'manifest.json')}})
    origin = {'run': str(raw), 'source': str(tmp_path / 'source'), 'source_commit': p['source_commit'],
        'analysis': str(analysis), 'readouts': str(reports)}
    origin['input_files'] = {str(path): driver.file_sha256(path) for path in driver.evidence_files(origin)}
    return origin


def test_actual_plain_closure_sealed_readout_abi_is_accepted_without_science(tmp_path, monkeypatch):
    origin = closed_origin(tmp_path, monkeypatch)
    _, _, bank = driver.origin_evidence(origin)
    assert len(bank['entries']) == 15


def test_changed_original_output_never_becomes_a_frozen_policy_bank(tmp_path, monkeypatch):
    origin = closed_origin(tmp_path, monkeypatch)
    p = Path(origin['readouts']) / 'report-2/slots.csv'; p.write_text('SCRIPTED changed')
    with pytest.raises(ValueError, match='changed'): driver.origin_evidence(origin)


@pytest.mark.parametrize('used', [False, True])
def test_public_prepare_preserves_strict_proof_and_stops_before_any_models(tmp_path, monkeypatch, used):
    from scripts import run_pre_scale_search_v1 as environment
    from tests.reports.test_native_benchmark_seed_usage import journal
    origin = closed_origin(tmp_path / 'input', monkeypatch)
    # closed_origin's parent is created by its fixture setup.
    raw_plan = driver.read(Path(origin['run']) / 'plan.json')
    monkeypatch.setattr(environment, 'require_environment', lambda: None)
    monkeypatch.setattr(driver, 'backend_binding', lambda provider: raw_plan['observer_contract']['backend'])
    monkeypatch.setattr(driver, 'native_sources', lambda commit: {'original_source': commit})
    inventory_root = tmp_path / 'strict-root'; inventory_root.mkdir()
    if used: journal(inventory_root / 'pytest-real/responses.sqlite', 83003)
    args = SimpleNamespace(output=tmp_path / 'out', seed_usage_root=[inventory_root], seed_software_exclusions=None,
        **{'origin_' + key: Path(origin[key]) for key in ('run', 'source', 'analysis', 'readouts')})
    (Path(origin['run']) / 'writer.lock').touch()
    if used:
        with pytest.raises(ValueError, match='strict all-path'): driver.prepare(args)
    else: driver.prepare(args)
    proof = driver.read(args.output / 'seed-usage-00.json')
    assert proof['strict_path_coverage'] and proof['valid'] is (not used)
    assert bool(proof['prior_matching_runs']) is used
    assert driver.read(args.output / 'preparation-ended.json')['status'] == ('stopped' if used else 'prepared')
    assert (args.output / 'plan.json').exists() is (not used)
    assert not (args.output / 'started.json').exists()
    with pytest.raises(ValueError, match='fresh output'): driver.prepare(args)


@pytest.mark.parametrize('failure', [None, 'known-null', 'unknown'])
def test_real_shared_run_lock_dispatch_boundary_no_refill_or_restart(tmp_path, monkeypatch, failure):
    p, _ = build(tmp_path / 'inputs', monkeypatch); root = tmp_path / 'run'; root.mkdir()
    origin = Path(p['origin']['run']); origin.mkdir(); (origin / 'writer.lock').touch()
    u = driver.strict_inventory(tmp_path / 'inputs/seed-root', clone(driver.SEEDS))
    save(root / 'seed-usage-00.json', {k: v for k, v in u.items() if k != 'content_sha256'})
    monkeypatch.setattr(driver, 'require_plan', lambda root: p)
    monkeypatch.setattr(shared, 'require_environment', lambda: None)
    class Observer:
        def __init__(self, *a, **kw): pass
        def audit(self): return seal({'SCRIPTED': 'observer'})
    monkeypatch.setattr(shared, 'CommonContentObserver', Observer)
    class Unknown(BaseException): pass
    calls = []
    def observe(root, plan, job, observer):
        calls.append(job['identity'])
        if failure == 'unknown': raise Unknown('SCRIPTED unknown dispatch')
        # A known null returns normally; it consumes its scheduled job.
        return {'status': 'failed', 'loss': None} if failure == 'known-null' else {'status': 'complete'}
    monkeypatch.setattr(driver, 'observe', observe)
    if failure == 'unknown':
        with pytest.raises(Unknown): driver.run(root)
    else: driver.run(root)
    end = driver.read(root / 'terminal.json')
    assert end['status'] == ('stopped' if failure == 'unknown' else 'closed')
    assert len(calls) == (1 if failure == 'unknown' else len(p['jobs']))
    assert end['completed_jobs'] == (0 if failure == 'unknown' else len(p['jobs']))
    assert driver.read(root / 'pre-dispatch-seed-usage-00.json')['strict_path_coverage']
    before = len(calls)
    with pytest.raises(ValueError, match='no redispatch'): driver.run(root)
    assert len(calls) == before
