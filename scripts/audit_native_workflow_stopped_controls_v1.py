"""Cold audit of completed reference cells inside a stopped workflow study.

This separate scope never supplies normal study closure, own selections, a
held-out prerequisite, a missing observer-audit journal, or repaired proposals.
Original scientist/critic/checkpoint/ledger readers execute from frozen science
source; this external analysis adapter is independently pinned and hashed.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys

SCHEMA = 'scienceutopia.native-workflow-stopped-control-audit.v1'


def worker(root, output, adapter_source):
    from scripts import run_native_workflow_objective_loop_v1 as driver
    from scripts.analyze_native_open_v7 import _inventory
    from scripts.analyze_native_design_benchmark import loaded
    from scripts.audit_native_institution_loop_v1 import epoch
    from scripts.native_benchmark_source import source_proofs
    from scripts.native_benchmark_physical import physical_proof
    from scripts.native_observer_physical_v1 import ColdObserver, accepted_request_keys, reconstruct_measurement
    from scripts.reports.native_institution_effect_trace_v1 import trace_world
    from utopia.optimization.blackbox import Suggestion
    from utopia.optimization.loss import evaluate_loss, loss_spec_sha256
    from utopia.optimization.native_scientist_transport_v1 import require_cell_transport
    from utopia.optimization.native_workflow_designer_v1 import replay_workflow
    from utopia.optimization.native_workflow_domain_v4 import require_workflow_candidate, verify_workflow_interval
    from utopia.runtime.checkpointing import read_portable_checkpoint
    from utopia.system import SystemSpec
    from utopia.system.design_patch import digest
    from utopia.utils.data_utils import file_sha256
    root, output = Path(root).resolve(), Path(output).resolve()
    if output.exists() or output.is_relative_to(root) or output.is_relative_to(driver.ROOT):
        raise ValueError('fresh stopped-control report outside science raw/source required')
    read = driver.read
    literal = lambda v: {k: x for k, x in v.items() if k != 'content_sha256'}
    with (root / 'writer.lock').open('r') as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        before = _inventory(root); p = driver.require_plan(root)
        start, end = read(root / 'started.json'), read(root / 'terminal.json')
        if (start['schema'] != driver.SCHEMA + '.start' or start['plan_sha256'] != p['content_sha256']
                or end['schema'] != driver.SCHEMA + '.terminal' or end['status'] != 'stopped'
                or end.get('no_retry') is not True
                or epoch(end['ended_utc']) < epoch(start['started_utc'])
                or (root / 'selection.json').exists()):
            raise ValueError('literal stopped study without selection required')
        source = source_proofs(driver.ROOT, p['source_commit'], scripts=[
            'scripts/run_native_workflow_objective_loop_v1.py', 'scripts/native_benchmark_physical.py',
            'scripts/native_observer_physical_v1.py', 'scripts/reports/native_institution_effect_trace_v1.py'],
            resources=[driver.PROTOCOL] + ([p['operational_protocol']['path']] if 'operational_protocol' in p else []))
        anchor = SystemSpec.from_dict(p['initial_system'])
        observer = ColdObserver(root / 'observer', p['observer_contract'])
        # Only a returned read-only value: never write the absent original
        # observer-audit.json or imply the original writer finalized it.
        observer_audit = observer.audit()
        original_observer = read(root / 'observer-audit.json') if (root / 'observer-audit.json').is_file() else None
        if original_observer is not None and original_observer != observer_audit:
            raise ValueError('retained original critic audit differs')
        worlds, traces, cells, keys = [], [], set(), set()
        for label in p['reference_order']:
            directory = root / 'references' / label
            suggestion = Suggestion('workflow-reference-' + label.lower(), p['reference_systems'][label],
                0, 'developer-reference').to_dict()
            dispatched = read(directory / 'started.json'); o = read(directory / 'observation.json')
            spec = SystemSpec.from_dict(suggestion['candidate']); identity = suggestion['suggestion_id']
            require_workflow_candidate(anchor, spec, structure_only=True)
            m = o['metadata']
            if (dispatched['suggestion'] != suggestion or dispatched['seed'] != driver.SEED
                    or not epoch(start['started_utc']) <= epoch(dispatched['started_utc']) <= epoch(end['ended_utc'])
                    or o['status'] != 'complete' or o['candidate'] != suggestion['candidate']
                    or o['suggestion_id'] != identity or o['observation_id'] != 'observation-' + identity
                    or m['system_fingerprint'] != spec.fingerprint
                    or m['loss_spec_sha256'] != loss_spec_sha256(p['losses']['throughput'])
                    or m['world_backend'] != 'native-research-world'
                    or len(m['runs']) != 1 or len(m['measurements']) != 1 or m['technical_failures']):
                raise ValueError('completed reference identity/status/evidence differs')
            cell = directory / 'worlds' / (identity + '-s' + str(driver.SEED)); cells.add(cell)
            require_cell_transport(cell, p, spec, seed=driver.SEED, failed=False)
            gate = loaded(cell / 'role-load-000.json', cell / 'loaded-role-context-000.json',
                provider=p['scientist'], purpose='before-native-world:' + cell.name, role='scientist')
            proof = physical_proof(cell, spec, world=p['world'], seed=driver.SEED, years=4, evidence=m['runs'][0])
            state = read_portable_checkpoint(m['runs'][0]['checkpoint_path'])
            keys.update(accepted_request_keys(state, p['observer_contract']))
            interval = verify_workflow_interval(anchor, spec, state['native_system']['events'], years=4)
            rebuilt = {**reconstruct_measurement(state, proof['measurement'], observer), 'native_workflow_interval': interval}
            scores = {k: evaluate_loss(loss, [rebuilt]) for k, loss in p['losses'].items()}
            if (m['measurements'] != [rebuilt] or literal(read(directory / 'cross-scores.json')) != scores
                    or o['loss'] != scores['throughput']['loss'] or m['loss_evaluation'] != scores['throughput']):
                raise ValueError('completed reference checkpoint/critic/loss differs')
            world = {'identity': identity, 'role': 'developer-reference', 'objective': 'throughput',
                'seed': driver.SEED, 'system': spec.to_dict(), 'status': 'complete',
                'scores': {k: v['loss'] for k, v in scores.items()}, 'physical_proof': proof, 'loaded': gate}
            worlds.append(world); traces.append(trace_world(cell, world, p['source_commit'], workflow=True))
        actual_cells = {v.resolve() for v in root.glob('**/worlds/*') if v.is_dir()}
        if cells != actual_cells or not {r['key'] for r in observer_audit['rows']} <= keys:
            raise ValueError('unexpected nonreference world or critic request outside completed controls')
        authors = []
        for path in sorted(root.rglob('binding.json')):
            result = replay_workflow(path.parent)
            authors.append({'root_relative_path': str(path.parent.relative_to(root)),
                'result_sha256': result['content_sha256'], 'status': result['status'],
                'completion_unknown': result['completion_unknown'], 'technical_error': result['technical_error']})
        if before != _inventory(root): raise ValueError('stopped scientific raw changed during cold read')
        driver.save(output, {'schema': SCHEMA, 'source_commit': p['source_commit'],
            'plan_sha256': p['content_sha256'], 'source_proof': source,
            'external_adapter': {'source_commit': adapter_source, 'file_sha256': file_sha256(__file__)},
            'original_closure': {'started': start, 'terminal': end},
            'scientific_study_closed': False, 'selection': None, 'fixed_evaluation_eligible': False,
            'scope': 'Completed reference physical/critic/loss/ledger proofs and literal author replay only; not a full optimization-history or whole-study audit.',
            'worlds': worlds, 'effect_traces': traces, 'author_replays': authors,
            'critic_read_only_audit': observer_audit, 'original_observer_audit_present': original_observer is not None,
            'raw_inventory_sha256': digest(before), 'raw_files': len(before),
            'new_model_calls': 0, 'new_code_executions': 0, 'new_scientist_worlds': 0,
            'held_out_evaluation': False, 'publication_ready': False})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('run', 'frozen-source', 'output'): parser.add_argument('--' + key, type=Path, required=True)
    parser.add_argument('--adapter-source'); parser.add_argument('--worker', action='store_true')
    args = parser.parse_args()
    if args.worker:
        worker(args.run, args.output, args.adapter_source); return
    from utopia.optimization.native_jobs import pinned_revision
    adapter_source = pinned_revision(Path(__file__).resolve().parents[1])
    source = args.frozen_source.resolve()
    result = subprocess.run([sys.executable, '-c',
        'import runpy,sys;sys.path.insert(0,sys.argv.pop(1));runpy.run_path(sys.argv.pop(1),run_name="__main__")',
        str(source), str(Path(__file__).resolve()), '--worker', '--run', str(args.run.resolve()),
        '--frozen-source', str(source), '--output', str(args.output.resolve()), '--adapter-source', adapter_source],
        cwd=source, env={**os.environ, 'PYTHONHASHSEED': '42'}, timeout=1800, check=False)
    if result.returncode: raise SystemExit(result.returncode)


if __name__ == '__main__': main()
