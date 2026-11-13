"""Finite parameter-only T/U continuation of a closed native planning study.

Reuse its exact audited common reference bank, not its own authored outcomes.
Each of two three-slot numeric histories starts at its loss-selected reference
and runs complete original native scientist worlds, without a model designer.
"""
import argparse
import fcntl
import hashlib
import json
import os
from pathlib import Path
import subprocess

from scripts.run_native_planning_fixed_evaluation_v1 import origin_evidence
from scripts.run_native_objective_instrument_loop_v1 import factory_for, measure_with, progress, utc
from scripts.run_pre_scale_search_v1 import require_environment, ENVIRONMENT
from utopia.optimization.blackbox import Observation
from utopia.optimization.common_content_observer import CommonContentObserver, LocalObserverBackend, make_contract
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_development_references import objective_view, validate_context
from utopia.optimization.native_designer_preflight import runtime_binding, backend_binding
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.optimization.native_parameter_space_v1 import NativeParameterSpace, NativeParameterOptimizer, parameter_domain
from utopia.optimization.native_world import evaluate_native_suggestion
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'scienceutopia.native-parameter-comparator.v1'
PROTOCOL = 'research/protocols/campaigns/native-parameter-comparator-v1.md'
SEED = 61001
AUTHOR_ONLY_DIFFERENCES = (
    'utopia/optimization/native_bounded_author_context_v45.py',
    'utopia/optimization/native_parent_evidence_v46.py',
    'utopia/optimization/native_staged_author_v15.py',
)


def read(path): return checked(json.loads(Path(path).read_text()))


def unchanged_native_sources(source):
    """Literal original native code, excluding explicitly named author-only code.

    No inference of global semantic equivalence is made. New numerical code is
    separately source-bound. The three excluded files implement the designer,
    which this comparator never calls, not a native scientist/consumer change.
    """
    names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', source,
        '--', 'utopia'], cwd=ROOT, text=True).splitlines()
    names += ['scripts/run_native_objective_instrument_loop_v1.py',
        'scripts/native_benchmark_physical.py', 'scripts/native_observer_physical_v1.py']
    proof = {}
    for name in sorted(set(names)):
        if not name.endswith('.py') or name in AUTHOR_ONLY_DIFFERENCES: continue
        raw = subprocess.check_output(['git', 'show', source + ':' + name], cwd=ROOT)
        path = ROOT / name
        if path.is_symlink() or not path.is_file() or path.read_bytes() != raw:
            raise ValueError('original native comparator source differs: ' + name)
        proof[name] = hashlib.sha256(raw).hexdigest()
    return {'original_source': source, 'literal_files': proof,
        'declared_author_only_exclusions': list(AUTHOR_ONLY_DIFFERENCES),
        'global_semantic_equivalence_claimed': False}


def space_for(anchor):
    spec = SystemSpec.from_dict(anchor)
    coordinates = [{'mechanism_id': 'developer-liquidity-director',
        'path': '/parameters/reserve_units', 'integer': True, 'lower': 1, 'upper': 60}]
    return NativeParameterSpace(spec, parameter_domain(spec, coordinates,
        world_law_scope='fixed-native-production-catalog-planning-v3'))


def context_for(original, origin):
    return validate_context(read(Path(origin['run']) / 'developer-reference-context.json'),
        target_world=original['world'], target_seeds=[SEED])


def anchors_for(original, context):
    anchors = {}
    for objective in original['objectives']:
        pairs = objective_view(context, original['losses'][objective])['observations']
        # Identical first-in-bank tie handling to the free-program first parent.
        best = min(pairs, key=lambda pair: pair['observation']['loss'])
        space = space_for(best['suggestion']['candidate'])
        anchors[objective] = {'reference_suggestion': clone(best['suggestion']),
            'reference_observation': clone(best['observation']), 'space_binding': space.binding,
            'space_binding_sha256': space.binding_sha256}
    return anchors


