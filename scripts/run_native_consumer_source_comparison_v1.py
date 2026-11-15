"""Finite matched source-evidence U/C search in the original researcher world."""
import argparse
from contextlib import ExitStack
import fcntl
import os
from pathlib import Path

from scripts import run_native_topic_free_optimization_v1 as free
from scripts import run_native_legacy_topic_pilot_v1 as topic
from scripts.reports.stage_native_component_fixtures_v1 import collect, TOPIC_SCOPE
from utopia.optimization.blackbox import Suggestion, Observation
from utopia.optimization.common_content_observer import CommonContentObserver, LocalObserverBackend
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign
from utopia.optimization.native_consumer_evidence_v1 import build as source_evidence, OPTION
from utopia.optimization.native_development_references import build_context
from utopia.optimization.native_designer_preflight import backend_binding, runtime_binding
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_world import evaluate_native_suggestion
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest
from utopia.system.native_terminal_cost_controls_v1 import terminal_consolidation_control
from utopia.utils.data_utils import file_sha256

ROOT, SEED, staged_author = free.ROOT, free.SEED, free.staged_author
SCHEMA = 'scienceutopia.native-consumer-source-comparison.v1'
AUDIT_SCHEMA = SCHEMA + '.audit'
PROTOCOL = 'research/protocols/campaigns/native-consumer-source-comparison-v1.md'
ARMS = ('interface-only', 'literal-consumers')
OBJECTIVES = ('content-utility', 'resource-aware-content')
COMPARISON_ONLY = 'terminal-consolidation'
AUDIT_SCRIPTS = ['scripts/run_native_consumer_source_comparison_v1.py',
                 'scripts/audit_native_consumer_source_comparison_v1.py']
read, save, utc = free.read, free.save, free.utc
scientist_factory, designer_for = free.scientist_factory, free.designer_for
require_candidate, verify_interval = free.require_candidate, free.verify_interval
measurement, reconstruct_extra_measurement = free.measurement, free.reconstruct_extra_measurement


def native_sources(original, source, *, source_root=None):
    adapters = {path: {'source_commit': topic.ADAPTER_SOURCE, 'role': role}
                for path, role in topic.ADAPTERS.items()}
    adapters.update({path: {'source_commit': source, 'role': role} for path, role in free.AUTHOR_ADAPTERS.items()})
    adapters['utopia/optimization/native_post_edit_feedback_v1.py'] = {
        'source_commit': source, 'role': 'Exact staged component feedback and optional non-veto field diagnostics; no native-law change'}
    return free.base.native_sources(original, adapters=adapters, source_root=source_root)


def open_institutions(p):
    if (p.get('schema') != SCHEMA + '.plan' or p.get('protocol') != PROTOCOL
            or p.get('designer_mode') != staged_author.MODE
            or p.get('design_space', {}).get('world_law_scope') != free.SCOPE):
        raise ValueError('explicit matched native-consumer free-system scope required')
    return True


def history_keys(p):
    return [(arm, objective) for arm in p['arms'] for objective in p['objectives']]


def history_key(slot):
    return slot['arm'], slot['objective']


def history_metadata(key):
    return {'arm': key[0]}


def history_directory(root, key):
    if not isinstance(key, tuple) or key[0] not in ARMS or key[1] not in OBJECTIVES:
        raise ValueError('declared matched arm/objective required')
    return root / 'search' / key[0] / key[1]


def initial_readiness_jobs(p):
    return [((arm, p['objectives'][0]), Path('initial-readiness') / arm) for arm in p['arms']]


