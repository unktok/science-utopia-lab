"""Exact SCRIPTED fixture provenance, not real scientific seed consumption."""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import sqlite3

import pytest

from scripts import native_seed_coverage_v2 as module
from tests.reports.test_native_benchmark_seed_usage import journal
from utopia.system.design_patch import digest

SEEDS = [193, 197]


def seal(value):
    value.pop('content_sha256', None)
    value['content_sha256'] = digest(value)
    return value


def policy_for(roots, files, links=()):
    source = Path(__file__).resolve()
    return seal({'schema': module.POLICY, 'seeds': SEEDS,
        'roots': sorted(str(p.resolve()) for p in roots),
        'files': files, 'external_links': list(links),
        'reviewed_fixture_sources': {str(source.relative_to(module.ROOT)): module.sha(source)}})


def setup(tmp_path):
    root = tmp_path / 'one'; root.mkdir()
    meta = root / 'fixture' / 'responses.sqlite'; journal(meta, SEEDS[0])
    plain = root / 'primitive' / 'responses.sqlite'; plain.parent.mkdir()
    plain.write_bytes(b'SCRIPTED cache primitive')
    source = str(Path(__file__).resolve().relative_to(module.ROOT))
    common = {'root': str(root), 'fixture_source': source, 'reason': 'Inspected exact scripted test helper output'}
    rows = [{**common, 'path': str(meta.relative_to(root)), 'file_sha256': module.sha(meta),
             'kind': 'metadata-only-scripted-fixture',
             'binding': {'seed': SEEDS[0], 'model': 'SCRIPTED', 'protocol': 'SCRIPTED'}},
            {**common, 'path': str(plain.relative_to(root)), 'file_sha256': module.sha(plain),
             'kind': 'nonmetadata-fixture'}]
    return root, meta, plain, policy_for([root], rows)


def test_v5_keeps_original_metadata_matches_and_errors_instead_of_erasing_them(tmp_path):
    root, _, _, policy = setup(tmp_path)
    result = module.inventory(root, SEEDS, policy)
    assert result['valid'] and not result['errors'] and not result['scientific_prior_matching_runs']
    assert not result['raw_inventory']['valid']
    assert len(result['raw_inventory']['errors']) == 1
    assert len(result['prior_matching_runs']) == len(result['bindings']) == 1
    assert result['prior_matching_runs'] == result['raw_inventory']['prior_matching_runs']
    assert len(result['explicit_nonmetadata_fixtures']) == 1
    assert len(result['explicit_metadata_only_scripted_fixtures']) == 1
    module.require_all([result], policy)


@pytest.mark.parametrize('change', ['bytes', 'missing', 'extra-table', 'unlisted-scripted', 'unlisted-bad', 'scientific-model'])
def test_changed_or_unclassified_evidence_still_stops(tmp_path, change):
    root, meta, plain, policy = setup(tmp_path)
    if change == 'bytes': plain.write_bytes(b'SCRIPTED changed')
    elif change == 'missing': plain.unlink()
    elif change == 'extra-table':
        with sqlite3.connect(meta) as db: db.execute('CREATE TABLE replies(data TEXT)')
        policy['files'][0]['file_sha256'] = module.sha(meta); seal(policy)
    elif change == 'unlisted-scripted': journal(root / 'ordinary-name' / 'responses.sqlite', SEEDS[0])
    elif change == 'unlisted-bad': (root / 'responses.sqlite').write_bytes(b'SCRIPTED unknown')
    else:
        with sqlite3.connect(meta) as db:
            db.execute('UPDATE metadata SET binding=?', (json.dumps({'seed': SEEDS[0], 'model': 'qwen3:8b', 'protocol': 'actual'}),))
        policy['files'][0]['file_sha256'] = module.sha(meta); seal(policy)
    result = module.inventory(root, SEEDS, policy)
    assert not result['valid']
    with pytest.raises(ValueError): module.require_all([result], policy)


def test_nonmetadata_kind_cannot_suppress_metadata_even_with_matching_file_hash(tmp_path):
    root, _, _, policy = setup(tmp_path)
    policy['files'][0]['kind'] = 'nonmetadata-fixture'; policy['files'][0].pop('binding'); seal(policy)
    result = module.inventory(root, SEEDS, policy)
    assert not result['valid'] and result['scientific_prior_matching_runs'] and result['errors']


@pytest.mark.parametrize('change', ['checksum', 'source', 'path', 'binding', 'duplicate-root', 'seed-type'])
def test_policy_is_exact_not_a_directory_or_model_name_whitelist(tmp_path, change):
    root, _, _, policy = setup(tmp_path)
    if change == 'checksum': policy['content_sha256'] = '0' * 64
    elif change == 'source': policy['reviewed_fixture_sources'] = {'scripts/native_seed_coverage_v2.py': '0' * 64}
    elif change == 'path': policy['files'][0]['path'] = '../responses.sqlite'
    elif change == 'binding': policy['files'][0]['binding']['model'] = 'qwen3:8b'
    elif change == 'duplicate-root': policy['roots'].append(str(root))
    else: policy['seeds'] = [True]
    if change != 'checksum': seal(policy)
    with pytest.raises(ValueError): module.inventory(root, SEEDS, policy)


def test_external_alias_requires_exact_coverage_of_its_target_root(tmp_path):
    root, _, _, policy = setup(tmp_path)
    other = tmp_path / 'two'; other.mkdir()
    (other / 'link').symlink_to(root, target_is_directory=True)
    policy['roots'] = sorted([str(root), str(other)])
    policy['external_links'] = [{'root': str(other), 'path': 'link', 'target': str(root),
                                 'reason': 'Target explicitly included and independently scanned'}]
    seal(policy)
    usages = [module.inventory(p, SEEDS, policy) for p in policy['roots']]
    assert all(u['valid'] for u in usages)
    assert any(u['raw_inventory']['errors'] for u in usages)
    module.require_all(usages, policy)
    with pytest.raises(ValueError, match='every declared'): module.require_all(usages[:1], policy)
    (other / 'link').unlink(); (other / 'link').symlink_to(tmp_path, target_is_directory=True)
    assert not module.inventory(other, SEEDS, policy)['valid']


def test_saved_projection_cannot_hide_an_original_match_or_change_classification(tmp_path):
    root, _, _, policy = setup(tmp_path)
    original = module.inventory(root, SEEDS, policy)
    changed = deepcopy(original); changed['prior_matching_runs'] = []; seal(changed)
    with pytest.raises(ValueError): module.require_all([changed], policy)
    changed = deepcopy(original); changed['explicit_metadata_only_scripted_fixtures'] = []; seal(changed)
    with pytest.raises(ValueError): module.require_all([changed], policy)


def test_inventory_cannot_silently_change_the_declared_conditions(tmp_path):
    root, _, _, policy = setup(tmp_path)
    with pytest.raises(ValueError, match='unchanged declared'): module.inventory(root, [199], policy)
