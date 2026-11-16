"""Finite uniform/adaptive-priority/free-institution comparison in native worlds.

The restricted family is a comparator, never a restriction on free authors.
Known technical nulls consume slots; unknown dispatch or changed bindings stop.
"""
import argparse
from contextlib import ExitStack
import fcntl
from pathlib import Path
import os

from scripts import run_native_topic_free_optimization_v1 as free
from scripts.reports.stage_native_component_fixtures_v1 import collect, TOPIC_SCOPE
from utopia.optimization.blackbox import Suggestion, Observation
from utopia.optimization.common_content_observer import CommonContentObserver, LocalObserverBackend
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign
from utopia.optimization.native_development_references import build_context, objective_view
from utopia.optimization.native_designer_preflight import backend_binding, runtime_binding
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_parameter_space_v1 import NativeParameterOptimizer
from utopia.optimization.native_topic_priority_space_v1 import topic_priority_space
from utopia.optimization.native_world import evaluate_native_suggestion
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest
from utopia.system.native_terminal_cost_controls_v1 import terminal_consolidation_control
from utopia.utils.data_utils import file_sha256

ROOT, SEED, staged_author = free.ROOT, free.SEED, free.staged_author
SCHEMA = 'scienceutopia.native-priority-method-comparison.v1'
AUDIT_SCHEMA = SCHEMA + '.audit'
PROTOCOL = 'research/protocols/campaigns/native-priority-method-comparison-v1.md'
METHODS = ('uniform-priority', 'adaptive-priority', 'free-code-graph')
OBJECTIVES = ('content-utility', 'resource-aware-content')
REPLICATION_SEEDS = (79011, 79019)
PARENTS = ('priority-zero', 'terminal-priority-zero')
AUDIT_SCRIPTS = ['scripts/run_native_priority_method_comparison_v1.py',
                 'scripts/audit_native_priority_method_comparison_v1.py']
read, save, utc = free.read, free.save, free.utc
scientist_factory, designer_for = free.scientist_factory, free.designer_for
require_candidate, verify_interval = free.require_candidate, free.verify_interval
measurement, reconstruct_extra_measurement = free.measurement, free.reconstruct_extra_measurement


def literal(value):
    return {k: v for k, v in value.items() if k != 'content_sha256'}


def native_sources(original, source):
    adapters = {path: {'source_commit': free.pilot.ADAPTER_SOURCE, 'role': role}
                for path, role in free.pilot.ADAPTERS.items()}
    adapters.update({path: {'source_commit': source, 'role': role} for path, role in free.AUTHOR_ADAPTERS.items()})
    adapters['utopia/optimization/native_post_edit_feedback_v1.py'] = {
        'source_commit': source, 'role': 'Staged feedback; no world-law change'}
    adapters['utopia/system/native_catalog_planning.py'] = {
        'source_commit': source, 'role': 'Explicit predicate error diagnostics; original acceptance predicates unchanged'}
    return free.base.native_sources(original, adapters=adapters)


def all_history_keys(p):
    return [(m, r, o) for m in p['methods'] for r in range(len(p['replication_seeds'])) for o in p['objectives']]


def history_keys(p):
    return [key for key in all_history_keys(p) if key[0] == METHODS[2]]


def history_key(slot):
    return slot['method'], slot['replication'], slot['objective']


def history_metadata(key):
    return {'method': key[0], 'optimizer_history': key[1]}


def history_directory(root, key):
    m, r, o = key
    if m not in METHODS or type(r) is not int or r not in range(2) or o not in OBJECTIVES:
        raise ValueError('declared method/history/objective required')
    return root / 'search' / m / ('history-' + str(r)) / o


def open_institutions(p):
    if (p.get('schema') != SCHEMA + '.plan' or p.get('protocol') != PROTOCOL
            or p.get('designer_mode') != staged_author.MODE
            or p.get('design_space', {}).get('world_law_scope') != free.SCOPE):
        raise ValueError('explicit prospective mixed-method native study required')
    return True