def build_plan(original, audit, *, source, origin, backend, observer_backend, bank, evidence, sources):
    p = free.build_plan(original, audit, source=source, origin=origin, backend=backend,
        observer_backend=observer_backend, bank=bank, evidence=evidence, sources=sources)
    visible = list(p['reference_order'])
    parent = SystemSpec.from_dict(p['reference_systems'][visible[1]])
    comparison = terminal_consolidation_control(parent, terminal_year=4)
    require_candidate(SystemSpec.from_dict(p['initial_system']), comparison)
    pack = source_evidence(source_commit=source)
    strategies = clone(p['strategies'])
    strategies['local-workflow-designer']['protocol'] = PROTOCOL
    by_arm = {arm: clone(strategies) for arm in ARMS}
    by_arm[ARMS[1]]['local-workflow-designer'][OPTION] = pack
    order = [(ARMS[0], OBJECTIVES[0]), (ARMS[1], OBJECTIVES[1]),
             (ARMS[0], OBJECTIVES[1]), (ARMS[1], OBJECTIVES[0])]
    p.update(schema=SCHEMA + '.plan', protocol=PROTOCOL, protocol_sha256=file_sha256(ROOT / PROTOCOL),
        arms=list(ARMS), objectives=list(OBJECTIVES), optimizer_seed=78011,
        experiment={'protocol': PROTOCOL, 'role': 'matched-fixed-native-consumer-source-evidence'},
        strategies=strategies, strategies_by_arm=by_arm, consumer_source_evidence=pack,
        reference_systems={**p['reference_systems'], COMPARISON_ONLY: comparison.to_dict()},
        reference_order=visible + [COMPARISON_ONLY], optimizer_reference_labels=visible,
        comparison_only_labels=[COMPARISON_ONLY],
        schedule=[{'arm': a, 'objective': o, 'generation': g} for g in range(2)
                  for a, o in (order if g == 0 else order[::-1])],
        comparison={'information_only': True, 'cross_arm_own_feedback': False,
            'same_output_context_probe_and_action_budgets': True, 'equal_measured_compute_claimed': False,
            'known_comparison_only_policy_withheld_from_both_optimizers': True,
            'recovering_known_control_is_not_beating_it': True,
            'source_evidence_is_untrusted_user_data': True, 'require_improvement_or_novelty': False})
    p['world'].update(experiment=clone(p['experiment']), classification='actual-native-consumer-source-comparison-v1')
    p['budget'].update(fresh_reference_worlds=3, candidate_slots=8, native_worlds_upper_bound=11,
        readiness_sessions=10, designer_POSTs_upper_bound=528, component_probes_upper_bound=512)
    return p


def require_plan(root):
    p = read(root / 'plan.json')
    if p['source_commit'] != pinned_revision(ROOT) or p['runtime'] != runtime_binding():
        raise ValueError('exact clean consumer-comparison source/runtime required')
    original, audit = free.preceding_evidence(p['origin'])
    expected = build_plan(original, audit, source=p['source_commit'], origin=p['origin'], backend=p['backend'],
        observer_backend=p['observer_contract']['backend'], bank=p['component_bank'], evidence=p['component_evidence'],
        sources=native_sources(original['original_native_sources']['original_source'], p['source_commit']))
    if expected != {k: v for k, v in p.items() if k != 'content_sha256'}:
        raise ValueError('literal matched visibility/authority/loss/budget plan reconstruction differs')
    return p


def reference_context(p, pairs):
    expected = ['workflow-reference-' + label.lower() for label in p['reference_order']]
    if [v['suggestion']['suggestion_id'] for v in pairs] != expected:
        raise ValueError('complete ordered three-reference bank required')
    visible = ['workflow-reference-' + label.lower() for label in p['optimizer_reference_labels']]
    chosen = [pair for pair in pairs if pair['suggestion']['suggestion_id'] in visible]
    if len(chosen) != 2 or COMPARISON_ONLY in p['optimizer_reference_labels']:
        raise ValueError('only the two original references may reach either optimizer')
    return build_context(chosen, world=p['world'], seeds=[SEED], loss_spec=p['losses']['throughput'])


def campaign(root, p, key, context=None, *, prototype=False):
    if key not in history_keys(p):
        raise ValueError('declared matched history required')
    path = ((root / 'initial-readiness' / key[0]) if prototype else history_directory(root, key)) / 'campaign'
    return NativeAdaptiveDesignCampaign(path, initial_system=SystemSpec.from_dict(p['initial_system']),
        loss_spec=p['losses'][key[1]], seeds=[SEED], world_binding=p['world'],
        strategies=p['strategies_by_arm'][key[0]], mode='blackbox', seed=p['optimizer_seed'],
        design_space=p['design_space'], **({} if context is None else {'development_references': context}))


def selection(root, p, context):
    selected = {}
    for key in history_keys(p):
        c = campaign(root, p, key, context)
        if c.state['pending'] is not None or len(c.state['records']) != p['generations']:
            raise ValueError('all eight own slots must be terminal')
        pool = [o for record in c.state['records'] for o in record['observations'] if o and o['status'] == 'complete']
        best = min((o['loss'] for o in pool), default=None)
        ties = [o for o in pool if o['loss'] == best]
        selected['::'.join(key)] = {'arm': key[0], 'objective': key[1], 'loss': best,
            'completed_submissions': len(pool), 'all_tied_ids': [o['suggestion_id'] for o in ties],
            'selected_id': ties[0]['suggestion_id'] if ties else None,
            'system': clone(ties[0]['candidate']) if ties else None}
    return {'schema': SCHEMA + '.selection', 'plan_sha256': p['content_sha256'], 'selected': selected,
        'baseline_fallback': False, 'held_out_evaluation': False}


