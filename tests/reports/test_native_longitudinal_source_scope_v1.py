"""SCRIPTED source changes, not native execution/readiness or scientific gains."""
from copy import deepcopy
import subprocess

import pytest

from scripts import native_longitudinal_source_scope_v1 as scope
from utopia.system.design_patch import digest


def git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root, text=True).strip()


def commit(root, message):
    git(root, 'add', '.')
    git(root, '-c', 'user.name=SCRIPTED fixture', '-c', 'user.email=fixture@example.invalid',
        '-c', 'commit.gpgsign=false', 'commit', '-m', message)
    return git(root, 'rev-parse', 'HEAD')


@pytest.fixture
def tree(tmp_path, monkeypatch):
    root = tmp_path/'source'; root.mkdir(); git(root, 'init', '-q')
    native = 'utopia/scientist.py'
    consumer = 'utopia/optimization/common_content_observer.py'
    for name in [native, consumer, *scope.AUTHOR_ROLES, *scope.EXTRA_NATIVE_FILES]:
        path = root/name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('# SCRIPTED original '+name+'\n')
    monkeypatch.setattr(scope, 'BASE', commit(root, 'SCRIPTED baseline'))
    for name in [*scope.AUTHOR_ROLES, *scope.ADDED_ROLES, scope.PROTOCOL, scope.GUARD]:
        path = root/name; path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text('# SCRIPTED prospective '+name+'\n')
    source = commit(root, 'SCRIPTED author changes')
    return root, source, native, consumer


def test_explicit_author_changes_are_bound_not_silently_excluded(tree):
    root, source, native, consumer = tree
    value = scope.source_scope(root, source_commit=source)
    assert set(value['declared_author_modules']) == set(scope.AUTHOR_ROLES)
    assert set(value['added_author_modules']) == set(scope.ADDED_ROLES)
    assert set(value['unchanged_native_files']) == {native, consumer, *scope.EXTRA_NATIVE_FILES}
    assert all(r['literal_changed'] and r['base_sha256'] != r['prospective_sha256']
        for r in value['declared_author_modules'].values())
    assert value['files_silently_excluded'] == []
    assert not value['legacy_guard_modified']
    assert not value['world_scientist_effect_or_loss_consumer_changes_permitted']
    assert not value['runner_cold_integration_proved']
    assert not value['real_backend_readiness_proved']
    assert not value['scientific_gain_claimed']
    assert scope.require_scope(value, root, source_commit=source) == value


@pytest.mark.parametrize('change', ['scientist', 'measurement-consumer', 'physical-script',
    'undeclared-addition', 'undeclared-deletion', 'dirty-author', 'dirty-protocol', 'dirty-guard', 'symlink', 'stale-head'])
def test_undeclared_science_source_or_checkout_changes_fail_visibly(tree, change):
    root, source, native, consumer = tree
    if change in ('scientist', 'measurement-consumer', 'physical-script'):
        name = {'scientist': native, 'measurement-consumer': consumer,
            'physical-script': scope.EXTRA_NATIVE_FILES[0]}[change]
        (root/name).write_text('# SCRIPTED forbidden native change\n')
        source = commit(root, 'SCRIPTED forbidden change')
    elif change == 'undeclared-addition':
        (root/'utopia/unreviewed_effect.py').write_text('# SCRIPTED unknown module\n')
        source = commit(root, 'SCRIPTED undeclared module')
    elif change == 'undeclared-deletion':
        (root/native).unlink()
        source = commit(root, 'SCRIPTED missing module')
    elif change == 'dirty-author':
        (root/next(iter(scope.AUTHOR_ROLES))).write_text('# SCRIPTED uncommitted author\n')
    elif change == 'dirty-protocol':
        (root/scope.PROTOCOL).write_text('# SCRIPTED uncommitted protocol\n')
    elif change == 'dirty-guard':
        (root/scope.GUARD).write_text('# SCRIPTED uncommitted source guard\n')
    elif change == 'symlink':
        path = root/next(iter(scope.ADDED_ROLES))
        target = root/'same-bytes'; target.write_bytes(path.read_bytes())
        path.unlink(); path.symlink_to(target)
    else:
        (root/'unrelated-note.txt').write_text('SCRIPTED new HEAD\n')
        commit(root, 'SCRIPTED new HEAD')
    with pytest.raises(ValueError):
        scope.source_scope(root, source_commit=source)


def test_resealed_misclassified_scope_cannot_inherit_actual_source_proof(tree):
    root, source, _, _ = tree
    value = deepcopy(scope.source_scope(root, source_commit=source))
    value['declared_author_modules'][next(iter(scope.AUTHOR_ROLES))]['role'] = 'SCRIPTED world transition'
    value.pop('content_sha256'); value['content_sha256'] = digest(value)
    with pytest.raises(ValueError, match='declaration differs'):
        scope.require_scope(value, root, source_commit=source)
