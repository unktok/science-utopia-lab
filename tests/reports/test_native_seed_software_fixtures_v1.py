"""SCRIPTED inventories only: no model, native world or code execution."""
import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts import native_benchmark_seed_usage as inventory
from scripts import run_native_workflow_fixed_evaluation_v1 as driver
from tests.reports.test_native_benchmark_seed_usage import journal
from tests.reports.test_native_workflow_fixed_evaluation_v1 import evidence, runner
from utopia.optimization.native_numeric_designer import save
from utopia.system.design_patch import digest


def seal(value):
    value.pop('content_sha256', None)
    value['content_sha256'] = digest(value)
    return value


def policy_for(root, file):
    source = Path(__file__).resolve()
    return seal({'schema': 'scienceutopia.seed-software-fixture-policy.v1',
        'files': [{'root': str(root.resolve()), 'path': str(file.relative_to(root)),
            'file_sha256': hashlib.sha256(file.read_bytes()).hexdigest(),
            'reason': 'SCRIPTED explicit fixture, not a production response journal'}],
        'reviewed_fixture_sources': {str(source.relative_to(inventory.Path(inventory.__file__).resolve().parents[1])):
            hashlib.sha256(source.read_bytes()).hexdigest()}})


def fixture(tmp_path):
    file = tmp_path / 'qa' / 'responses.sqlite'
    file.parent.mkdir(); file.write_bytes(b'SCRIPTED cache primitive')
    return file, policy_for(tmp_path, file)


def test_only_exact_reviewed_nonproduction_file_is_excluded(tmp_path):
    file, policy = fixture(tmp_path)
    assert not inventory.usage_inventory(tmp_path, [1858637637])['valid']
    result = inventory.usage_inventory(tmp_path, [1858637637], software_exclusions=policy)
    assert result['valid'] and result['schema'].endswith('.v3')
    assert len(result['explicit_nonproduction_software_files']) == 1
    inventory.require_inventory_policy(result, policy)
    other = tmp_path / 'qa' / 'unlisted' / 'responses.sqlite'
    other.parent.mkdir(); other.write_bytes(file.read_bytes())
    result = inventory.usage_inventory(tmp_path, [1858637637], software_exclusions=policy)
    assert not result['valid'] and result['errors'][0]['path'] == 'qa/unlisted/responses.sqlite'


@pytest.mark.parametrize('change', ['content', 'missing'])
def test_changed_or_missing_fixture_never_passes(tmp_path, change):
    file, policy = fixture(tmp_path)
    if change == 'content': file.write_bytes(b'SCRIPTED changed fixture')
    else: file.unlink()
    result = inventory.usage_inventory(tmp_path, [42], software_exclusions=policy)
    assert not result['valid'] and result['errors']


def test_metadata_journal_is_scanned_even_if_explicitly_listed(tmp_path):
    file = tmp_path / 'software-verification' / 'responses.sqlite'
    journal(file, 1858637637)
    policy = policy_for(tmp_path, file)
    result = inventory.usage_inventory(tmp_path, [1858637637], software_exclusions=policy)
    assert not result['valid'] and result['prior_matching_runs'][0]['seed'] == 1858637637
    assert not result['explicit_nonproduction_software_files']
    assert not result['excluded_software_verification_paths']


@pytest.mark.parametrize('change', ['parent', 'absolute', 'duplicate', 'source', 'checksum'])
def test_invalid_policy_is_not_a_directory_skip(tmp_path, change):
    _, policy = fixture(tmp_path)
    if change == 'parent': policy['files'][0]['path'] = '../responses.sqlite'
    elif change == 'absolute': policy['files'][0]['path'] = '/private/tmp/responses.sqlite'
    elif change == 'duplicate': policy['files'].append(dict(policy['files'][0]))
    elif change == 'source': policy['reviewed_fixture_sources'] = {'scripts/native_benchmark_seed_usage.py': 'a' * 64}
    else: policy['content_sha256'] = 'a' * 64
    if change != 'checksum': seal(policy)
    with pytest.raises(ValueError): inventory.usage_inventory(tmp_path, [42], software_exclusions=policy)