def run(root):
    free.base.require_environment(); p = require_plan(root)
    with ExitStack() as stack:
        for path in sorted({root / 'writer.lock', Path(p['origin']['run']) / 'writer.lock'}):
            handle = stack.enter_context(path.open('a' if path == root / 'writer.lock' else 'r'))
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (root / 'started.json').exists():
            raise ValueError('consumed matched study; no redispatch')
        save(root / 'started.json', {'schema': SCHEMA + '.start', 'plan_sha256': p['content_sha256'],
            'pid': os.getpid(), 'started_utc': utc()})
        stage, consumed, observations, status = 'initial-readiness', 0, 0, 'stopped'
        try:
            for key, relative in initial_readiness_jobs(p):
                free.base.progress(root, stage, key[0])
                c = campaign(root, p, key, prototype=True)
                designer_for(root / relative / 'author', p, root).calibrate(c._request([], c._validate(), 1))
                require_plan(root)
            observer = CommonContentObserver(root / 'observer', p['observer_contract'],
                backend=LocalObserverBackend(inference_lock=root / 'inference.lock'))
            pairs = []
            for label in p['reference_order']:
                stage = 'references'; free.base.progress(root, stage, label)
                directory = root / 'references' / label
                s = Suggestion('workflow-reference-' + label.lower(), p['reference_systems'][label], 0, 'developer-reference')
                save(directory / 'started.json', {'suggestion': s.to_dict(), 'seed': SEED, 'started_utc': utc()})
                o = evaluate_native_suggestion(s, seeds=[SEED], simulation_factory=scientist_factory(directory / 'worlds', p, root),
                    loss_spec=p['losses']['throughput'], measurement_adapter=measurement(p, observer)).to_dict()
                save(directory / 'observation.json', o)
                save(directory / 'cross-scores.json', {k: evaluate_loss(v, o['metadata']['measurements']) for k, v in p['losses'].items()})
                if o['status'] != 'complete':
                    raise ValueError('reference technical null; no refill')
                pairs.append({'suggestion': s.to_dict(), 'observation': Observation.from_dict(o).to_dict()})
                observations += 1; require_plan(root)
            context = reference_context(p, pairs)
            save(root / 'developer-reference-context.json', {k: v for k, v in context.items() if k != 'content_sha256'})
            for slot in p['schedule']:
                key, g = history_key(slot), slot['generation']
                c = campaign(root, p, key, context)
                if c.state['pending'] is not None or len(c.state['records']) != g:
                    raise ValueError('consumed/pending matched slot; no redispatch')
                request = c._request(c.state['records'], c._validate(), 1)
                directory = history_directory(root, key)
                author = designer_for(directory / 'authoring', p, root)
                stage = 'readiness'; free.base.progress(root, stage, '::'.join(key) + ':g' + str(g))
                certificate = author.calibrate(request); require_plan(root)
                def generate(req):
                    if req != request:
                        raise ValueError('proposal request differs from actual readiness')
                    return free.base.generation_definition(author.execute(req, purpose='proposal', certificate=certificate))
                stage = 'optimization'; free.base.progress(root, stage, '::'.join(key) + ':g' + str(g))
                record = c.advance(simulation_factory=scientist_factory(directory / 'worlds', p, root),
                    generators={'local-workflow-designer': generate}, count=1,
                    measurement_adapter=measurement(p, observer), measurement_contract=p['observer_contract'])
                consumed += 1; observations += sum(o is not None for o in record['observations']); require_plan(root)
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


def prepare(args):
    free.base.require_environment(); source = pinned_revision(ROOT)
    origin = {'run': str(args.origin_run.resolve()), 'source': str(args.origin_source.resolve()),
        'source_commit': read(args.audit_one)['source_commit'],
        'audit_files': {str(path.resolve()): file_sha256(path) for path in (args.audit_one, args.audit_two)}}
    output = args.output.resolve()
    if output.exists() or output.is_relative_to(args.origin_run.resolve()):
        raise ValueError('fresh separate matched-study root required')
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
    if args.stage == 'prepare':
        if any(getattr(args, key) is None for key in ('origin_run', 'origin_source', 'audit_one', 'audit_two')):
            parser.error('closed original-topic pilot and paired original audits required')
        prepare(args)
    else:
        run(args.output)


if __name__ == '__main__':
    main()