def build_plan(original, audit, *, source, origin, backend, observer_backend, bank, evidence, sources):
    p = free.build_plan(original, audit, source=source, origin=origin, backend=backend,
        observer_backend=observer_backend, bank=bank, evidence=evidence, sources=sources)
    related = SystemSpec.from_dict(p['reference_systems']['core-plus-related'])
    zero = topic_priority_space(related).binding['anchor']
    terminal = topic_priority_space(terminal_consolidation_control(related, terminal_year=4)).binding['anchor']
    order = [(m, r, o) for r in range(2) for o in OBJECTIVES for m in METHODS]
    p.update(schema=SCHEMA + '.plan', protocol=PROTOCOL, protocol_sha256=file_sha256(ROOT / PROTOCOL),
        methods=list(METHODS), objectives=list(OBJECTIVES), replication_seeds=list(REPLICATION_SEEDS),
        experiment={'protocol': PROTOCOL, 'role': 'restricted-and-free-objective-conditioned-methods'},
        literal_related_system=related.to_dict(),
        reference_systems={PARENTS[0]: zero, PARENTS[1]: terminal, 'literal-related': related.to_dict()},
        reference_order=[*PARENTS, 'literal-related'], optimizer_reference_labels=list(PARENTS),
        comparison_only_labels=['literal-related'], generations=2,
        schedule=[{'method': m, 'replication': r, 'objective': o, 'generation': g}
                  for g in range(2) for m, r, o in (order if g == 0 else order[::-1])],
        numeric_settings={'uniform-priority': {'initial_random': 2, 'mutation_scale': .2},
                          'adaptive-priority': {'initial_random': 1, 'mutation_scale': .2}},
        reference_policy='Fresh exact zero/terminal parents; first minimum assigned-loss parent, shared by all methods',
        selection_policy='Earliest tied complete own submission in each method/history/objective; no reference fallback',
        comparison={'posthoc_development_design': True, 'known_terminal_rule_visible': True,
            'same_proposal_budget_not_equal_compute': True, 'isolated_topology_causal_effect_claimed': False,
            'independent_optimizer_seeds_not_independent_world_seeds': True,
            'unconditional_method_superiority_claimed': False})
    p['strategies']['local-workflow-designer']['protocol'] = PROTOCOL
    p['world'].update(experiment=clone(p['experiment']), classification='actual-native-priority-method-comparison-v1')
    p['budget'].update(fresh_reference_worlds=3, candidate_slots=24, native_worlds_upper_bound=27,
        readiness_sessions=9, designer_POSTs_upper_bound=488, component_probes_upper_bound=512,
        observer_POSTs_upper_bound=6000)
    # The inherited actual observer contract already has this same finite ceiling.
    if p['observer_contract']['maximum_posts'] != p['budget']['observer_POSTs_upper_bound']:
        raise ValueError('declared observer budget differs from actual contract')
    return p


def require_plan(root):
    p = read(root / 'plan.json')
    if p['source_commit'] != pinned_revision(ROOT) or p['runtime'] != runtime_binding():
        raise ValueError('exact clean mixed-method source/runtime required')
    original, audit = free.preceding_evidence(p['origin'])
    expected = build_plan(original, audit, source=p['source_commit'], origin=p['origin'], backend=p['backend'],
        observer_backend=p['observer_contract']['backend'], bank=p['component_bank'], evidence=p['component_evidence'],
        sources=native_sources(original['original_native_sources']['original_source'], p['source_commit']))
    if literal(p) != expected:
        raise ValueError('literal method/reference/loss/seed/budget plan reconstruction differs')
    return p


def reference_context(p, pairs):
    if [v['suggestion']['suggestion_id'] for v in pairs] != ['workflow-reference-' + s for s in p['reference_order']]:
        raise ValueError('complete exact ordered common references required')
    return build_context(pairs[:2], world=p['world'], seeds=[SEED], loss_spec=p['losses']['throughput'])


def parent_for(p, context, objective):
    return min(objective_view(context, p['losses'][objective])['observations'],
               key=lambda row: row['observation']['loss'])


def numeric_optimizer(p, context, key):
    method, replication, objective = key
    if method not in p['numeric_settings']:
        raise ValueError('declared numeric method required')
    parent = parent_for(p, context, objective)
    identity = parent['suggestion']['suggestion_id']
    base = SystemSpec.from_dict(p['literal_related_system'])
    if identity == 'workflow-reference-' + PARENTS[1]:
        base = terminal_consolidation_control(base, terminal_year=4)
    elif identity != 'workflow-reference-' + PARENTS[0]:
        raise ValueError('numeric parent has no declared literal family')
    space = topic_priority_space(base)
    if space.binding['anchor'] != parent['suggestion']['candidate']:
        raise ValueError('numeric anchor is not the measured exact parent')
    optimizer = NativeParameterOptimizer(space, seed=p['replication_seeds'][replication], **p['numeric_settings'][method])
    optimizer.warm_start(Observation.from_dict(parent['observation']))
    return optimizer


