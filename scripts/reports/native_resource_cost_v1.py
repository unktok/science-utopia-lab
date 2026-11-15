"""Cold resource-use reconstruction of closed development studies, not optimization.

The original scientific checkout supplies its checkpoint decoder and ledger
reconciler. The new instrument is loaded as a separately hashed external reader.
No unused evaluation is rescored and no objective or selection is changed.
"""
import argparse
import importlib.util
import json
from pathlib import Path

from scripts.analyze_native_open_v7 import _inventory
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'scienceutopia.native-resource-cost-readout.v1'
SCOPES = {
    'longitudinal-development': 'scienceutopia.native-longitudinal-comparison-audit.v1',
    'legacy-choice-controls': 'scienceutopia.native-legacy-choice-pilot-audit.v1',
}
INSTRUMENT_PATH = ROOT / 'utopia/optimization/native_resource_cost.py'


def instrument():
    spec = importlib.util.spec_from_file_location('external_native_resource_cost_v1', INSTRUMENT_PATH)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def measure_world(root, world, module):
    """Keep failed worlds unknown; reconstruct all complete annual boundaries."""
    record = {k: clone(world[k]) for k in ('identity', 'role', 'seed', 'status', 'scores')}
    record['original_initial_physical_identity'] = world['physical_proof'].get('initial_identity')
    if world['status'] != 'complete':
        return {**record, 'resource_cost_status': 'unknown', 'resource_cost': None,
                'reason': 'original incomplete/failed world; partial cost is not a completed outcome'}
    name = world['identity'] + '-s' + str(world['seed'])
    cells = [p for p in root.glob('**/worlds/' + name) if p.is_dir()]
    if len(cells) != 1:
        raise ValueError('unique original audited world required')
    cell = cells[0]
    annual = world['physical_proof']['annual_checkpoints']
    if [item['year'] for item in annual] != list(range(1, world['physical_proof']['years'] + 1)):
        raise ValueError('every audited complete annual checkpoint required')
    paths = []
    for year in range(len(annual) + 1):
        matches = list(cell.rglob(f'portable_checkpoint_year_{year}.json.gz'))
        if len(matches) != 1:
            raise ValueError('unique original initial and annual checkpoint required')
        path = matches[0]
        if year and file_sha256(path) != annual[year - 1]['checkpoint_sha256']:
            raise ValueError('original audited annual checkpoint hash differs')
        paths.append(path)
    base = world['physical_proof']['measurement']
    augmented = module.measure_from_checkpoints(base, paths)
    # Keep original measurements/scores literal. Only separately declared new
    # metrics are extracted; do not feed them back into historical selection.
    return {**record, 'resource_cost_status': 'measured',
            'resource_cost': augmented[module.INSTRUMENT],
            'original_measurement_sha256': digest(base),
            'accepted_decisions': base['metrics']['native.accepted_decisions']['value']}


def export(args):
    run, frozen, out = args.run, args.frozen_source, args.output
    if out.exists() or out.is_relative_to(run) or out.is_relative_to(frozen):
        raise ValueError('fresh output outside original scientific raw/source required')
    paths = [run / 'plan.json', run / 'terminal.json', args.audit_one, args.audit_two]
    if args.audit_one == args.audit_two or args.audit_one.read_bytes() != args.audit_two.read_bytes():
        raise ValueError('two distinct matching original audits required')
    inputs = {str(p): file_sha256(p) for p in paths}
    plan, terminal, audit = [checked(json.loads(p.read_text())) for p in paths[:3]]
    before = _inventory(run)
    reader_commit = pinned_revision(ROOT)
    if (audit['schema'] != SCOPES[args.scope] or terminal['status'] != 'closed'
            or audit['closure']['terminal'] != terminal
            or audit['source_commit'] != plan['source_commit']
            or pinned_revision(frozen) != plan['source_commit']
            or audit['plan_sha256'] != plan['content_sha256']
            or audit['source_proof']['status'] != 'verified-exact-source-closure'
            or audit['raw_inventory_sha256'] != digest(before)
            or audit['new_model_calls'] or audit['new_code_executions']):
        raise ValueError('exact closed development source/plan/audit/raw binding required')
    module = instrument()
    # A worker importing its own newer reconciler is not an original-source
    # reconstruction, even if a selected measurement happens to agree.
    import inspect
    for consumer, relative in [(module.ResourceLedger, 'utopia/funding/accounting.py'),
                               (module.read_portable_checkpoint, 'utopia/runtime/checkpointing.py')]:
        if Path(inspect.getfile(consumer)).resolve() != frozen / relative:
            raise ValueError('original scientific decoder and ledger consumer required')
    readers = [Path(__file__).resolve(), INSTRUMENT_PATH,
               frozen / 'utopia/funding/accounting.py', frozen / 'utopia/runtime/checkpointing.py']
    reader_hashes = {str(p): file_sha256(p) for p in readers}
    worlds = [measure_world(run, w, module) for w in audit['worlds']]
    result = {'schema': SCHEMA, 'scope': args.scope,
        'scientific_source_commit': plan['source_commit'], 'reader_source_commit': reader_commit,
        'reader_sha256s': reader_hashes, 'plan_sha256': plan['content_sha256'],
        'audit_content_sha256': audit['content_sha256'], 'raw_inventory_sha256': digest(before),
        'inputs': inputs, 'worlds': worlds,
        'interpretation': {'development_only': True, 'post_hoc_diagnostic': True,
            'new_model_calls': 0, 'new_native_worlds': 0, 'new_code_executions': 0,
            'loss_changed': False, 'policy_selection': False, 'new_optimization': False,
            'held_out_rescored': False, 'method_superiority': False, 'publication_ready': False}}
    if (before != _inventory(run) or inputs != {str(p): file_sha256(p) for p in paths}
            or reader_hashes != {str(p): file_sha256(p) for p in readers}
            or pinned_revision(frozen) != plan['source_commit']
            or pinned_revision(ROOT) != reader_commit):
        raise ValueError('original raw/input/source or external reader changed during measurement')
    out.mkdir(parents=True)
    save(out / 'report.json', result)
    print(json.dumps({'scope': args.scope, 'worlds': len(worlds),
        'measured': sum(w['resource_cost_status'] == 'measured' for w in worlds),
        'unknown': sum(w['resource_cost_status'] == 'unknown' for w in worlds)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    keys = ('run', 'frozen-source', 'audit-one', 'audit-two', 'output')
    for key in keys:
        parser.add_argument('--' + key, type=lambda p: Path(p).resolve(), required=True)
    parser.add_argument('--scope', choices=tuple(SCOPES), required=True)
    args = parser.parse_args()
    import os
    import subprocess
    import sys
    if os.environ.get('SCIENCE_UTOPIA_RESOURCE_COST_WORKER') == '1':
        export(args)
        return
    result = subprocess.run([sys.executable, '-B', '-c',
        'import runpy,sys;sys.path.insert(0,sys.argv.pop(1));runpy.run_path(sys.argv.pop(1),run_name="__main__")',
        str(args.frozen_source), str(Path(__file__).resolve()),
        *[v for key in keys for v in ('--' + key, str(getattr(args, key.replace('-', '_'))))],
        '--scope', args.scope], cwd=args.frozen_source,
        env={**os.environ, 'PYTHONHASHSEED': '42', 'SCIENCE_UTOPIA_RESOURCE_COST_WORKER': '1'},
        timeout=1800, check=False)
    if result.returncode:
        raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