def build_plan(original, audit, context, *, source, origin, observer_backend, native_sources):
    if (original['schema'] != 'scienceutopia.native-planning-objective-loop.v1.plan'
            or original['objectives'] != ['throughput', 'content-utility']
            or original['generations'] != 3 or original['held_out_evaluation']
            or audit['schema'] != 'scienceutopia.native-planning-objective-loop-audit.v1'
            or audit['source_commit'] != original['source_commit']
            or native_sources['original_source'] != original['source_commit']
            or len(source) != 40 or any(c not in '0123456789abcdef' for c in source)):
        raise ValueError('normally audited original planning development study required')
    validate_context(context, target_world=original['world'], target_seeds=[SEED])
    if [p['suggestion']['suggestion_id'] for p in context['pairs']] != [
            'reference-' + label for label in original['reference_order']]:
        raise ValueError('all eight original references in their literal order required')
    observer = make_contract(source_commit=source,
        provider={k: original['scientist'][k] for k in ('model', 'model_digest')},
        backend=observer_backend, maximum_posts=1500, critics=3)
    for key in original['observer_contract']:
        if key not in ('source_commit', 'content_sha256') and original['observer_contract'][key] != observer[key]:
            raise ValueError('fixed original content observer changed')
    experiment = {'protocol': PROTOCOL, 'role': 'parameter-only-planning-comparator'}
    world = {**clone(original['world']), 'source_commit': source, 'experiment': experiment,
        'measurement_adapter_contract': observer, 'classification': 'actual-native-parameter-comparator-v1'}
    return {'schema': SCHEMA + '.plan', 'source_commit': source, 'runtime': runtime_binding(),
        'protocol': PROTOCOL, 'protocol_sha256': file_sha256(ROOT / PROTOCOL),
        'origin': clone(origin), 'origin_audit_content_sha256': audit['content_sha256'],
        'original_native_sources': clone(native_sources), 'launch_environment': clone(ENVIRONMENT),
        **{k: clone(original[k]) for k in ('scientist', 'designer', 'data_cache', 'losses', 'catalog')},
        'world': world, 'experiment': experiment, 'observer_contract': observer,
        'reference_context_sha256': context['content_sha256'], 'anchors': anchors_for(original, context),
        'objectives': clone(original['objectives']), 'generations': 3, 'optimizer_seed': 68011,
        'optimizer': {'method': 'existing-adaptive-random-search', 'initial_random': 1, 'mutation_scale': .2},
        'schedule': [{'objective': o, 'generation': g} for g in range(3)
            for o in (original['objectives'] if g % 2 == 0 else original['objectives'][::-1])],
        'budget': {'reused_reference_worlds': 8, 'new_reference_worlds': 0, 'candidate_slots': 6,
            'native_worlds_upper_bound': 6, 'scientist_HTTP_attempts_per_world': 1024,
            'world_wall_seconds': 7200, 'observer_POSTs_upper_bound': 1500,
            'designer_generation_POSTs': 0, 'replace_failed_slots': False},
        'reference_policy': 'same audited bank; first minimum assigned-loss reference; no other anchor fallback',
        'selection_policy': 'earliest tied complete own numeric proposal; no automatic reference fallback',
        'development_seed_reused': True, 'posthoc_comparator_design': True,
        'held_out_evaluation': False, 'independent_optimizer_replications': False,
        'isolated_design_freedom_causal_effect_claimed': False, 'publication_ready': False}


def require_plan(root):
    p = read(root / 'plan.json')
    if p['source_commit'] != pinned_revision(ROOT) or p['runtime'] != runtime_binding():
        raise ValueError('exact clean numeric comparator source/runtime required')
    original, audit = origin_evidence(p['origin']); context = context_for(original, p['origin'])
    expected = build_plan(original, audit, context, source=p['source_commit'], origin=p['origin'],
        observer_backend=p['observer_contract']['backend'], native_sources=unchanged_native_sources(original['source_commit']))
    if expected != {k: v for k, v in p.items() if k != 'content_sha256'}:
        raise ValueError('literal numeric comparator plan reconstruction differs')
    return p


def optimizer_for(p, objective):
    anchor = p['anchors'][objective]
    space = space_for(anchor['reference_suggestion']['candidate'])
    if space.binding != anchor['space_binding'] or space.binding_sha256 != anchor['space_binding_sha256']:
        raise ValueError('literal numeric space/anchor changed')
    optimizer = NativeParameterOptimizer(space, seed=p['optimizer_seed'],
        initial_random=p['optimizer']['initial_random'], mutation_scale=p['optimizer']['mutation_scale'])
    optimizer.warm_start(Observation.from_dict(anchor['reference_observation']))
    return optimizer


def selection(p, observations):
    selected = {}
    for objective in p['objectives']:
        rows = observations[objective]
        if len(rows) != p['generations']: raise ValueError('all declared own numeric slots required')
        pool = [row for row in rows if row['status'] == 'complete']
        best = min((row['loss'] for row in pool), default=None)
        ties = [row for row in pool if row['loss'] == best]
        selected[objective] = {'loss': best, 'all_tied_ids': [row['suggestion_id'] for row in ties],
            'selected_id': ties[0]['suggestion_id'] if ties else None,
            'system': clone(ties[0]['candidate']) if ties else None, 'completed_submissions': len(pool),
            'reference_loss': p['anchors'][objective]['reference_observation']['loss']}
    return {'schema': SCHEMA + '.selection', 'plan_sha256': p['content_sha256'],
        'selected': selected, 'baseline_fallback': False, 'held_out_evaluation': False}


