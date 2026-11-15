"""Read-only original-source replay of native workflow proposals and worlds."""
import argparse
import fcntl
import json
import os
from pathlib import Path
import subprocess
import sys


def worker(root, output, *, driver_module=None):
    if driver_module is None:
        from scripts import run_native_workflow_objective_loop_v1 as driver
    else:
        driver = driver_module
    from scripts.analyze_native_open_v7 import _inventory
    from scripts.analyze_native_design_benchmark import loaded
    from scripts.audit_native_institution_loop_v1 import epoch, require_age
    from scripts.native_benchmark_source import source_proofs
    from scripts.native_benchmark_physical import physical_proof
    from scripts.native_observer_physical_v1 import ColdObserver, accepted_request_keys, reconstruct_measurement
    from utopia.optimization.blackbox import Observation, Suggestion
    from utopia.optimization.loss import evaluate_loss, loss_spec_sha256
    from utopia.optimization.native_development_references import build_context
    from utopia.optimization.native_workflow_designer_v1 import replay_workflow, require_certificate, generation_definition
    from utopia.optimization.native_workflow_domain_v4 import require_workflow_candidate, verify_workflow_interval
    check_candidate = getattr(driver, 'require_candidate', require_workflow_candidate)
    check_interval = getattr(driver, 'verify_interval', verify_workflow_interval)
    from utopia.runtime.checkpointing import read_portable_checkpoint
    from utopia.system import SystemSpec
    from utopia.system.design_patch import clone, digest
    root, output = Path(root).resolve(), Path(output).resolve(); read = driver.read
    if output.exists() or output.is_relative_to(root) or output.is_relative_to(driver.ROOT):
        raise ValueError('fresh workflow audit outside raw/source required')
    literal = lambda v: {k: x for k, x in v.items() if k != 'content_sha256'}
    with (root / 'writer.lock').open('r') as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        before = _inventory(root); p = driver.require_plan(root)
        start, end = read(root / 'started.json'), read(root / 'terminal.json')
        if (start['schema'] != driver.SCHEMA + '.start' or start['plan_sha256'] != p['content_sha256']
                or end['schema'] != driver.SCHEMA + '.terminal' or end['status'] != 'closed'
                or end['stage'] != 'closed' or end['consumed_slots'] != len(p['schedule'])
                or epoch(end['ended_utc']) < epoch(start['started_utc'])):
            raise ValueError('normally closed exact declared workflow study required')
        author_sources = (['utopia/optimization/native_open_workflow_submission_v1.py',
            'utopia/optimization/native_workflow_designer_v1.py',
            'utopia/optimization/native_authoring_ir.py',
            'utopia/optimization/native_search_generator_v14.py'] if driver.open_institutions(p) else [])
        staged = p.get('designer_mode') == driver.staged_author.MODE
        if staged:
            author_sources += ['utopia/optimization/native_workflow_staged_designer_v1.py',
                'scripts/reports/stage_native_component_fixtures_v1.py']
        source = source_proofs(driver.ROOT, p['source_commit'], scripts=[
            'scripts/run_native_workflow_objective_loop_v1.py', 'scripts/audit_native_workflow_objective_loop_v1.py',
            'scripts/native_benchmark_physical.py', 'scripts/native_observer_physical_v1.py'] + author_sources
                + getattr(driver, 'AUDIT_SCRIPTS', []),
            resources=[p['protocol']] + ([p['eligibility_protocol']['path']] if 'eligibility_protocol' in p else [])
                + ([p['operational_protocol']['path']] if 'operational_protocol' in p else [])
                + ([p['author_profile_protocol']['path']] if 'author_profile_protocol' in p else []))
        anchor = SystemSpec.from_dict(p['initial_system'])
        observer = ColdObserver(root / 'observer', p['observer_contract']); observer_audit = observer.audit()
        if observer_audit != read(root / 'observer-audit.json'): raise ValueError('original critic audit differs')
        cells, caches, author_roots, keys, worlds = set(), set(), set(), set(), []
        staged_wire_directories = set()
        def author(parent, request, *, proposal=False):
            calibration = parent / ('calibration-' + digest(request)); author_roots.add(calibration)
            if staged:
                from utopia.optimization.native_bounded_staged_designer import replay as replay_bounded
                def cold(path, purpose):
                    value = driver.staged_author.replay(path, request=request, provider=p['designer'],
                        backend=p['backend'], source_commit=p['source_commit'], bank=p['component_bank'], purpose=purpose)
                    session = path/('editor-readiness' if purpose=='calibration' else 'editor-session')
                    wire = session/'wire'; staged_wire_directories.add(wire.resolve())
                    for intent_path in wire.glob('dispatch-*.intent.json'):
                        intent = read(intent_path)
                        if not epoch(start['started_utc']) <= epoch(intent['started_utc']) <= epoch(end['ended_utc']):
                            raise ValueError('staged workflow dispatch outside original study interval')
                    return value, session
                value, calibration_session = cold(calibration, 'calibration')
                certificate_path = calibration_session/'calibration/certificate.json'
                cert = driver.staged_author.cold_certificate(certificate_path, request=request,
                    provider=p['designer'], backend=p['backend'], contract=p['post_edit_contract'])
                if proposal:
                    path = parent/('proposal-'+digest(request)); author_roots.add(path)
                    value, session = cold(path, 'proposal')
                    intent = read(session/'intent.json')
                    if intent['certificate'] != str(certificate_path.resolve()):
                        raise ValueError('staged workflow proposal used a different readiness certificate')
                    for intent_path in (session/'wire').glob('dispatch-*.intent.json'):
                        require_age(read(intent_path)['started_utc'], cert['completed_epoch'])
                return value
            cert = require_certificate(calibration / 'certificate.json', request=request,
                provider=p['designer'], backend=p['backend'], enforce_age=False, settings=p['author_settings'])
            value = replay_workflow(calibration)
            if proposal:
                path = parent / ('proposal-' + digest(request)); author_roots.add(path)
                value = replay_workflow(path)
            if value['completion_unknown']: raise ValueError('normal workflow study cannot contain an unknown dispatch')
            path = path if proposal else calibration
            intent = read(path / 'call.intent.json')
            if not epoch(start['started_utc']) <= epoch(intent['started_utc']) <= epoch(value['ended_utc']) <= epoch(end['ended_utc']):
                raise ValueError('workflow dispatch interval exceeds original study')
            if proposal and not 0 <= epoch(intent['started_utc']) - cert['created_unix_seconds'] <= 86400:
                raise ValueError('workflow actual dispatch did not have a fresh readiness certificate')
            return value
        initial_jobs = (driver.initial_readiness_jobs(p) if hasattr(driver, 'initial_readiness_jobs')
                        else [(p['objectives'][0], Path('initial-readiness'))])
        for initial_key, relative in initial_jobs:
            initial_file = root / relative / 'campaign/native-adaptive-state.json'
            if not initial_file.is_file(): raise ValueError('original workflow initial campaign missing')
            initial = driver.campaign(root, p, initial_key, prototype=True)
            if initial.state['records'] or initial.state['pending']: raise ValueError('initial readiness dispatched science')
            author(root / relative / 'author', initial._request([], initial._validate(), 1))
        def physical(directory, suggestion, o, objective, role, history=None):
            spec = SystemSpec.from_dict(suggestion['candidate'])
            check_candidate(anchor, spec, structure_only=not driver.open_institutions(p))
            m = o['metadata']; identity = suggestion['suggestion_id']
            if (o['candidate'] != suggestion['candidate'] or o['suggestion_id'] != identity
                    or o['observation_id'] != 'observation-' + identity or m['system_fingerprint'] != spec.fingerprint
                    or m['loss_spec_sha256'] != loss_spec_sha256(p['losses'][objective])
                    or m['world_backend'] != 'native-research-world'):
                raise ValueError('workflow actual native observation identity differs')
            cell = directory / 'worlds' / (identity + '-s' + str(driver.SEED)); cells.add(cell)
            from utopia.optimization.native_scientist_transport_v1 import require_cell_transport
            require_cell_transport(cell, p, spec, seed=driver.SEED, failed=o['status'] == 'failed')
            cache = cell / 'replies/responses.sqlite'
            if cache.is_file(): caches.add(cache)
            gate = loaded(cell / 'role-load-000.json', cell / 'loaded-role-context-000.json', provider=p['scientist'],
                purpose='before-native-world:' + cell.name, role='scientist', allow_unconfirmed=o['status'] == 'failed')
            runs, measurements = m['runs'], m['measurements']
            if len(runs) > 1 or len(measurements) > 1 or (measurements and not runs):
                raise ValueError('ambiguous workflow native evidence')
            if runs:
                proof = physical_proof(cell, spec, world=p['world'], seed=driver.SEED, years=4, evidence=runs[0])
                state = read_portable_checkpoint(runs[0]['checkpoint_path'])
                keys.update(accepted_request_keys(state, p['observer_contract']))
                if measurements:
                    interval = check_interval(anchor, spec, state['native_system']['events'], years=4)
                    rebuilt = {**reconstruct_measurement(state, proof['measurement'], observer), 'native_workflow_interval': interval}
                    if hasattr(driver, 'reconstruct_extra_measurement'):
                        rebuilt = driver.reconstruct_extra_measurement(p, state, rebuilt, runs[0])
                    if measurements != [rebuilt] or m['technical_failures']:
                        raise ValueError('workflow measurement differs from original checkpoint/critic/event data')
                elif o['status'] != 'failed' or not m['technical_failures']:
                    raise ValueError('workflow missing completed-world measurement without a technical failure')
            else:
                if o['status'] != 'failed' or not m['technical_failures']: raise ValueError('missing native world without failure')
                if cache.is_file() and not gate['confirmed']: raise ValueError('native responses follow an unconfirmed load')
                proof = physical_proof(cell, spec, world=p['world'], seed=driver.SEED, years=4) if cache.is_file() else None
            scores = {k: evaluate_loss(v, measurements) for k, v in p['losses'].items()}
            if (o['loss'] != scores[objective]['loss'] or m['loss_evaluation'] != scores[objective]
                    or (o['status'] == 'complete') != (scores[objective]['status'] == 'complete')):
                raise ValueError('workflow original assigned loss/status differs')
            worlds.append({'identity': identity, 'role': role, 'objective': objective, 'seed': driver.SEED,
                'system': spec.to_dict(), 'status': o['status'], 'scores': {k: v['loss'] for k, v in scores.items()},
                'physical_proof': proof, 'loaded': gate,
                **({} if history is None else driver.history_metadata(history))})
            return scores
        pairs = []
        for label in p['reference_order']:
            directory = root / 'references' / label; dispatched = read(directory / 'started.json')
            s = Suggestion('workflow-reference-' + label.lower(), p['reference_systems'][label], 0, 'developer-reference').to_dict()
            if dispatched['suggestion'] != s or dispatched['seed'] != driver.SEED:
                raise ValueError('literal workflow reference dispatch differs')
            o = read(directory / 'observation.json'); scores = physical(directory, s, o, 'throughput', 'developer-reference')
            if o['status'] != 'complete' or literal(read(directory / 'cross-scores.json')) != scores:
                raise ValueError('normally closed workflow references must be complete')
            pairs.append({'suggestion': s, 'observation': Observation.from_dict(o).to_dict()})
        context = driver.reference_context(p, pairs)
        if context != read(root / 'developer-reference-context.json'): raise ValueError('workflow common bank differs')
        campaigns = {}
        for key in driver.history_keys(p):
            if not (driver.history_directory(root, key) / 'campaign/native-adaptive-state.json').is_file():
                raise ValueError('original workflow campaign missing')
            c = driver.campaign(root, p, key, context)
            if c.state['pending'] or len(c.state['records']) != p.get('generations', 3):
                raise ValueError('workflow declared own slots not terminal')
            campaigns[key] = c
        for slot in p['schedule']:
            objective, g = slot['objective'], slot['generation']; key = driver.history_key(slot); c = campaigns[key]
            record = c.state['records'][g]
            result = author(driver.history_directory(root, key) / 'authoring', record['request'], proposal=True)
            if generation_definition(result) != record['definition']:
                raise ValueError('workflow generated definition differs from exact received operations')
            for draw, o in zip(record['draws'], record['observations']):
                if draw['suggestion'] is not None:
                    if o is None: raise ValueError('workflow compiled draw lacks its consumed observation')
                    physical(driver.history_directory(root, key), draw['suggestion'], o, objective,
                        'workflow-own-proposal', history=key)
        if literal(read(root / 'selection.json')) != driver.selection(root, p, context):
            raise ValueError('workflow original own-only selection differs')
        if (cells != {v.resolve() for v in root.glob('**/worlds/*') if v.is_dir()}
                or caches != {v.resolve() for v in root.rglob('responses.sqlite')}
                or author_roots != {v.parent.resolve() for v in root.rglob('binding.json')}
                or not {r['key'] for r in observer_audit['rows']} <= keys
                or end['observations'] != len(worlds)):
            raise ValueError('unaccounted workflow world/cache/author/critic slot')
        if staged and staged_wire_directories != {v.parent.resolve() for v in root.rglob('dispatch-*.intent.json')}:
            raise ValueError('unaccounted staged workflow calibration/proposal dispatch directory')
        if before != _inventory(root): raise ValueError('workflow raw changed during cold audit')
        driver.save(output, {'schema': getattr(driver, 'AUDIT_SCHEMA', 'scienceutopia.native-workflow-objective-loop-audit.v1'),
            'source_commit': p['source_commit'], 'plan_sha256': p['content_sha256'], 'source_proof': source,
            'closure': {'started': start, 'terminal': end}, 'worlds': worlds, 'selection': read(root / 'selection.json'),
            'observer': observer_audit, 'raw_inventory_sha256': digest(before), 'raw_files': len(before),
            'new_model_calls': 0, 'new_code_executions': 0, 'held_out_evaluation': False, 'publication_ready': False})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('run', 'frozen-source', 'output'): parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--worker', action='store_true'); args = parser.parse_args()
    if args.worker: worker(args.run, args.output); return
    result = subprocess.run([sys.executable, '-m', 'scripts.audit_native_workflow_objective_loop_v1', '--worker',
        '--run', str(args.run.resolve()), '--frozen-source', str(args.frozen_source.resolve()),
        '--output', str(args.output.resolve())], cwd=args.frozen_source,
        env={**os.environ, 'PYTHONHASHSEED': '42'}, timeout=1800, check=False)
    if result.returncode: raise SystemExit(result.returncode)


if __name__ == '__main__': main()
