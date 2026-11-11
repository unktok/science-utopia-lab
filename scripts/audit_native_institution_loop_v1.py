"""Cold audit of a closed native institution loop, using its original source.

The parent imports only stdlib. The overlay starts a fresh interpreter with the
explicit frozen checkout first on sys.path; no inference or authored execution.
An incomplete/stopped pilot must not be represented as a closed scientific run.
"""
import argparse
from datetime import datetime
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys


def epoch(value):
    parsed = datetime.fromisoformat(value)
    if parsed.tzinfo is None:
        raise ValueError('timezone-aware recorded timestamp required')
    return parsed.timestamp()


def require_age(started, completed):
    age = epoch(started)-completed
    if not 0 <= age <= 86400:
        raise ValueError('dispatch readiness was stale or future')
    return age


def request_at(controller, count):
    """Reconstruct the state actually available before this scheduled slot."""
    records = controller.state['records']
    if type(count) is not int or not 0 <= count <= len(records):
        raise ValueError('unavailable historical proposal prefix')
    strategy = controller._strategy_initial() if count == 0 else records[count-1]['report']['strategy_after']
    return controller._request(records[:count], strategy, 1)


def readiness_schedule(plan):
    counts = {arm: 0 for arm in plan['arm_order']}
    yield 'initial-readiness', False, dict(counts), 'throughput:code-and-graph'
    yield 'initial-readiness', True, dict(counts), None
    for slot in plan['schedule']:
        arm, generation = slot['arm'], slot['generation']
        if counts[arm] != generation:
            raise ValueError('invalid declared generation chronology')
        target = 'search/run-00/'+arm.replace(':', '--')+'/readiness-'+str(generation)
        yield target, plan['assignments'][arm]['method'] == 'parameters', dict(counts), arm
        counts[arm] += 1


def closed_state(root, plan, controllers, evaluation_count):
    from utopia.optimization.native_numeric_designer import checked
    read = lambda name: checked(json.loads((Path(root)/name).read_text()))
    start, end = read('started.json'), read('terminal.json')
    progress = json.loads((Path(root)/'progress.json').read_text())
    if (start['schema'] != plan['schema'].removesuffix('.plan')+'.start'
            or start['plan_sha256'] != plan['content_sha256']
            or end['status'] != 'closed' or set(end) != {'schema', 'status', 'ended_utc', 'content_sha256'}
            or end['schema'] != plan['schema'].removesuffix('.plan')+'.terminal'
            or epoch(end['ended_utc']) < epoch(start['started_utc'])):
        raise ValueError('normal source-bound loop closure required')
    rows = []
    for arm in plan['arm_order']:
        c = controllers[arm]
        if c.state['pending'] is not None or len(c.state['records']) != plan['generations']:
            raise ValueError('closed loop has incomplete candidate slots')
        for g, record in enumerate(c.state['records']):
            o = record['observations'][0] if record['observations'] else None
            rows.append({'arm': arm, 'generation': g,
                'status': 'generation-failure' if record['generation_error'] else o['status'] if o else 'unknown',
                'loss': o['loss'] if o else None})
    expected = {'schema': plan['schema'].removesuffix('.plan')+'.progress', 'stage': 'closed',
        'active': None, 'candidate_slots': rows, 'writer_pid': start['pid'],
        'reference_observations': len(plan['reference_order']), 'evaluation_observations': evaluation_count,
        'observed_utc': progress.get('observed_utc')}
    if progress != expected or not epoch(start['started_utc']) <= epoch(progress['observed_utc']) <= epoch(end['ended_utc']):
        raise ValueError('terminal progress differs from exact slots/chronology')
    return {'started': start, 'terminal': end, 'progress': progress}