def campaign(root, p, key, context=None, *, prototype=False):
    if key not in history_keys(p):
        raise ValueError('declared free-author history required')
    path = (root / 'initial-readiness' if prototype else history_directory(root, key)) / 'campaign'
    return NativeAdaptiveDesignCampaign(path, initial_system=SystemSpec.from_dict(p['initial_system']),
        loss_spec=p['losses'][key[2]], seeds=[SEED], world_binding=p['world'], strategies=p['strategies'],
        mode='blackbox', seed=p['replication_seeds'][key[1]], design_space=p['design_space'],
        **({} if context is None else {'development_references': context}))


def initial_readiness_jobs(p):
    return [(history_keys(p)[0], Path('initial-readiness'))]


def selection(root, p, context):
    selected = {m: {str(r): {} for r in range(2)} for m in p['methods']}
    for key in all_history_keys(p):
        m, r, objective = key; directory = history_directory(root, key)
        if m == METHODS[2]:
            c = campaign(root, p, key, context)
            if c.state['pending'] is not None or len(c.state['records']) != p['generations']:
                raise ValueError('all free-author slots must be terminal')
            rows = [o for record in c.state['records'] for o in record['observations'] if o is not None]
        else:
            rows = [read(directory / ('generation-' + str(g)) / 'observation.json') for g in range(p['generations'])]
        pool = [row for row in rows if row['status'] == 'complete']
        best = min((row['loss'] for row in pool), default=None)
        ties = [row for row in pool if row['loss'] == best]
        selected[m][str(r)][objective] = {'loss': best, 'completed_submissions': len(pool),
            'all_tied_ids': [row['suggestion_id'] for row in ties],
            'selected_id': ties[0]['suggestion_id'] if ties else None,
            'system': clone(ties[0]['candidate']) if ties else None,
            'reference_loss': parent_for(p, context, objective)['observation']['loss']}
    return {'schema': SCHEMA + '.selection', 'plan_sha256': p['content_sha256'],
            'selected': selected, 'baseline_fallback': False, 'held_out_evaluation': False}


