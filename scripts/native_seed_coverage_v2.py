"""Prospective, exact-file software provenance over complete declared roots.

Keep the strict-v4 scan and every metadata match literally. A separately
declared v5 projection can distinguish an inspected metadata-only SCRIPTED
fixture from scientific seed use; a directory name never supplies that proof.
No model calls, generated-code execution, seed replacement or archive edits.
"""
import hashlib
from pathlib import Path
import sqlite3

from scripts.native_benchmark_seed_usage import usage_inventory
from utopia.optimization.native_numeric_designer import checked
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import decode_json

ROOT = Path(__file__).resolve().parents[1]
POLICY = 'scienceutopia.seed-coverage-policy.v2'
SCHEMA = 'scienceutopia.native-benchmark-seed-usage.v5'
LINK_ERROR = 'directory symlink coverage unresolved; inventory its target as an explicit root'
FIXTURE_ERRORS = {'OperationalError: no such table: metadata', 'DatabaseError: file is not a database'}


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def relative(name):
    if not isinstance(name, str):
        raise ValueError('literal relative path required')
    path = Path(name)
    if path.is_absolute() or str(path) != name or not path.parts or any(p in ('.', '..') for p in path.parts):
        raise ValueError('canonical literal relative path required')
    return path


def validate(policy):
    checked(policy)
    if (policy.get('schema') != POLICY or not isinstance(policy.get('seeds'), list)
            or not policy['seeds'] or any(type(s) is not int for s in policy['seeds'])
            or len(set(policy['seeds'])) != len(policy['seeds'])
            or not isinstance(policy.get('roots'), list) or not policy['roots']
            or policy['roots'] != sorted(set(policy['roots']))
            or not isinstance(policy.get('files'), list) or not policy['files']
            or not isinstance(policy.get('external_links'), list)
            or not isinstance(policy.get('reviewed_fixture_sources'), dict)
            or not policy['reviewed_fixture_sources']):
        raise ValueError('sealed explicit v2 root/file/source coverage policy required')
    for root in policy['roots']:
        path = Path(root)
        if not path.is_absolute() or str(path.resolve()) != root or not path.is_dir():
            raise ValueError('existing canonical explicit root required')
    for name, expected in policy['reviewed_fixture_sources'].items():
        path = (ROOT / relative(name)).resolve()
        if not path.is_relative_to(ROOT / 'tests') or not path.is_file() or sha(path) != expected:
            raise ValueError('reviewed fixture test source changed or is outside tests')
    seen = set()
    for row in policy['files']:
        path = relative(row['path']); identity = (row['root'], row['path'])
        if (row['root'] not in policy['roots'] or identity in seen or path.name != 'responses.sqlite'
                or row.get('kind') not in ('nonmetadata-fixture', 'metadata-only-scripted-fixture')
                or not isinstance(row.get('file_sha256'), str) or len(row['file_sha256']) != 64
                or any(c not in '0123456789abcdef' for c in row['file_sha256'])
                or not row.get('reason') or row.get('fixture_source') not in policy['reviewed_fixture_sources']):
            raise ValueError('unique exact fixture file/source binding required')
        seen.add(identity)
        if row['kind'] == 'metadata-only-scripted-fixture':
            binding = row.get('binding')
            if (not isinstance(binding, dict) or set(binding) != {'seed', 'model', 'protocol'}
                    or type(binding['seed']) is not int or binding['model'] != 'SCRIPTED'
                    or binding['protocol'] != 'SCRIPTED'):
                raise ValueError('exact metadata-only SCRIPTED fixture binding required')
    seen = set()
    for row in policy['external_links']:
        relative(row['path']); identity = (row['root'], row['path'])
        if (row['root'] not in policy['roots'] or row.get('target') not in policy['roots']
                or identity in seen or row['root'] == row['target'] or not row.get('reason')):
            raise ValueError('exact external alias and independently inventoried target root required')
        seen.add(identity)
    return policy


def inspect_fixture(root, row):
    path = root / row['path']
    if path.is_symlink() or not path.resolve().is_relative_to(root) or not path.is_file() or sha(path) != row['file_sha256']:
        raise ValueError('declared fixture missing, linked, moved or changed')
    tables = None; bindings = None
    try:
        with sqlite3.connect(path.as_uri() + '?mode=ro', uri=True) as db:
            tables = sorted(r[0] for r in db.execute("SELECT name FROM sqlite_master WHERE type='table'"))
            if 'metadata' in tables:
                bindings = [decode_json(r[0], strict=True, finite_floats=True)
                            for r in db.execute('SELECT binding FROM metadata')]
    except sqlite3.DatabaseError:
        if row['kind'] != 'nonmetadata-fixture':
            raise ValueError('declared SCRIPTED metadata is not readable')
    if row['kind'] == 'metadata-only-scripted-fixture':
        if tables != ['metadata'] or bindings != [row['binding']]:
            raise ValueError('metadata-only fixture acquired real/extra content or changed binding')
    elif tables is not None and 'metadata' in tables:
        raise ValueError('nonmetadata fixture cannot hide a metadata-bearing journal')


