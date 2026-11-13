"""Cold deterministic ask/tell and original native proof for numeric comparison."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys


def worker(root, output):
    from scripts import run_native_parameter_comparator_v1 as driver
    from scripts.analyze_native_open_v7 import _inventory
    from scripts.analyze_native_design_benchmark import loaded
    from scripts.audit_native_institution_loop_v1 import epoch
    from scripts.native_benchmark_source import source_proofs
    from scripts.native_benchmark_physical import physical_proof
    from scripts.native_observer_physical_v1 import ColdObserver, accepted_request_keys, reconstruct_measurement
    from utopia.optimization.blackbox import Observation
    from utopia.optimization.loss import evaluate_loss, loss_spec_sha256
    from utopia.optimization.native_discrete_policy import verify_native_observation
    from utopia.runtime.checkpointing import read_portable_checkpoint
    from utopia.system import SystemSpec
    from utopia.system.design_patch import digest
    root, output = Path(root).resolve(), Path(output).resolve(); read = driver.read
    if output.exists() or output.is_relative_to(root) or output.is_relative_to(driver.ROOT):
        raise ValueError('fresh audit outside original raw/source required')
    def literal(value): return {k: v for k, v in value.items() if k != 'content_sha256'}
    with (root / 'writer.lock').open('r') as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        before = _inventory(root); p = driver.require_plan(root)
        start, end = read(root / 'started.json'), read(root / 'terminal.json')
        if (start['schema'] != driver.SCHEMA + '.start' or end['schema'] != driver.SCHEMA + '.terminal'
                or start['plan_sha256'] != p['content_sha256'] or end['status'] != 'closed'
                or end['stage'] != 'closed' or end['consumed_slots'] != 6 or end['completed_observations'] != 6
                or epoch(start['started_utc']) > epoch(end['ended_utc'])):
            raise ValueError('normally closed exact six-slot numeric study required')
        source = source_proofs(driver.ROOT, p['source_commit'], scripts=[
            'scripts/run_native_parameter_comparator_v1.py', 'scripts/audit_native_parameter_comparator_v1.py',
            'scripts/native_benchmark_physical.py', 'scripts/native_observer_physical_v1.py'], resources=[driver.PROTOCOL])
        observer = ColdObserver(root / 'observer', p['observer_contract']); observer_audit = observer.audit()
        if observer_audit != read(root / 'observer-audit.json'): raise ValueError('literal observer cold audit differs')
        optimizers = {o: driver.optimizer_for(p, o) for o in p['objectives']}
        for o in p['objectives']:
            if literal(read(root / 'search' / o / 'initial-state.json')) != optimizers[o].state_dict():
                raise ValueError('literal warmed reference state differs')
        observations = {o: [] for o in p['objectives']}
        cells, caches, keys, directories, worlds = set(), set(), set(), set(), []
        previous_epoch = epoch(start['started_utc'])
        for slot in p['schedule']:
            objective, generation = slot['objective'], slot['generation']
            directory = root / 'search' / objective / ('generation-' + str(generation)); directories.add(directory)
            dispatched = read(directory / 'started.json'); optimizer = optimizers[objective]
            suggestion = optimizer.ask()[0]
            expected = {'plan_sha256': p['content_sha256'], 'objective': objective, 'generation': generation,
                'seed': driver.SEED, 'suggestion': suggestion.to_dict(), 'optimizer_after_ask': optimizer.state_dict()}
            at = epoch(dispatched['started_utc'])
            if (literal(dispatched) != {**expected, 'started_utc': dispatched['started_utc']}
                    or not previous_epoch <= at <= epoch(end['ended_utc'])):
                raise ValueError('numeric proposal/state/order differs from deterministic cold ask')
            previous_epoch = at
            o = read(directory / 'observation.json'); spec = SystemSpec.from_dict(suggestion.candidate); m = o['metadata']
            if (o['suggestion_id'] != suggestion.suggestion_id or o['candidate'] != suggestion.candidate
                    or o['observation_id'] != 'observation-' + suggestion.suggestion_id
                    or m['world_backend'] != 'native-research-world' or m['system_fingerprint'] != spec.fingerprint
                    or m['loss_spec_sha256'] != loss_spec_sha256(p['losses'][objective])):
                raise ValueError('literal numeric observation identity/loss differs')
            cell = directory / 'worlds' / (suggestion.suggestion_id + '-s' + str(driver.SEED)); cells.add(cell)
            if not cell.is_dir(): raise ValueError('original numeric native-world directory required')
            cache = cell / 'replies/responses.sqlite'
            if cache.exists(): caches.add(cache)
            gate = loaded(cell / 'role-load-000.json', cell / 'loaded-role-context-000.json', provider=p['scientist'],
                purpose='before-native-world:' + cell.name, role='scientist', allow_unconfirmed=o['status'] == 'failed')
            runs, measurements = m['runs'], m['measurements']
            if len(runs) > 1 or len(measurements) > 1 or (measurements and not runs):
                raise ValueError('ambiguous numeric native observation')
            if runs:
                proof = physical_proof(cell, spec, world=p['world'], seed=driver.SEED, years=4, evidence=runs[0])
                state = read_portable_checkpoint(runs[0]['checkpoint_path'])
                keys.update(accepted_request_keys(state, p['observer_contract']))
                if measurements:
                    rebuilt = reconstruct_measurement(state, proof['measurement'], observer)
                    if measurements != [rebuilt] or m['technical_failures']:
                        raise ValueError('numeric measurement differs from original native state/critic responses')
                    verify_native_observation(Observation.from_dict(o), p['world'], [driver.SEED])
                elif o['status'] != 'failed' or not m['technical_failures']:
                    raise ValueError('missing numeric measurement without technical failure')
            else:
                if o['status'] != 'failed' or not m['technical_failures']:
                    raise ValueError('unobserved numeric world cannot acquire a loss')
                if cache.exists() and not gate['confirmed']: raise ValueError('replies follow unconfirmed scientist load')
                proof = (physical_proof(cell, spec, world=p['world'], seed=driver.SEED, years=4)
                    if cache.exists() else {'status': 'pre-response-journal-failure'})
            scores = {k: evaluate_loss(v, measurements) for k, v in p['losses'].items()}
            if (o['loss'] != scores[objective]['loss'] or m['loss_evaluation'] != scores[objective]
                    or (o['status'] == 'complete') != (scores[objective]['status'] == 'complete')
                    or literal(read(directory / 'cross-scores.json')) != scores):
                raise ValueError('numeric literal cross-score/status differs')
            optimizer.tell([Observation.from_dict(o)])
            if literal(read(directory / 'optimizer-after-tell.json')) != optimizer.state_dict():
                raise ValueError('numeric posterior state differs from original scalar feedback')
            observations[objective].append(Observation.from_dict(o).to_dict())
            worlds.append({'objective': objective, 'generation': generation, 'identity': suggestion.suggestion_id,
                'role': 'numeric-own-proposal', 'system': suggestion.candidate, 'status': o['status'],
                'scores': {k: v['loss'] for k, v in scores.items()}, 'physical_proof': proof, 'loaded': gate})
        selected = driver.selection(p, observations)
        if literal(read(root / 'selection.json')) != selected: raise ValueError('own-only numeric selection differs')
        if (cells != {v.resolve() for v in root.glob('**/worlds/*') if v.is_dir()}
                or caches != {v.resolve() for v in root.rglob('responses.sqlite')}
                or directories != {v.resolve() for v in (root / 'search').glob('*/generation-*') if v.is_dir()}
                or set(optimizers) != {v.name for v in (root / 'search').iterdir()}
                or not {r['key'] for r in observer_audit['rows']} <= keys
                or list(root.rglob('dispatch-*.intent.json'))):
            raise ValueError('unaccounted numeric world/cache/slot/critic/designer intent')
        progress = json.loads((root / 'progress.json').read_text())
        if progress['stage'] != 'closed' or progress['active'] is not None: raise ValueError('final numeric progress differs')
        if before != _inventory(root): raise ValueError('numeric raw changed during cold proof')
        result = {'schema': 'scienceutopia.native-parameter-comparator-audit.v1', 'source_commit': p['source_commit'],
            'plan_sha256': p['content_sha256'], 'source_proof': source, 'closure': {'started': start, 'terminal': end},
            'origin_audit_content_sha256': p['origin_audit_content_sha256'], 'reused_reference_worlds': 8,
            'worlds': worlds, 'selection': read(root / 'selection.json'), 'observer': observer_audit,
            'raw_inventory_sha256': digest(before), 'raw_files': len(before), 'new_model_calls': 0,
            'new_code_executions': 0, 'held_out_evaluation': False, 'independent_optimizer_replications': False,
            'publication_ready': False}
        driver.save(output, result)
        print(json.dumps({'audit': str(output), 'worlds': len(worlds)}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('run', 'frozen-source', 'output'): parser.add_argument('--' + key, type=Path, required=True)
    parser.add_argument('--worker', action='store_true'); args = parser.parse_args()
    if args.worker: worker(args.run, args.output); return
    if json.loads((args.run / 'terminal.json').read_text())['status'] != 'closed':
        raise ValueError('normal numeric study closure required')
    result = subprocess.run([sys.executable, '-c',
        'import runpy,sys;sys.path.insert(0,sys.argv.pop(1));runpy.run_path(sys.argv.pop(1),run_name="__main__")',
        str(args.frozen_source.resolve()), str(Path(__file__).resolve()), '--worker', '--run', str(args.run.resolve()),
        '--frozen-source', str(args.frozen_source.resolve()), '--output', str(args.output.resolve())], cwd=args.frozen_source,
        env={**os.environ, 'PYTHONHASHSEED': '42'}, timeout=1800, check=False)
    if result.returncode: raise SystemExit(result.returncode)


if __name__ == '__main__': main()