def run(root):
    require_environment(); p = require_plan(root)
    with (root / 'writer.lock').open('a') as owner, (Path(p['origin']['run']) / 'writer.lock').open('r') as previous:
        for handle in (owner, previous): fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (root / 'started.json').exists(): raise ValueError('consumed numeric study; no redispatch')
        save(root / 'started.json', {'schema': SCHEMA + '.start', 'plan_sha256': p['content_sha256'],
            'pid': os.getpid(), 'started_utc': utc()})
        status, stage, consumed, completed, failure = 'stopped', 'initialization', 0, 0, {}
        try:
            optimizers = {o: optimizer_for(p, o) for o in p['objectives']}
            observations = {o: [] for o in p['objectives']}
            for o in p['objectives']: save(root / 'search' / o / 'initial-state.json', optimizers[o].state_dict())
            observer = CommonContentObserver(root / 'observer', p['observer_contract'],
                backend=LocalObserverBackend(inference_lock=root / 'inference.lock'))
            for slot in p['schedule']:
                objective, generation = slot['objective'], slot['generation']
                directory = root / 'search' / objective / ('generation-' + str(generation))
                stage = 'optimization'; progress(root, stage, objective + ':g' + str(generation))
                if directory.exists(): raise ValueError('consumed numeric slot; no redispatch')
                optimizer = optimizers[objective]; suggestion = optimizer.ask()[0]
                save(directory / 'started.json', {'plan_sha256': p['content_sha256'],
                    'objective': objective, 'generation': generation, 'seed': SEED,
                    'suggestion': suggestion.to_dict(), 'optimizer_after_ask': optimizer.state_dict(), 'started_utc': utc()})
                consumed += 1
                result = evaluate_native_suggestion(suggestion, seeds=[SEED],
                    simulation_factory=factory_for(directory / 'worlds', p, root), loss_spec=p['losses'][objective],
                    measurement_adapter=measure_with(observer, p['observer_contract']))
                save(directory / 'observation.json', result.to_dict())
                save(directory / 'cross-scores.json', {k: evaluate_loss(v, result.metadata['measurements'])
                    for k, v in p['losses'].items()})
                optimizer.tell([result]); save(directory / 'optimizer-after-tell.json', optimizer.state_dict())
                observations[objective].append(result.to_dict()); completed += 1; require_plan(root)
            save(root / 'selection.json', selection(p, observations))
            audit = observer.audit(); save(root / 'observer-audit.json', {k: v for k, v in audit.items() if k != 'content_sha256'})
            if read(root / 'observer-audit.json') != audit: raise ValueError('literal public observer retention differs')
            status = stage = 'closed'; progress(root, stage)
        except BaseException as error:
            failure = {'error_type': type(error).__name__, 'error': str(error)}; raise
        finally:
            save(root / 'terminal.json', {'schema': SCHEMA + '.terminal', 'status': status, 'stage': stage,
                'consumed_slots': consumed, 'completed_observations': completed, 'ended_utc': utc(),
                'held_out_evaluation': False, 'publication_ready': False, **failure})


def prepare(args):
    require_environment(); source = pinned_revision(ROOT)
    if args.output.exists() or args.output.is_relative_to(args.origin_run.resolve()):
        raise ValueError('fresh separate numeric output required')
    audit = read(args.audit_one)
    origin = {'run': str(args.origin_run.resolve()), 'source': str(args.origin_source.resolve()),
        'source_commit': audit['source_commit'],
        'audit_files': {str(path.resolve()): file_sha256(path) for path in (args.audit_one, args.audit_two)}}
    with (args.origin_run / 'writer.lock').open('r') as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB); original, audit = origin_evidence(origin)
        context = context_for(original, origin)
        p = build_plan(original, audit, context, source=source, origin=origin,
            observer_backend=backend_binding({k: original['scientist'][k] for k in ('model', 'model_digest')}),
            native_sources=unchanged_native_sources(original['source_commit']))
        args.output.mkdir(parents=True); save(args.output / 'plan.json', p); require_plan(args.output)
    print(json.dumps({'prepared_source': source, 'reused_reference_worlds': 8,
        'new_native_worlds_upper_bound': 6, 'new_model_calls': 0}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('prepare', 'run')); parser.add_argument('--output', type=Path, required=True)
    for key in ('origin-run', 'origin-source', 'audit-one', 'audit-two'): parser.add_argument('--' + key, type=Path)
    args = parser.parse_args(); args.output = args.output.resolve()
    if args.stage == 'run': run(args.output); return
    if any(getattr(args, key) is None for key in ('origin_run', 'origin_source', 'audit_one', 'audit_two')):
        parser.error('exact closed original planning study and two matching audits required')
    prepare(args)


if __name__ == '__main__': main()
