"""Read-only prospective seed usage check within this project's raw outputs."""
from datetime import datetime,timezone
import json
import hashlib
from pathlib import Path
import sqlite3

from utopia.system.design_patch import digest


def software_fixture_policy(policy):
    """An explicit reviewed file list, never a directory-name exclusion."""
    from utopia.optimization.native_numeric_designer import checked
    checked(policy)
    if (policy.get('schema') != 'scienceutopia.seed-software-fixture-policy.v1'
            or not isinstance(policy.get('files'), list) or not policy['files']
            or not isinstance(policy.get('reviewed_fixture_sources'), dict)
            or not policy['reviewed_fixture_sources']):
        raise ValueError('sealed explicit reviewed software-fixture policy required')
    source = Path(__file__).resolve().parents[1]
    for name, expected in policy['reviewed_fixture_sources'].items():
        path = (source / name).resolve()
        if (Path(name).is_absolute() or not path.is_relative_to(source / 'tests')
                or hashlib.sha256(path.read_bytes()).hexdigest() != expected):
            raise ValueError('reviewed fixture source changed or is outside tests')
    seen = set()
    for row in policy['files']:
        root, relative = Path(row['root']), Path(row['path'])
        identity = (str(root), str(relative))
        if (not root.is_absolute() or root != root.resolve() or relative.is_absolute()
                or '..' in relative.parts or relative.name != 'responses.sqlite'
                or identity in seen or not row.get('reason')
                or not isinstance(row.get('file_sha256'), str) or len(row['file_sha256']) != 64):
            raise ValueError('unique exact relative fixture file binding required')
        seen.add(identity)
    return policy


def usage_inventory(root,seeds,*,software_exclusions=None,strict_paths=False):
    if type(strict_paths) is not bool:
        raise ValueError('explicit boolean prospective path-coverage mode required')
    root=Path(root).resolve();rows=[];excluded=[];errors=[];seen=[]
    if strict_paths:
        if not root.is_dir():
            errors.append({'path': '.', 'error': 'explicit inventory root is missing or not a directory'})
        for path in root.rglob('*'):
            if path.is_symlink() and path.is_dir():
                errors.append({'path': str(path.relative_to(root)),
                    'error': 'directory symlink coverage unresolved; inventory its target as an explicit root'})
    explicit = {}; retained = []
    if software_exclusions is not None:
        policy = software_fixture_policy(software_exclusions)
        explicit = {row['path']: row for row in policy['files'] if Path(row['root']) == root}
        for name, row in explicit.items():
            path = root / name
            if (not path.resolve().is_relative_to(root) or not path.is_file()
                    or hashlib.sha256(path.read_bytes()).hexdigest() != row['file_sha256']):
                errors.append({'path': name, 'error': 'explicit software fixture missing, moved or changed'})
    for path in sorted(root.rglob('responses.sqlite')):
        relative=path.relative_to(root)
        name = str(relative)
        if strict_paths and not path.resolve().is_relative_to(root):
            errors.append({'path': name, 'error': 'response journal resolves outside explicit inventory root'})
            continue
        # An explicit exception is only for the inspected non-production stores.
        # A real metadata-bearing journal is ALWAYS scanned, even if listed.
        if name in explicit:
            row = explicit[name]
            if (not path.resolve().is_relative_to(root)
                    or hashlib.sha256(path.read_bytes()).hexdigest() != row['file_sha256']):
                continue  # already retained as an error above; never claim valid
            try:
                with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True) as db:
                    has_metadata = bool(db.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='metadata'").fetchone())
            except sqlite3.DatabaseError:
                has_metadata = False
            if not has_metadata:
                retained.append({'path': name, 'file_sha256': row['file_sha256'], 'reason': row['reason']})
                continue
            errors.append({'path': name, 'error': 'refuse software exclusion of metadata-bearing journal'})
        if (not strict_paths and name not in explicit
                and any('verification' in part or 'pytest' in part for part in relative.parts)):
            excluded.append(str(relative));continue
        try:
            with sqlite3.connect(path.resolve().as_uri()+'?mode=ro',uri=True) as db:
                records=db.execute('SELECT binding FROM metadata').fetchall()
            if len(records)!=1:raise ValueError('response journal has no unique immutable binding')
            binding=json.loads(records[0][0])
            row={'path':str(relative),'binding_sha256':digest(binding),'seed':binding.get('seed'),
                'model':binding.get('model'),'protocol':binding.get('protocol')}
            rows.append(row)
            if type(row['seed']) is int and row['seed'] in seeds:seen.append(row)
        except Exception as e:errors.append({'path':str(relative),'error':type(e).__name__+': '+str(e)})
    receipt={'schema':'scienceutopia.native-benchmark-seed-usage.v2','root':str(root),
        'seeds':list(seeds),'checked_utc':datetime.now(timezone.utc).isoformat(),
        'bindings':rows,'excluded_software_verification_paths':excluded,'errors':errors,
        'prior_matching_runs':seen,'valid':not errors and not seen,'new_model_calls':0,
        'scope':'Project raw response journals outside explicit software verification; not a claim about other directories or machines.'}
    if software_exclusions is not None:
        receipt.update(schema='scienceutopia.native-benchmark-seed-usage.v3',
            explicit_nonproduction_software_files=retained,
            software_fixture_policy_sha256=software_exclusions['content_sha256'])
    if strict_paths:
        receipt.update(schema='scienceutopia.native-benchmark-seed-usage.v4', strict_path_coverage=True,
            scope='All response journals under the explicit resolved root, without directory-name exclusions; '
                  'only exact reviewed non-production file exceptions may be omitted. '
                  'Not proof that other roots/machines or a different corpus are unused.')
    receipt['content_sha256']=digest(receipt)
    return receipt


def require_inventory_policy(receipt, policy):
    software_fixture_policy(policy)
    expected = [{'path': row['path'], 'file_sha256': row['file_sha256'], 'reason': row['reason']}
        for row in policy['files'] if row['root'] == receipt['root']]
    order = lambda rows: sorted(rows, key=lambda row: row['path'])
    supported = receipt.get('schema') == 'scienceutopia.native-benchmark-seed-usage.v3' or (
        receipt.get('schema') == 'scienceutopia.native-benchmark-seed-usage.v4'
        and receipt.get('strict_path_coverage') is True
        and not receipt.get('excluded_software_verification_paths'))
    if (not supported
            or receipt.get('software_fixture_policy_sha256') != policy['content_sha256']
            or order(receipt.get('explicit_nonproduction_software_files', [])) != order(expected)):
        raise ValueError('literal complete software-fixture exclusions differ from the bound policy')