def project(raw, policy):
    """Reconstruct classification from the unchanged strict scan, not its labels."""
    checked(raw); validate(policy)
    if (raw.get('schema') != 'scienceutopia.native-benchmark-seed-usage.v4'
            or raw.get('strict_path_coverage') is not True
            or raw.get('excluded_software_verification_paths')
            or raw.get('software_fixture_policy_sha256')
            or raw.get('root') not in policy['roots'] or raw.get('seeds') != policy['seeds']):
        raise ValueError('unexcluded original strict-v4 scan over an exact declared root required')
    root = Path(raw['root']); errors = []; nonmetadata = []; metadata = []; aliases = []
    for row in policy['files']:
        if row['root'] != str(root):
            continue
        try:
            inspect_fixture(root, row)
            proof = clone(row)
            if row['kind'] == 'metadata-only-scripted-fixture':
                actual = [r for r in raw['bindings'] if r['path'] == row['path']]
                if len(actual) != 1 or actual[0]['binding_sha256'] != digest(row['binding']):
                    raise ValueError('SCRIPTED fixture absent/different in original scanned bindings')
                metadata.append(proof)
            else:
                nonmetadata.append(proof)
        except (ValueError, OSError) as error:
            errors.append({'path': row['path'], 'error': str(error)})
    for row in policy['external_links']:
        if row['root'] != str(root):
            continue
        path = root / row['path']
        if not path.is_symlink() or not path.is_dir() or str(path.resolve()) != row['target']:
            errors.append({'path': row['path'], 'error': 'declared external directory alias missing or changed'})
        else:
            aliases.append(clone(row))
    fixture_names = {r['path'] for r in nonmetadata}; alias_names = {r['path'] for r in aliases}
    for row in raw['errors']:
        if row['path'] in fixture_names and row['error'] in FIXTURE_ERRORS:
            continue
        if row['path'] in alias_names and row['error'] == LINK_ERROR:
            continue
        errors.append(clone(row))
    classified = {r['path'] for r in metadata}
    scientific = [clone(r) for r in raw['prior_matching_runs'] if r['path'] not in classified]
    result = {'schema': SCHEMA, 'root': str(root), 'seeds': clone(raw['seeds']),
        'checked_utc': raw['checked_utc'], 'strict_path_coverage': True,
        'coverage_policy_sha256': policy['content_sha256'], 'raw_inventory': clone(raw),
        'bindings': clone(raw['bindings']), 'prior_matching_runs': clone(raw['prior_matching_runs']),
        'scientific_prior_matching_runs': scientific, 'errors': errors,
        'explicit_nonmetadata_fixtures': nonmetadata, 'explicit_metadata_only_scripted_fixtures': metadata,
        'covered_external_directory_aliases': aliases, 'excluded_software_verification_paths': [],
        'valid': not errors and not scientific, 'new_model_calls': 0,
        'scope': 'Declared prospective root-set coverage with exact reviewed fixture provenance. '
            'All original metadata rows/matches/errors remain in raw_inventory; no name-pattern exclusions. '
            'Only hash/source-bound metadata-only SCRIPTED test fixtures are distinguished from scientific '
            'seed use. Every target root must also have its own valid inventory. Unknown/changed files, '
            'scientific matches and missing roots still stop; no global unusedness or scientific gain claim.'}
    result['content_sha256'] = digest(result)
    return result


def inventory(root, seeds, policy):
    validate(policy)
    if list(seeds) != policy['seeds']:
        raise ValueError('unchanged declared evaluation conditions required')
    return project(usage_inventory(root, seeds, strict_paths=True), policy)


def require_all(usages, policy):
    validate(policy)
    if [u['root'] for u in usages] != policy['roots']:
        raise ValueError('every declared target/root inventory is required in exact order')
    for receipt in usages:
        checked(receipt)
        if receipt != project(receipt['raw_inventory'], policy) or not receipt['valid']:
            raise ValueError('valid original-scan/file/source-bound coverage reconstruction required')
