"""Actual prepare/shared-run inventory boundaries with SCRIPTED native metadata."""
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import native_seed_coverage_v2 as coverage
from scripts import run_native_corrected_choice_fixed_evaluation_v1 as driver
from scripts import run_native_priority_fixed_evaluation_v1 as base
from scripts import run_native_objective_fixed_evaluation_v1 as shared
from tests.reports import test_native_corrected_choice_fixed_evaluation_v1 as native
from tests.reports.test_native_benchmark_seed_usage import journal
from utopia.optimization.native_numeric_designer import save
from utopia.system.design_patch import digest


def policy(root):
    path = root / 'scripted-meta/responses.sqlite'; journal(path, base.SEEDS[0])
    source = str(Path(__file__).resolve().relative_to(coverage.ROOT))
    value = {'schema': coverage.POLICY, 'seeds': list(base.SEEDS), 'roots': [str(root.resolve())],
        'files': [{'root': str(root.resolve()), 'path': str(path.relative_to(root)),
            'file_sha256': coverage.sha(path), 'kind': 'metadata-only-scripted-fixture',
            'binding': {'seed': base.SEEDS[0], 'model': 'SCRIPTED', 'protocol': 'SCRIPTED'},
            'fixture_source': source, 'reason': 'Exact imported journal helper call above, no native/model execution'}],
        'external_links': [], 'reviewed_fixture_sources': {source: coverage.sha(Path(__file__).resolve())}}
    value['content_sha256'] = digest(value)
    return value


def test_v5_keeps_original_bank_world_losses_and_literal_jobs(tmp_path, monkeypatch):
    p, a, bank, original_usage, _, _ = native.fixture(tmp_path, monkeypatch)
    kwargs = {'source': 'e' * 40, 'origin': {}, 'observer_backend': p['observer_contract']['backend'],
              'source_proof': {'original_source': p['source_commit']}}
    before = driver.build_plan(p, a, bank, usages=[original_usage], **kwargs)
    root = Path(original_usage['root']); declaration = policy(root)
    usage = base.strict_inventory(root, base.SEEDS, declaration)
    after = driver.build_plan(p, a, bank, usages=[usage], software_exclusions=declaration, **kwargs)
    for name in ('fixed_selection', 'world', 'losses', 'objectives', 'scientist', 'scientist_transport', 'budget', 'claims'):
        assert before[name] == after[name]
    assert before['jobs'] == after['jobs']
    assert usage['prior_matching_runs'] and not usage['scientific_prior_matching_runs']
    assert after['seed_software_exclusions'] == declaration
    with pytest.raises(ValueError, match='only for corrected'):
        base.build_plan(p, a, bank, usages=[usage], software_exclusions=declaration, **kwargs)


@pytest.mark.parametrize('new_conflict', [False, True])
def test_actual_prepare_reconstruction_and_predispatch_same_policy(tmp_path, monkeypatch, new_conflict):
    from scripts import run_pre_scale_search_v1 as environment
    origin = native.closed_origin(tmp_path / 'origin', monkeypatch)
    p = driver.read(Path(origin['run']) / 'plan.json')
    monkeypatch.setattr(environment, 'require_environment', lambda: None)
    monkeypatch.setattr(shared, 'require_environment', lambda: None)
    monkeypatch.setattr(base, 'backend_binding', lambda provider: p['observer_contract']['backend'])
    monkeypatch.setattr(base, 'native_sources', lambda commit: {'original_source': commit})
    raw = tmp_path / 'inventory'; raw.mkdir(); declaration = policy(raw)
    file = tmp_path / 'policy.json'; save(file, {k: v for k, v in declaration.items() if k != 'content_sha256'})
    args = SimpleNamespace(output=tmp_path / 'evaluation', seed_usage_root=[raw], seed_software_exclusions=file,
        **{'origin_' + k: Path(origin[k]) for k in ('run', 'source', 'analysis', 'readouts')})
    (Path(origin['run']) / 'writer.lock').touch()
    driver.prepare(args); prepared = driver.require_plan(args.output)
    assert prepared['seed_software_exclusions'] == declaration
    initial = driver.read(args.output / 'seed-usage-00.json')
    assert initial['valid'] and initial['prior_matching_runs']
    calls = []
    class Observer:
        def __init__(self, *args, **kwargs): pass
        def audit(self): return native.seal({'SCRIPTED': 'no native/model work'})
    monkeypatch.setattr(shared, 'CommonContentObserver', Observer)
    monkeypatch.setattr(base, 'observe', lambda *args: calls.append(args[-2]['identity']))
    if new_conflict:
        journal(raw / 'new-unclassified/responses.sqlite', base.SEEDS[1])
        with pytest.raises(ValueError, match='consumed after preparation'): driver.run(args.output)
        assert not calls and not (args.output / 'started.json').exists()
        assert not driver.read(args.output / 'pre-dispatch-seed-usage-00.json')['valid']
    else:
        driver.run(args.output)
        assert len(calls) == len(prepared['jobs'])
        final = driver.read(args.output / 'pre-dispatch-seed-usage-00.json')
        assert final['valid'] and final['coverage_policy_sha256'] == declaration['content_sha256']
        assert final['prior_matching_runs'] == initial['prior_matching_runs']
        assert driver.read(args.output / 'terminal.json')['status'] == 'closed'