def run(root):
    free.base.require_environment(); p = require_plan(root)
    with ExitStack() as stack:
        for path in sorted({root / 'writer.lock', Path(p['origin']['run']) / 'writer.lock'}):
            h = stack.enter_context(path.open('a' if path == root / 'writer.lock' else 'r'))
            fcntl.flock(h, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (root / 'started.json').exists():
            raise ValueError('consumed method study; no redispatch')
        save(root / 'started.json', {'schema': SCHEMA + '.start', 'plan_sha256': p['content_sha256'],
            'pid': os.getpid(), 'started_utc': utc()})
        stage, consumed, observations, status = 'initial-readiness', 0, 0, 'stopped'
        try:
            key, relative = initial_readiness_jobs(p)[0]
            c = campaign(root, p, key, prototype=True)
            designer_for(root / relative / 'author', p, root).calibrate(c._request([], c._validate(), 1))
            require_plan(root)
            observer = CommonContentObserver(root / 'observer', p['observer_contract'],
                backend=LocalObserverBackend(inference_lock=root / 'inference.lock'))
            pairs = []
            for label in p['reference_order']:
                stage = 'references'; free.base.progress(root, stage, label)
                directory = root / 'references' / label
                s = Suggestion('workflow-reference-' + label, p['reference_systems'][label], 0, 'developer-reference')
                save(directory / 'started.json', {'suggestion': s.to_dict(), 'seed': SEED, 'started_utc': utc()})
                o = evaluate_native_suggestion(s, seeds=[SEED], simulation_factory=scientist_factory(directory / 'worlds', p, root),
                    loss_spec=p['losses']['throughput'], measurement_adapter=measurement(p, observer)).to_dict()
                save(directory / 'observation.json', o)
                save(directory / 'cross-scores.json', {k: evaluate_loss(v, o['metadata']['measurements']) for k, v in p['losses'].items()})
                if o['status'] != 'complete':
                    raise ValueError('reference technical null retained; no fallback or refill')
                pairs.append({'suggestion': s.to_dict(), 'observation': Observation.from_dict(o).to_dict()})
                observations += 1; require_plan(root)
            context = reference_context(p, pairs)
            save(root / 'developer-reference-context.json', literal(context))
            optimizers = {key: numeric_optimizer(p, context, key) for key in all_history_keys(p) if key[0] != METHODS[2]}
            for key, opt in optimizers.items():
                save(history_directory(root, key) / 'initial-state.json', opt.state_dict())
            for index, slot in enumerate(p['schedule']):
                key, g = history_key(slot), slot['generation']; objective = key[2]
                save(root / 'slots' / f'{index:03}.json', {'slot': clone(slot), 'plan_sha256': p['content_sha256'],
                    'started_utc': utc(), 'world_seed': SEED})
                consumed += 1; directory = history_directory(root, key)
                free.base.progress(root, 'optimization', '/'.join(map(str, key)) + ':g' + str(g))
                if key in optimizers:
                    stage = 'numeric-optimization'; opt = optimizers[key]
                    target = directory / ('generation-' + str(g)); s, = opt.ask()
                    save(target / 'started.json', {'slot': clone(slot), 'plan_sha256': p['content_sha256'],
                        'suggestion': s.to_dict(), 'optimizer_after_ask': opt.state_dict(), 'started_utc': utc()})
                    o = evaluate_native_suggestion(s, seeds=[SEED], simulation_factory=scientist_factory(target / 'worlds', p, root),
                        loss_spec=p['losses'][objective], measurement_adapter=measurement(p, observer))
                    save(target / 'observation.json', o.to_dict())
                    save(target / 'cross-scores.json', {k: evaluate_loss(v, o.metadata['measurements']) for k, v in p['losses'].items()})
                    opt.tell([o]); save(target / 'optimizer-after-tell.json', opt.state_dict()); observations += 1
                else:
                    c = campaign(root, p, key, context)
                    if c.state['pending'] is not None or len(c.state['records']) != g:
                        raise ValueError('consumed/pending author slot; no redispatch')
                    req = c._request(c.state['records'], c._validate(), 1)
                    author = designer_for(directory / 'authoring', p, root)
                    stage = 'readiness'; cert = author.calibrate(req); require_plan(root)
                    def generate(request):
                        if request != req:
                            raise ValueError('proposal differs from calibrated actual request')
                        return free.base.generation_definition(author.execute(request, purpose='proposal', certificate=cert))
                    stage = 'free-optimization'
                    record = c.advance(simulation_factory=scientist_factory(directory / 'worlds', p, root),
                        generators={'local-workflow-designer': generate}, count=1,
                        measurement_adapter=measurement(p, observer), measurement_contract=p['observer_contract'])
                    observations += sum(o is not None for o in record['observations'])
                require_plan(root)
            save(root / 'selection.json', selection(root, p, context)); free.base.retain_observer_audit(root, observer)
            status = stage = 'closed'; free.base.progress(root, stage, None)
        except BaseException as error:
            save(root / 'failure.json', {'error_type': type(error).__name__, 'error': str(error),
                'stage': stage, 'consumed_slots': consumed, 'no_retry': True})
            raise
        finally:
            save(root / 'terminal.json', {'schema': SCHEMA + '.terminal', 'status': status, 'stage': stage,
                'consumed_slots': consumed, 'observations': observations, 'ended_utc': utc(),
                'no_retry': True, 'held_out_evaluation': False, 'publication_ready': False})


def cold_numeric_begin(root, p, context):
    states = {}
    for key in all_history_keys(p):
        if key[0] == METHODS[2]:
            continue
        opt = numeric_optimizer(p, context, key)
        if literal(read(history_directory(root, key) / 'initial-state.json')) != opt.state_dict():
            raise ValueError('original measured numeric anchor/state differs')
        states[key] = {'optimizer': opt, 'completed_slots': 0}
    return states


def cold_numeric_slot(root, p, context, slot, states, physical):
    key, g = history_key(slot), slot['generation']; row = states[key]
    if row['completed_slots'] != g:
        raise ValueError('numeric cold slot order differs')
    target = history_directory(root, key) / ('generation-' + str(g)); opt = row['optimizer']
    s, = opt.ask(); start = read(target / 'started.json')
    expected = {'slot': clone(slot), 'plan_sha256': p['content_sha256'], 'suggestion': s.to_dict(),
        'optimizer_after_ask': opt.state_dict(), 'started_utc': start['started_utc']}
    if literal(start) != expected:
        raise ValueError('numeric ask/state/slot differs from cold replay')
    o = read(target / 'observation.json')
    scores = physical(target, s.to_dict(), o, key[2], 'numeric-own-proposal', history=key)
    if literal(read(target / 'cross-scores.json')) != scores:
        raise ValueError('literal numeric cross-scores differ')
    opt.tell([Observation.from_dict(o)])
    if literal(read(target / 'optimizer-after-tell.json')) != opt.state_dict():
        raise ValueError('numeric feedback state differs from measured scalar')
    row['completed_slots'] += 1


def cold_numeric_end(root, p, states, start, end):
    from scripts.audit_native_institution_loop_v1 import epoch
    if any(v['completed_slots'] != p['generations'] for v in states.values()):
        raise ValueError('all declared numeric slots required')
    expected_dirs = {history_directory(root, k) / ('generation-' + str(g)) for k in states for g in range(p['generations'])}
    if expected_dirs != {v for v in (root / 'search').glob('*/*/*/generation-*') if v.is_dir()}:
        raise ValueError('unaccounted numeric generation directory')
    paths = sorted((root / 'slots').glob('*.json'))
    if [v.name for v in paths] != [f'{i:03}.json' for i in range(len(p['schedule']))]:
        raise ValueError('all exact scheduled slot receipts required')
    previous = epoch(start['started_utc'])
    for path, slot in zip(paths, p['schedule'], strict=True):
        row = read(path); at = epoch(row['started_utc'])
        if (literal(row) != {'slot': slot, 'plan_sha256': p['content_sha256'], 'world_seed': SEED,
                            'started_utc': row['started_utc']} or not previous <= at <= epoch(end['ended_utc'])):
            raise ValueError('literal interleaved slot chronology differs')
        previous = at


def prepare(args):
    free.base.require_environment(); source = pinned_revision(ROOT)
    origin = {'run': str(args.origin_run.resolve()), 'source': str(args.origin_source.resolve()),
        'source_commit': read(args.audit_one)['source_commit'],
        'audit_files': {str(v.resolve()): file_sha256(v) for v in (args.audit_one, args.audit_two)}}
    output = args.output.resolve()
    if output.exists() or output.is_relative_to(args.origin_run.resolve()):
        raise ValueError('fresh separate mixed-method output required')
    with (args.origin_run / 'writer.lock').open('r') as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        original, audit = free.preceding_evidence(origin)
        if not Path(original['data_cache']).is_dir():
            raise ValueError('existing offline corpus required')
        bank = collect(args.origin_run, args.audit_one, scope=TOPIC_SCOPE, source_root=args.origin_source)
        bank = {**bank, 'content_sha256': digest(bank)}
        evidence = {'run': str(args.origin_run.resolve()), 'source': str(args.origin_source.resolve()),
            'audit': str(args.audit_one.resolve()), 'audit_file_sha256': file_sha256(args.audit_one), 'staging_scope': TOPIC_SCOPE}
        p = build_plan(original, audit, source=source, origin=origin, backend=backend_binding(original['designer']),
            observer_backend=backend_binding(original['scientist']), bank=bank, evidence=evidence,
            sources=native_sources(original['original_native_sources']['original_source'], source))
        output.mkdir(parents=True); save(output / 'plan.json', p); require_plan(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('prepare', 'run')); parser.add_argument('--output', type=Path, required=True)
    for key in ('origin-run', 'origin-source', 'audit-one', 'audit-two'):
        parser.add_argument('--' + key, type=Path)
    args = parser.parse_args(); args.output = args.output.resolve()
    if args.stage == 'run':
        run(args.output); return
    if any(getattr(args, k) is None for k in ('origin_run', 'origin_source', 'audit_one', 'audit_two')):
        parser.error('closed original topic pilot and both exact original audits required')
    prepare(args)


if __name__ == '__main__':
    main()