def test_plan_binds_complete_inventory_policy_and_keeps_same_jobs(tmp_path, monkeypatch):
    original, audit, old, _, sources = evidence(tmp_path / 'input', monkeypatch)
    _, policy = fixture(tmp_path)
    usages = [inventory.usage_inventory(tmp_path, old['evaluation']['seeds'], software_exclusions=policy)]
    p = driver.build_plan(original, audit, source=old['source_commit'], origin={}, usages=usages,
        seeds=old['evaluation']['seeds'], observer_backend=old['observer_contract']['backend'],
        source_proof=sources, software_exclusions=policy)
    assert p['seed_software_exclusions'] == policy and p['fixed_selection'] == old['fixed_selection']
    # Job identities bind the entire plan; compare literal systems/labels/seeds.
    assert [{k: v for k, v in j.items() if k != 'identity'} for j in p['jobs']] == [
        {k: v for k, v in j.items() if k != 'identity'} for j in old['jobs']]
    usages[0]['explicit_nonproduction_software_files'] = []; seal(usages[0])
    with pytest.raises(ValueError, match='complete software-fixture'):
        driver.build_plan(original, audit, source=old['source_commit'], origin={}, usages=usages,
            seeds=old['evaluation']['seeds'], observer_backend=old['observer_contract']['backend'],
            source_proof=sources, software_exclusions=policy)


def test_real_shared_dispatch_uses_same_explicit_policy_before_start(tmp_path, monkeypatch):
    root, p, _ = runner(tmp_path, monkeypatch)
    inventory_root = tmp_path / 'inventory'
    _, policy = fixture(inventory_root)
    p['seed_software_exclusions'] = policy; seal(p)
    seen = []
    original = driver.usage_inventory
    def inspect(root, seeds, **kwargs):
        seen.append(kwargs['software_exclusions'])
        return original(root, seeds, **kwargs)
    monkeypatch.setattr(driver, 'usage_inventory', inspect)
    monkeypatch.setattr(driver, 'observe', lambda *args: None)
    driver.run(root)
    assert seen == [policy] and driver.read(root / 'terminal.json')['status'] == 'closed'
    u = driver.read(root / 'pre-dispatch-seed-usage-00.json')
    inventory.require_inventory_policy(u, policy)


def test_optional_prepare_retains_rejected_inventory_without_plan(tmp_path, monkeypatch):
    original, audit, _, _, sources = evidence(tmp_path / 'input', monkeypatch)
    origin = tmp_path / 'origin'; origin.mkdir(); (origin / 'writer.lock').touch()
    inventory_root = tmp_path / 'inventory'; inventory_root.mkdir()
    _, policy = fixture(inventory_root)
    # This additional unlisted malformed file must stop the new preparation.
    (inventory_root / 'responses.sqlite').write_bytes(b'SCRIPTED unknown')
    policy_file = tmp_path / 'policy.json'; save(policy_file, {k: v for k, v in policy.items() if k != 'content_sha256'})
    paths = [tmp_path / 'audit-one.json', tmp_path / 'audit-two.json']
    for path in paths: save(path, {k: v for k, v in audit.items() if k != 'content_sha256'})
    monkeypatch.setattr(driver, 'require_environment', lambda: None)
    monkeypatch.setattr(driver, 'pinned_revision', lambda *args: 'a' * 40)
    monkeypatch.setattr(driver, 'origin_evidence', lambda *args: (original, audit))
    monkeypatch.setattr(driver, 'backend_binding', lambda *args: original['observer_contract']['backend'])
    monkeypatch.setattr(driver, 'native_sources', lambda *args: sources)
    output = tmp_path / 'out'
    args = SimpleNamespace(output=output, origin_run=origin, origin_source=origin,
        audit_one=paths[0], audit_two=paths[1], seed_usage_root=[inventory_root],
        evaluation_seed=[1858637637], seed_software_exclusions=policy_file)
    with pytest.raises(ValueError, match='unconsumed seed'): driver.prepare(args)
    assert not driver.read(output / 'seed-usage-00.json')['valid']
    assert driver.read(output / 'preparation-ended.json')['status'] == 'stopped'
    assert not (output / 'plan.json').exists() and not (output / 'started.json').exists()


def test_new_dispatch_conflict_retains_proof_without_scientific_start(tmp_path, monkeypatch):
    root, p, _ = runner(tmp_path, monkeypatch)
    inventory_root = tmp_path / 'inventory'
    _, policy = fixture(inventory_root)
    p['seed_software_exclusions'] = policy; seal(p)
    journal(inventory_root / 'new-real' / 'responses.sqlite', p['evaluation']['seeds'][0])
    monkeypatch.setattr(driver, 'observe', lambda *args: pytest.fail('no scientific dispatch'))
    with pytest.raises(ValueError, match='consumed after preparation'): driver.run(root)
    result = driver.read(root / 'pre-dispatch-seed-usage-00.json')
    assert not result['valid'] and result['prior_matching_runs']
    assert not (root / 'started.json').exists()
