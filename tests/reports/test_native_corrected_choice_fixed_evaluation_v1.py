"""SCRIPTED metadata/transport boundaries; no native execution or unused claim."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import run_native_corrected_choice_fixed_evaluation_v1 as driver
from scripts import run_native_priority_fixed_evaluation_v1 as base
from scripts import run_native_objective_fixed_evaluation_v1 as shared
from scripts.native_corrected_choice_fixed_bank_v1 import freeze_bank
from tests.reports import test_native_priority_fixed_evaluation_v1 as legacy
from tests.reports.test_native_corrected_choice_fixed_bank_v1 import inputs
from utopia.optimization.native_numeric_designer import save
from utopia.system.design_patch import clone

seal = legacy.seal
original_fixture = legacy.fixture


def fixture(tmp_path, monkeypatch):
    native, _, _, usage, _, _ = original_fixture(tmp_path, monkeypatch)
    p, a, slots, refs = inputs(); system = clone(native['initial_system'])
    for key in ('source_commit', 'scientist', 'designer', 'data_cache', 'world', 'catalog',
                'initial_system', 'observer_contract', 'scientist_transport', 'operational_protocol'):
        p[key] = clone(native[key])
    for entry in slots:
        entry['parent_system'] = clone(system)
        for key in ('suggestion', 'observation'):
            if entry[key] is not None: entry[key]['candidate'] = clone(system)
    for ref in refs.values(): ref['candidate'] = clone(system)
    for world in a['worlds']: world['system'] = clone(system)
    for scope in ('selected', 'own_only_selected'):
        for method in a['selection'][scope].values():
            for history in method.values():
                for entry in history.values():
                    if entry['system'] is not None: entry['system'] = clone(system)
    p = seal(p); a.update(source_commit=p['source_commit'], plan_sha256=p['content_sha256'])
    a['selection'] = seal(a['selection']); a = seal(a)
    return p, a, freeze_bank(p, a, slots, refs), usage, slots, refs


def build(tmp_path, monkeypatch):
    p, a, bank, usage, slots, refs = fixture(tmp_path, monkeypatch)
    result = driver.build_plan(p, a, bank, source='e' * 40,
        origin={'run': str(tmp_path / 'origin'), 'SCRIPTED': 'not an actual scientific closure'}, usages=[usage],
        observer_backend=p['observer_contract']['backend'], source_proof={'original_source': p['source_commit']})
    return seal(result), (p, a, bank, usage, slots, refs)


def test_both_endpoint_scopes_keep_exact_native_world_laws_loss_and_transport(tmp_path, monkeypatch):
    result, (p, a, bank, _, _, _) = build(tmp_path, monkeypatch)
    assert result['schema'] == driver.SCHEMA + '.plan'
    assert result['protocol'] == driver.PROTOCOL
    assert result['fixed_selection'] == bank and len(bank['entries']) == 15
    assert result['evaluation']['seeds'] == [83003, 83011]
    assert len(result['jobs']) == 2 and all(len(job['labels']) == 15 for job in result['jobs'])
    assert result['losses'] == p['losses'] and result['scientist_transport'] == p['scientist_transport']
    assert result['world']['world_conditions'] == p['world']['world_conditions']
    assert result['budget']['designer_generation_POSTs'] == 0 and not result['budget']['replace_failed_slots']
    assert result['origin_selection_content_sha256'] == a['selection']['content_sha256']
    assert bank['entries'][3]['selected_origin'] == 'reference'
    assert bank['entries'][-1]['selected_origin'] == 'own'
    assert driver.interval is base.interval and driver.observe is base.observe


@pytest.mark.parametrize('profile', ['priority-v1', 'unknown', 'corrected-choice-v1'])
def test_no_implicit_old_bank_or_unknown_profile_transfer(tmp_path, monkeypatch, profile):
    p, a, bank, usage, _, _ = fixture(tmp_path, monkeypatch)
    if profile == 'corrected-choice-v1':
        bank = original_fixture(tmp_path / 'old', monkeypatch)[2]
    with pytest.raises(ValueError):
        base.build_plan(p, a, bank, source='e' * 40, origin={}, usages=[usage],
            observer_backend=p['observer_contract']['backend'], source_proof={'original_source': p['source_commit']},
            profile=profile)


def closed_origin(tmp_path, monkeypatch):
    monkeypatch.setattr(legacy, 'fixture', fixture)
    return legacy.closed_origin(tmp_path, monkeypatch)


def test_actual_plain_closure_abi_and_two_scope_projection(tmp_path, monkeypatch):
    origin = closed_origin(tmp_path, monkeypatch)
    p, _, bank = driver.origin_evidence(origin)
    assert p['generations'] == 4 and len(bank['entries']) == 15
    with pytest.raises(ValueError, match='readout differs'): base.origin_evidence(origin)
    target = Path(origin['readouts']) / 'report-2/slots.csv'; target.write_text('SCRIPTED changed')
    with pytest.raises(ValueError, match='changed'): driver.origin_evidence(origin)


@pytest.mark.parametrize('used', [False, True])
def test_public_prepare_never_calls_models_and_retains_rejected_inventory(tmp_path, monkeypatch, used):
    from scripts import run_pre_scale_search_v1 as environment
    from tests.reports.test_native_benchmark_seed_usage import journal
    origin = closed_origin(tmp_path / 'input', monkeypatch)
    p = driver.read(Path(origin['run']) / 'plan.json')
    monkeypatch.setattr(environment, 'require_environment', lambda: None)
    monkeypatch.setattr(base, 'backend_binding', lambda provider: p['observer_contract']['backend'])
    monkeypatch.setattr(base, 'native_sources', lambda commit: {'original_source': commit})
    raw = tmp_path / 'usage'; raw.mkdir()
    if used: journal(raw / 'pytest-real/responses.sqlite', 83003)
    args = SimpleNamespace(output=tmp_path / 'out', seed_usage_root=[raw], seed_software_exclusions=None,
        **{'origin_' + key: Path(origin[key]) for key in ('run', 'source', 'analysis', 'readouts')})
    (Path(origin['run']) / 'writer.lock').touch()
    if used:
        with pytest.raises(ValueError, match='strict all-path'): driver.prepare(args)
    else: driver.prepare(args)
    assert driver.read(args.output / 'seed-usage-00.json')['valid'] is (not used)
    assert driver.read(args.output / 'preparation-ended.json')['status'] == ('stopped' if used else 'prepared')
    assert not (args.output / 'started.json').exists()
    with pytest.raises(ValueError, match='fresh output'): driver.prepare(args)


@pytest.mark.parametrize('failure', [None, 'known-null', 'unknown'])
def test_shared_public_run_consumes_null_and_never_refills_or_restarts(tmp_path, monkeypatch, failure):
    p, _ = build(tmp_path / 'inputs', monkeypatch); root = tmp_path / 'run'; root.mkdir()
    origin = Path(p['origin']['run']); origin.mkdir(); (origin / 'writer.lock').touch()
    usage = driver.strict_inventory(tmp_path / 'inputs/seed-root', clone(driver.SEEDS))
    save(root / 'seed-usage-00.json', {k: v for k, v in usage.items() if k != 'content_sha256'})
    monkeypatch.setattr(base, 'require_plan', lambda root, **kwargs: p)
    monkeypatch.setattr(shared, 'require_environment', lambda: None)
    class Observer:
        def __init__(self, *args, **kwargs): pass
        def audit(self): return seal({'SCRIPTED': 'observer'})
    monkeypatch.setattr(shared, 'CommonContentObserver', Observer)
    class Unknown(BaseException): pass
    calls = []
    def observe(root, plan, job, observer):
        calls.append(job['identity'])
        if failure == 'unknown': raise Unknown('SCRIPTED unknown dispatch')
        return {'status': 'failed', 'loss': None} if failure == 'known-null' else {'status': 'complete'}
    monkeypatch.setattr(base, 'observe', observe)
    if failure == 'unknown':
        with pytest.raises(Unknown): driver.run(root)
    else: driver.run(root)
    end = driver.read(root / 'terminal.json')
    assert end['schema'] == driver.SCHEMA + '.terminal'
    assert end['status'] == ('stopped' if failure == 'unknown' else 'closed')
    assert len(calls) == (1 if failure == 'unknown' else len(p['jobs']))
    assert end['completed_jobs'] == (0 if failure == 'unknown' else len(p['jobs']))
    with pytest.raises(ValueError, match='no redispatch'): driver.run(root)
