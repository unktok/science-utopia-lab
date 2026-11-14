"""Prospective, explicit author changes over the actual staged native source.

This does not weaken the legacy workflow source guard. Every existing native
module except five named author/observation-presentation/decoding modules must retain
the actual staged source bytes. Those five and the one added projection helper
are bound to their new exact committed bytes, not ignored. Runner/cold source
closure, model calibration and scientific effects remain separate obligations.
"""
import hashlib
import io
from pathlib import Path
import re
import subprocess

from utopia.optimization.native_numeric_designer import checked
from utopia.system.design_patch import clone, digest

SCHEMA = 'scienceutopia.native-longitudinal-source-scope.v2'
BASE = 'f47270b967fa167d59df759bebe7b6b104b383d3'
PROTOCOL = 'research/protocols/campaigns/native-longitudinal-source-scope-v1.md'
GUARD = 'scripts/native_longitudinal_source_scope_v1.py'
AUTHOR_ROLES = {
    'utopia/optimization/native_adaptive_search.py':
        'Opt-in optimizer binding and request projection, not a researcher or world transition',
    'utopia/optimization/native_bounded_author_context_v45.py':
        'Inline designer presentation of the explicitly selected parent trajectory',
    'utopia/optimization/native_objective_view.py':
        'Source-owned descriptions of existing common-content measurement arithmetic',
    'utopia/optimization/native_staged_author_v15.py':
        'Optional rationale schema and exact designer component-source bindings',
    'utopia/optimization/native_designer_decoding_v24.py':
        'Declared common 65536-token bounded designer context, not scientist inference or world transitions',
}
ADDED_ROLES = {
    'utopia/optimization/native_longitudinal_feedback_v1.py':
        'Read-only completed-checkpoint attachment and deterministic author-access projection',
}
EXTRA_NATIVE_FILES = (
    'scripts/run_native_objective_instrument_loop_v1.py',
    'scripts/native_benchmark_physical.py',
    'scripts/native_observer_physical_v1.py',
)


def _git(root, *args):
    return subprocess.check_output(['git', *args], cwd=root)


def _names(root, source):
    return {n for n in _git(root, 'ls-tree', '-r', '--name-only', source, '--', 'utopia')
        .decode().splitlines() if n.endswith('.py')}


def _blobs(root, source, names):
    names = sorted(names)
    result = subprocess.run(['git', 'cat-file', '--batch'], cwd=root,
        input=''.join(source + ':' + n + '\n' for n in names).encode(),
        stdout=subprocess.PIPE, check=True)
    stream = io.BytesIO(result.stdout); bodies = {}
    for name in names:
        header = stream.readline().split()
        if len(header) != 3 or header[1] != b'blob':
            raise ValueError('declared source blob missing: ' + name)
        size = int(header[2]); raw = stream.read(size)
        if len(raw) != size or stream.read(1) != b'\n':
            raise ValueError('declared source Git framing differs')
        bodies[name] = raw
    if stream.read():
        raise ValueError('unconsumed source Git bytes')
    return bodies


def source_scope(root, *, source_commit):
    root = Path(root).resolve()
    if not isinstance(source_commit, str) or not re.fullmatch('[0-9a-f]{40}', source_commit):
        raise ValueError('literal prospective source commit required')
    if _git(root, 'rev-parse', 'HEAD').decode().strip() != source_commit:
        raise ValueError('prospective source must be the actual checkout HEAD')
    before, after = _names(root, BASE), _names(root, source_commit)
    if before - after or after - before != set(ADDED_ROLES):
        raise ValueError('undeclared native module addition/deletion in prospective source')
    if not set(AUTHOR_ROLES) <= before:
        raise ValueError('declared author modules missing from actual staged baseline')
    baseline = _blobs(root, BASE, before | set(EXTRA_NATIVE_FILES))
    current = _blobs(root, source_commit, after | set(EXTRA_NATIVE_FILES) | {PROTOCOL, GUARD})
    unchanged, edited = {}, {}
    sha = lambda body: hashlib.sha256(body).hexdigest()
    for name, raw in baseline.items():
        if name in AUTHOR_ROLES:
            edited[name] = {'role': AUTHOR_ROLES[name], 'base_sha256': sha(raw),
                'prospective_sha256': sha(current[name]), 'literal_changed': current[name] != raw}
        elif current[name] != raw:
            raise ValueError('inherited scientist/effect/measurement source differs: ' + name)
        else:
            unchanged[name] = sha(raw)
    for name, raw in current.items():
        path = root/name
        if (path.is_symlink() or not path.is_file() or path.read_bytes() != raw
                or any(p.is_symlink() for p in path.parents if p != root and p.is_relative_to(root))):
            raise ValueError('prospective replay-critical source differs: ' + name)
    result = {'schema': SCHEMA, 'base_native_source_commit': BASE,
        'prospective_source_commit': source_commit,
        'protocol': {'path': PROTOCOL, 'sha256': sha(current[PROTOCOL])},
        'guard': {'path': GUARD, 'sha256': sha(current[GUARD])},
        'unchanged_native_files': unchanged, 'declared_author_modules': edited,
        'added_author_modules': {n: {'role': role, 'sha256': sha(current[n])}
            for n, role in ADDED_ROLES.items()},
        'legacy_guard_modified': False, 'files_silently_excluded': [],
        'world_scientist_effect_or_loss_consumer_changes_permitted': False,
        'global_semantic_equivalence_claimed': False,
        'runner_cold_integration_proved': False, 'real_backend_readiness_proved': False,
        'scientific_gain_claimed': False}
    if _git(root, 'rev-parse', 'HEAD').decode().strip() != source_commit:
        raise ValueError('prospective source changed during comparison')
    result['content_sha256'] = digest(result)
    return result


def require_scope(value, root, *, source_commit):
    checked(value)
    if value != source_scope(root, source_commit=source_commit):
        raise ValueError('prospective native/author source declaration differs')
    return clone(value)