def worker(root, output):
    from scripts import run_native_institution_loop_v1 as driver
    from scripts.analyze_native_open_v7 import _inventory
    from scripts.analyze_native_autonomous_search_v14 import replay_campaign
    from scripts.audit_pre_scale_search_v1 import actual_policy_order, forward_evidence
    from scripts.native_benchmark_physical import physical_proof
    from scripts.native_benchmark_source import source_proofs
    from scripts.analyze_native_design_benchmark import loaded
    from utopia.optimization.native_numeric_designer import checked, replay_numeric
    from utopia.optimization.native_bounded_staged_designer import replay as replay_editor
    from utopia.optimization.native_designer_preflight import require_certificate, EXECUTION_SCOPE
    from utopia.optimization.native_designer_tools_v25 import BOUNDED_AUTHORING
    from utopia.optimization.native_discrete_policy import verify_native_observation
    from utopia.optimization.blackbox import Observation
    from utopia.optimization.loss import evaluate_loss, loss_spec_sha256
    from utopia.system import SystemSpec
    from utopia.system.design_patch import clone, digest
    from utopia.utils.data_utils import file_sha256, write_json_atomic
    root, output, source = Path(root).resolve(), Path(output).resolve(), Path.cwd()
    if output.exists() or output.is_relative_to(source) or output.is_relative_to(root):
        raise ValueError('fresh external audit output required')
    read = lambda p: checked(json.loads(Path(p).read_text()))
    # Holding this advisory lock prevents a cooperating writer from starting.
    with (root/'writer.lock').open('r') as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        before = _inventory(root)
        plan = driver.require_plan(root)
        sources = source_proofs(source, plan['source_commit'], scripts=[
            'scripts/run_native_institution_loop_v1.py', 'scripts/native_benchmark_physical.py',
            'scripts/audit_pre_scale_search_v1.py', 'scripts/analyze_native_design_benchmark.py'],
            resources=[plan['protocol']])
        usages = [read(p) for p in sorted(root.glob('seed-usage-*.json'))]
        if (not usages or [u['content_sha256'] for u in usages] != plan['evaluation']['seed_usage']
                or any(not u['valid'] or u['errors'] or u['prior_matching_runs']
                    or u['seeds'] != [driver.SEED, *driver.EVALUATION_SEEDS] for u in usages)):
            raise ValueError('prospective development/evaluation seed inventory differs')
        rebuilt = driver.build_plan(source=plan['source_commit'], operator={k: plan[k]
            for k in ('scientist', 'designer', 'data_cache')}, backend=plan['backend'], seed_usage=usages)
        if rebuilt != {k:v for k,v in plan.items() if k != 'content_sha256'}:
            raise ValueError('frozen plan differs from original driver reconstruction')
        controllers = {}
        for arm in plan['arm_order']:
            c = replay_campaign(root/'search/run-00'/arm.replace(':', '--')/'campaign', 'blackbox')
            expected = {**clone(plan['campaign_bindings']['run-00'][arm]), 'mode':'blackbox',
                'learning_rate':.1, 'strategy_learning_rate':.1, 'strategy_baseline':0.,
                'exploration':.1, 'proposal_feedback':'matched-loss'}
            if c.binding != expected:
                raise ValueError('campaign binding differs')
            controllers[arm] = c
        selection = read(root/'selection.json')
        reconstructed = driver.selection_payload(root, plan, frozen_utc=selection['frozen_utc'],
            campaign_loader=lambda base, p, run, arm: controllers[arm])
        reconstructed['schema'] = driver.SCHEMA+'.selection'
        reconstructed['content_sha256'] = digest({k:v for k,v in reconstructed.items() if k != 'content_sha256'})
        if reconstructed != selection:
            raise ValueError('selection differs from all original candidates/ties/order')
        jobs = driver.evaluation_jobs(plan, selection)
        evaluation = read(root/'evaluation-plan.json')
        if {k:v for k,v in evaluation.items() if k != 'content_sha256'} != {
                'schema':driver.SCHEMA+'.evaluation-plan', 'selection_sha256':selection['content_sha256'], 'jobs':jobs}:
            raise ValueError('evaluation manifest differs from selection')
        closure = closed_state(root, plan, controllers, len(jobs))
        logical = actual_policy_order(plan, selection, jobs)
        expected_authors, expected_cells, expected_caches = set(), set(), set()
        numeric_certs, editor_certs, readiness = {}, {}, []

        class MetadataResponse:
            def __init__(self, data): self.data = data
            def raise_for_status(self): pass
            def json(self): return self.data

        class RecordedBackend:
            def get(self, url, timeout):
                if url.endswith('/api/version'):
                    return MetadataResponse({'version':plan['backend']['ollama_version']})
                if url.endswith('/api/tags'):
                    return MetadataResponse({'models':[{'name':plan['designer']['model'],
                        'digest':plan['designer']['model_digest']}]})
                raise ValueError('offline metadata adapter cannot dispatch')

        for target, numeric, counts, arm in readiness_schedule(plan):
            base = root/target
            if numeric:
                cert = read(base/'numeric-readiness/certificate.json')
                if (not cert['passed'] or cert['unattempted_cases'] or cert['provider'] != plan['designer']
                        or cert['backend'] != plan['backend'] or cert['runtime'] != plan['runtime']
                        or [v['objective'] for v in cert['cases']] != plan['objectives']):
                    raise ValueError('numeric readiness differs from exact source/roles/objectives')
                for case in cert['cases']:
                    directory = base/case['journal_relative']; expected_authors.add(directory.resolve())
                    result = replay_numeric(directory); binding = read(directory/'binding.json')
                    key = case['objective']+':parameters'
                    if (not case['submitted'] or result['definition'] is None
                            or binding['request'] != request_at(controllers[key], counts[key])
                            or binding['provider'] != plan['designer'] or binding['backend'] != plan['backend']
                            or binding['runtime'] != plan['runtime'] or binding['calibration'] is not True
                            or binding['settings'] != cert['settings']
                            or file_sha256(directory/'result.json') != case['result_sha256']):
                        raise ValueError('numeric readiness literal/request replay differs')
                numeric_certs[target] = cert
            else:
                directory = base/'editor-readiness'; replay_editor(directory)
                cert = read(directory/'calibration/certificate.json')
                proof = require_certificate(directory/'calibration/certificate.json', plan['designer'],
                    protocol='staged-v15', session=RecordedBackend(), now=cert['completed_epoch'],
                    scope=EXECUTION_SCOPE, conversation_profile=BOUNDED_AUTHORING)
                intent = read(directory/'intent.json')
                if (cert['plan']['backend'] != plan['backend'] or cert['plan']['runtime'] != plan['runtime']
                        or cert['plan']['request'] != request_at(controllers[arm], counts[arm])
                        or intent['request'] != cert['plan']['request'] or intent['provider'] != plan['designer']
                        or intent['source_commit'] != plan['source_commit']):
                    raise ValueError('editor readiness request/source/roles differs')
                editor_certs[target] = cert
                cert = {**cert, 'cold_proof':proof}
            readiness.append({'target':target, 'numeric':numeric, 'certificate':cert})

        worlds = []
        def physical(directory, identity, system, seed, role, observation=None, loss_name='throughput'):
            spec = SystemSpec.from_dict(system); standalone = observation is None
            o = read(directory/'observation.json') if standalone else observation
            if standalone:
                started = read(directory/'started.json')
                if (started['identity'], started['system'], started['seed'], started['role']) != (identity, system, seed, role):
                    raise ValueError('world dispatch differs from fixed job')
                if role == 'selection-fixed-evaluation' and epoch(started['started_utc']) < epoch(selection['frozen_utc']):
                    raise ValueError('evaluation precedes frozen selection')
                if role == 'developer-reference':
                    completed = max(editor_certs['initial-readiness']['completed_epoch'],
                        numeric_certs['initial-readiness']['created_unix_seconds'])
                    if epoch(started['started_utc']) < completed:
                        raise ValueError('reference precedes initial readiness')
            if (o['suggestion_id'] != identity or o['candidate'] != system
                    or o['metadata']['system_fingerprint'] != spec.fingerprint
                    or o['metadata']['world_backend'] != 'native-research-world'
                    or o['metadata']['loss_spec_sha256'] != loss_spec_sha256(plan['losses'][loss_name])):
                raise ValueError('observation identity/system/loss differs')
            cell = directory/'worlds'/(identity+'-s'+str(seed)); expected_cells.add(cell.resolve())
            if not cell.is_dir(): raise ValueError('missing physical world')
            cache = cell/'replies/responses.sqlite'
            if cache.exists():
                if cache.resolve() in expected_caches: raise ValueError('scientist response cache reused')
                expected_caches.add(cache.resolve())
            gate = loaded(cell/'role-load-000.json', cell/'loaded-role-context-000.json', provider=plan['scientist'],
                purpose='before-native-world:'+cell.name, role='scientist', allow_unconfirmed=o['status']=='failed')
            if forward_evidence(o):
                if o['status'] == 'complete': verify_native_observation(Observation.from_dict(o), plan['world'], [seed])
                proof = physical_proof(cell, spec, world=plan['world'], seed=seed, years=4, evidence=o['metadata']['runs'][0])
                if o['metadata']['measurements'] != [proof['measurement']]: raise ValueError('checkpoint measurement differs')
            else:
                if cache.exists() and not gate['confirmed']: raise ValueError('unconfirmed scientist load before responses')
                proof = physical_proof(cell, spec, world=plan['world'], seed=seed, years=4) if cache.exists() else {'status':'pre-response-journal-failure'}
            scores = {k:evaluate_loss(v, o['metadata']['measurements']) for k,v in plan['losses'].items()}
            if (o['loss'] != scores[loss_name]['loss'] or o['metadata']['loss_evaluation'] != scores[loss_name]
                    or (o['status']=='complete') != (scores[loss_name]['status']=='complete')):
                raise ValueError('loss/status differs from raw components')
            if standalone and {k:v for k,v in read(directory/'cross-scores.json').items() if k != 'content_sha256'} != scores:
                raise ValueError('cross-scores differ from raw components')
            worlds.append({'identity':identity, 'role':role, 'seed':seed, 'system':system, 'status':o['status'],
                'scores':{k:v['loss'] for k,v in scores.items()}, 'physical_proof':proof, 'loaded':gate})

        for name in plan['reference_order']:
            physical(root/'references'/name, 'reference-'+name, plan['reference_systems'][name], driver.SEED, 'developer-reference')
        authoring = []
        for slot in plan['schedule']:
            arm, g = slot['arm'], slot['generation']; record = controllers[arm].state['records'][g]
            directory = root/'search/run-00'/arm.replace(':', '--')
            generation = directory/'authoring'/('generation-'+record['request_sha256'])
            expected_authors.add(generation.resolve()); target = str((directory/f'readiness-{g}').relative_to(root))
            if plan['assignments'][arm]['method'] == 'parameters':
                result = replay_numeric(generation); binding = read(generation/'binding.json'); cert = numeric_certs[target]
                if (binding['request'] != record['request'] or binding['provider'] != plan['designer']
                        or binding['backend'] != plan['backend'] or binding['calibration'] is not False
                        or binding['settings'] != cert['settings'] or result['definition'] != record['definition']):
                    raise ValueError('numeric production differs from literal/readiness')
                for intent in generation.glob('call-*.intent.json'):
                    require_age(read(intent)['started_utc'], cert['created_unix_seconds'])
            else:
                definition = replay_editor(generation); intent = read(generation/'intent.json'); cert = editor_certs[target]
                if (intent['request'] != record['request'] or intent['provider'] != plan['designer']
                        or intent['certificate'] != str((root/target/'editor-readiness/calibration/certificate.json').resolve())
                        or definition != record['definition']):
                    raise ValueError('editor production differs from literal/readiness')
                for intent_path in (generation/'wire').glob('dispatch-*.intent.json'):
                    require_age(read(intent_path)['started_utc'], cert['completed_epoch'])
            authoring.append({'arm':arm, 'generation':g, 'request_sha256':record['request_sha256'],
                'generation_error':record['generation_error'], 'definition':record['definition'], 'raw_directory':str(generation)})
            for draw, o in zip(record['draws'], record['observations']):
                if o is not None:
                    physical(directory, draw['suggestion']['suggestion_id'], o['candidate'], driver.SEED,
                        'search:'+arm, observation=o, loss_name=plan['assignments'][arm]['objective'])
        for job in jobs:
            physical(root/'evaluation'/job['identity'], job['identity'], job['system'], job['seed'], 'selection-fixed-evaluation')
        if expected_cells != {p.resolve() for p in root.glob('**/worlds/*') if p.is_dir()}:
            raise ValueError('unaccounted physical world')
        if expected_caches != {p.resolve() for p in root.rglob('responses.sqlite')}:
            raise ValueError('unaccounted physical response cache')
        actual_authors = {p.parent.resolve() for p in root.rglob('binding.json')
            if p.parent.name.startswith('generation-')}
        actual_authors.update(p.parent.resolve() for p in (root/'search').glob('run-00/*/authoring/generation-*/intent.json'))
        if expected_authors != actual_authors: raise ValueError('unaccounted authoring journal')
        if {p.name for p in (root/'references').iterdir()} != set(plan['reference_order']):
            raise ValueError('unaccounted reference slot')
        if {p.name for p in (root/'evaluation').iterdir()} != {j['identity'] for j in jobs}:
            raise ValueError('unaccounted evaluation slot')
        if before != _inventory(root): raise ValueError('raw study changed during read-only audit')
        result = {'schema':'scienceutopia.native-institution-loop-audit.v1', 'source_commit':plan['source_commit'],
            'plan_sha256':plan['content_sha256'], 'source_proof':sources, 'closure':closure, 'worlds':worlds,
            'authoring':authoring, 'selection':selection, 'logical_evaluation':logical, 'readiness':readiness,
            'raw_inventory_sha256':digest(before), 'raw_files':len(before),
            'analysis_adapter_sha256':file_sha256(Path(__file__)), 'new_model_calls':0, 'new_code_executions':0,
            'historical_backend_metadata_scope':'Saved source-owned metadata for cold replay, not fresh backend verification',
            'analysis_scope':'Overlay adapter; native/driver imports from unchanged original clean source'}
        result['content_sha256'] = digest(result)
        write_json_atomic(output, result, sort_keys=True, allow_nan=False)
        print(json.dumps({'audit':str(output), 'content_sha256':result['content_sha256'], 'physical_worlds':len(worlds)}))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True); parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--frozen-source', type=Path); parser.add_argument('--worker', action='store_true')
    args = parser.parse_args()
    if args.worker: worker(args.run, args.output); return
    if args.frozen_source is None or not (args.run/'terminal.json').exists():
        raise ValueError('closed study and explicit frozen source required; never audit a live writer')
    if json.loads((args.run/'terminal.json').read_text()).get('status') != 'closed':
        raise ValueError('stopped study is not closed scientific evidence')
    script = Path(__file__).resolve(); before = hashlib.sha256(script.read_bytes()).hexdigest()
    command = [sys.executable, '-c',
        'import runpy,sys; sys.path.insert(0,sys.argv.pop(1)); runpy.run_path(sys.argv.pop(1),run_name="__main__")',
        str(args.frozen_source.resolve()), str(script), '--worker', '--run', str(args.run.resolve()), '--output', str(args.output.resolve())]
    result = subprocess.run(command, cwd=args.frozen_source.resolve(), env={**os.environ, 'PYTHONHASHSEED':'42'}, timeout=1800, check=False)
    if hashlib.sha256(script.read_bytes()).hexdigest() != before: raise ValueError('analysis adapter changed during audit')
    if result.returncode: raise SystemExit(result.returncode)


if __name__ == '__main__': main()
