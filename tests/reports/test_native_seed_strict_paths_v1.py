"""Prospective strict inventories; all SQLite journals here are SCRIPTED."""
from copy import deepcopy

import pytest

from scripts import native_benchmark_seed_usage as module
from tests.reports.test_native_benchmark_seed_usage import journal
from tests.reports.test_native_seed_software_fixtures_v1 import fixture, policy_for, seal


@pytest.mark.parametrize('name', ['software-verification', 'pytest-actual', 'outer/verification-inner'])
def test_all_metadata_journals_scanned_despite_directory_names(tmp_path, name):
    journal(tmp_path / name / 'responses.sqlite', 83003)
    old = module.usage_inventory(tmp_path, [83003, 83011])
    assert old['valid'] and old['excluded_software_verification_paths']  # Original legacy contract remains.
    actual = module.usage_inventory(tmp_path, [83003, 83011], strict_paths=True)
    assert actual['schema'].endswith('.v4') and actual['strict_path_coverage']
    assert not actual['valid'] and not actual['excluded_software_verification_paths']
    assert actual['prior_matching_runs'][0]['seed'] == 83003


def test_strict_unrelated_seed_is_valid_without_claiming_other_root_coverage(tmp_path):
    journal(tmp_path / 'pytest-actual/responses.sqlite', 42)
    r = module.usage_inventory(tmp_path, [83003, 83011], strict_paths=True)
    assert r['valid'] and len(r['bindings']) == 1 and not r['prior_matching_runs']
    assert 'other roots' in r['scope']


def test_strict_software_exception_requires_exact_reviewed_nonmetadata_file(tmp_path):
    file, policy = fixture(tmp_path)
    r = module.usage_inventory(tmp_path, [83003, 83011], strict_paths=True, software_exclusions=policy)
    assert r['valid'] and r['schema'].endswith('.v4')
    module.require_inventory_policy(r, policy)
    for edit in ('mode', 'skip'):
        bad = deepcopy(r)
        if edit == 'mode': bad['strict_path_coverage'] = False
        else: bad['excluded_software_verification_paths'] = ['hidden-real-journal']
        seal(bad)
        with pytest.raises(ValueError): module.require_inventory_policy(bad, policy)


def test_strict_cannot_exclude_real_metadata_even_with_explicit_policy(tmp_path):
    path = tmp_path / 'pytest-actual/responses.sqlite'; journal(path, 83003)
    policy = policy_for(tmp_path, path)
    r = module.usage_inventory(tmp_path, [83003], strict_paths=True, software_exclusions=policy)
    assert not r['valid'] and r['errors'] and r['prior_matching_runs']
    assert not r['explicit_nonproduction_software_files']


def test_strict_unknown_journal_is_not_a_directory_name_exception(tmp_path):
    p = tmp_path / 'pytest-actual/responses.sqlite'; p.parent.mkdir(); p.write_bytes(b'SCRIPTED invalid SQLite')
    r = module.usage_inventory(tmp_path, [83003], strict_paths=True)
    assert not r['valid'] and r['errors'] and not r['excluded_software_verification_paths']


@pytest.mark.parametrize('kind', ['file', 'directory', 'missing-root'])
def test_strict_unresolved_coverage_is_not_unused_proof(tmp_path, kind):
    root = tmp_path / 'scan'; root.mkdir(); elsewhere = tmp_path / 'other'
    journal(elsewhere / 'responses.sqlite', 83003)
    if kind == 'directory': (root / 'linked').symlink_to(elsewhere, target_is_directory=True)
    elif kind == 'file': (root / 'responses.sqlite').symlink_to(elsewhere / 'responses.sqlite')
    else: root = root / 'missing'
    r = module.usage_inventory(root, [83003], strict_paths=True)
    assert not r['valid'] and r['errors']


def test_strict_mode_is_not_truthy_string(tmp_path):
    with pytest.raises(ValueError): module.usage_inventory(tmp_path, [83003], strict_paths='true')
