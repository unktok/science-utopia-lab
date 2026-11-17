"""Finite same-native-world comparison of explicit literal-change information.

Two information arms x two unchanged objectives x two own proposals, not a
new population of independent histories or a forced-novelty invention test.
"""
import argparse
from contextlib import ExitStack
import fcntl
import os
from pathlib import Path
import subprocess

from scripts import run_native_corrected_choice_search_v1 as preceding
from utopia.optimization.blackbox import Observation, Suggestion
from utopia.optimization.common_content_observer import CommonContentObserver, LocalObserverBackend
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign
from utopia.optimization.native_component_parameter_context_v1 import OPTION, SCOPE as PARAMETER_SCOPE
from utopia.optimization.native_designer_preflight import backend_binding, runtime_binding
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_literal_change_feedback_v1 import OPTION as CHANGE_OPTION, contract
from utopia.optimization.native_world import evaluate_native_suggestion
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'scienceutopia.native-literal-feedback-comparison.v1'
AUDIT_SCHEMA = SCHEMA + '.audit'
PROTOCOL = 'research/protocols/campaigns/native-literal-feedback-comparison-v1.md'
AUDIT_SCRIPTS = ['scripts/run_native_literal_feedback_comparison_v1.py',
    'scripts/audit_native_literal_feedback_comparison_v1.py']
ARMS = ('current-information', 'literal-change-information')
OBJECTIVES, SEED = preceding.OBJECTIVES, preceding.SEED
free, staged_author = preceding.free, preceding.staged_author
read, save, utc, literal = preceding.read, preceding.save, preceding.utc, preceding.literal
native_sources = preceding.native_sources
scientist_factory, designer_for = preceding.scientist_factory, preceding.designer_for
require_candidate, verify_interval = preceding.require_candidate, preceding.verify_interval
measurement, reconstruct_extra_measurement = preceding.measurement, preceding.reconstruct_extra_measurement
reference_context = preceding.reference_context


def history_keys(p):
    return [(arm, 0, objective) for arm in p['methods'] for objective in p['objectives']]


def history_key(slot):
    return slot['method'], slot['replication'], slot['objective']


def history_metadata(key):
    return {'method': key[0], 'optimizer_history': key[1]}


def history_directory(root, key):
    if key not in [(a, 0, o) for a in ARMS for o in OBJECTIVES]:
        raise ValueError('declared information arm/objective/history required')
    return root/'search'/key[0]/'history-0'/key[2]


def initial_readiness_jobs(p):
    return [((arm, 0, OBJECTIVES[0]), Path('initial-readiness')/arm) for arm in ARMS]


def open_institutions(p):
    if (p.get('schema') != SCHEMA+'.plan' or p.get('protocol') != PROTOCOL
            or p.get('methods') != list(ARMS) or p.get('generations') != 2
            or p.get('designer_mode') != staged_author.MODE
            or p.get('design_space', {}).get('world_law_scope') != free.SCOPE):
        raise ValueError('explicit finite native literal-information comparison required')
    return True


def build_plan(original, audit, **kwargs):
    p = preceding.build_plan(original, audit, **kwargs)
    base = clone(p['strategies']); base['local-workflow-designer']['protocol'] = PROTOCOL
    treatment = clone(base); treatment['local-workflow-designer'][CHANGE_OPTION] = contract()
    order = [(ARMS[0], OBJECTIVES[0]), (ARMS[1], OBJECTIVES[0]),
        (ARMS[1], OBJECTIVES[1]), (ARMS[0], OBJECTIVES[1])]
    p.update(schema=SCHEMA+'.plan', protocol=PROTOCOL, protocol_sha256=file_sha256(ROOT/PROTOCOL),
        methods=list(ARMS), generations=2, strategies=base,
        strategies_by_arm={ARMS[0]: base, ARMS[1]: treatment},
        literal_feedback_contract=contract(),
        schedule=[{'method': arm, 'replication': 0, 'objective': objective, 'generation': g}
            for g in range(2) for arm, objective in (order if not g else order[::-1])],
        experiment={'protocol': PROTOCOL, 'role': 'native-literal-information-comparison'},
        comparison={'development_informed': True, 'same_native_world': True,
            'within_objective_same_reference_bank_and_optimizer_seed': True,
            'two_proposals_allow_one_loss_feedback_update': True,
            'same_proposal_budget_not_equal_compute': True,
            'independent_optimizer_replications': False,
            'causal_effect_of_model_capability_claimed': False,
            'objective_coefficient_changed': False, 'forced_change_or_gain': False})
    for key in ('initial_choice_contract', 'numeric_settings', 'numeric_kernels'):
        del p[key]
    p['world'].update(experiment=clone(p['experiment']),
        classification='actual-native-literal-feedback-comparison-v1')
    p['budget'].update(fresh_reference_worlds=3, candidate_slots=8, native_worlds_upper_bound=11,
        readiness_sessions=10, designer_POSTs_upper_bound=528, component_probes_upper_bound=512)
    open_institutions(p)
    return p


def require_plan(root):
    p = read(root/'plan.json')
    if p['source_commit'] != pinned_revision(ROOT) or p['runtime'] != runtime_binding():
        raise ValueError('exact clean literal-feedback source/runtime required')
    original, audit = free.preceding_evidence(p['origin'])
    expected = build_plan(original, audit, source=p['source_commit'], origin=p['origin'],
        backend=p['backend'], observer_backend=p['observer_contract']['backend'],
        bank=p['component_bank'], evidence=p['component_evidence'],
        sources=native_sources(original['original_native_sources']['original_source'], p['source_commit']))
    if literal(p) != expected:
        raise ValueError('literal information/world/loss/seed/reference/budget plan differs')
    return p


def campaign(root, p, key, context=None, *, prototype=False):
    directory = (root/'initial-readiness'/key[0] if prototype else history_directory(root, key))
    if key not in history_keys(p): raise ValueError('declared information history required')
    return NativeAdaptiveDesignCampaign(directory/'campaign',
        initial_system=SystemSpec.from_dict(p['initial_system']), loss_spec=p['losses'][key[2]],
        seeds=[SEED], world_binding=p['world'], strategies=p['strategies_by_arm'][key[0]],
        mode='blackbox', seed=p['replication_seeds'][0], design_space=p['design_space'],
        **({} if context is None else {'development_references': context}))


def selection(root, p, context):
    primary, own_only = ({arm: {'0': {}} for arm in ARMS} for _ in range(2))
    for key in history_keys(p):
        c = campaign(root, p, key, context)
        if c.state['pending'] is not None or len(c.state['records']) != 2:
            raise ValueError('both declared author slots must be terminal')
        own = [o for record in c.state['records'] for o in record['observations'] if o is not None]
        references = [row['observation'] for row in preceding.objective_view(context, p['losses'][key[2]])['observations']]
        pairs = [('own', o) for o in own]; best = min(o['loss'] for o in references)
        complete = sum(o['status'] == 'complete' for o in own)
        for bank, pool in ((own_only, pairs),
                (primary, [('reference', o) for o in references]+pairs)):
            bank[key[0]]['0'][key[2]] = preceding.endpoint(pool,
                reference_loss=best, complete_own=complete)
    return {'schema': SCHEMA+'.selection', 'plan_sha256': p['content_sha256'],
        'selected': primary, 'own_only_selected': own_only,
        'primary_is_measured_best_known_not_own_discovery': True,
        'baseline_fallback': False, 'held_out_evaluation': False}


def run(root):
    free.base.require_environment(); p = require_plan(root)
    if any(k.startswith('SCIENCE_UTOPIA_') and 'FIXTURE' in k for k in os.environ):
        raise ValueError('test-only fixtures cannot enter actual scientific comparison')
    with ExitStack() as stack:
        for path in sorted({root/'writer.lock', Path(p['origin']['run'])/'writer.lock'}):
            handle = stack.enter_context(path.open('a' if path == root/'writer.lock' else 'r'))
            fcntl.flock(handle, fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (root/'started.json').exists(): raise ValueError('consumed comparison; no redispatch')
        save(root/'started.json', {'schema': SCHEMA+'.start', 'plan_sha256': p['content_sha256'],
            'pid': os.getpid(), 'started_utc': utc(), 'exclusive_hardware_claimed': False,
            'shared_host_process_snapshot': subprocess.check_output(
                ['ps', '-axo', 'pid,ppid,%cpu,%mem,etime,comm'], text=True)})
        status, stage, consumed, observations = 'stopped', 'initial-readiness', 0, 0
        try:
            for key, relative in initial_readiness_jobs(p):
                c = campaign(root, p, key, prototype=True)
                designer_for(root/relative/'author', p, root).calibrate(c._request([], c._validate(), 1))
                require_plan(root)
            observer = CommonContentObserver(root/'observer', p['observer_contract'],
                backend=LocalObserverBackend(inference_lock=root/'inference.lock'))
            pairs = []
            for label in p['reference_order']:
                stage = 'references'; directory = root/'references'/label
                free.base.progress(root, stage, label)
                s = Suggestion('workflow-reference-'+label, p['reference_systems'][label], 0, 'developer-reference')
                save(directory/'started.json', {'suggestion': s.to_dict(), 'seed': SEED, 'started_utc': utc()})
                o = evaluate_native_suggestion(s, seeds=[SEED],
                    simulation_factory=scientist_factory(directory/'worlds', p, root),
                    loss_spec=p['losses']['throughput'], measurement_adapter=measurement(p, observer)).to_dict()
                save(directory/'observation.json', o)
                save(directory/'cross-scores.json', {k: evaluate_loss(v, o['metadata']['measurements']) for k,v in p['losses'].items()})
                observations += 1
                if o['status'] != 'complete': raise ValueError('reference null retained; no fallback/refill')
                pairs.append({'suggestion': s.to_dict(), 'observation': Observation.from_dict(o).to_dict()})
                require_plan(root)
            context = reference_context(p, pairs); save(root/'developer-reference-context.json', literal(context))
            for index, slot in enumerate(p['schedule']):
                require_plan(root); key = history_key(slot)
                save(root/'slots'/f'{index:03}.json', {'slot': clone(slot), 'plan_sha256': p['content_sha256'],
                    'started_utc': utc(), 'world_seed': SEED})
                consumed += 1; directory = history_directory(root, key)
                free.base.progress(root, 'optimization', '/'.join(map(str,key))+':g'+str(slot['generation']))
                c = campaign(root, p, key, context)
                if c.state['pending'] is not None or len(c.state['records']) != slot['generation']:
                    raise ValueError('consumed/pending author slot; no redispatch')
                req = c._request(c.state['records'], c._validate(), 1)
                author = designer_for(directory/'authoring', p, root)
                stage = 'readiness'; cert = author.calibrate(req); require_plan(root)
                def generate(request):
                    if request != req: raise ValueError('proposal differs from exact calibrated request')
                    return free.base.generation_definition(author.execute(request, purpose='proposal', certificate=cert))
                stage = 'free-optimization'
                record = c.advance(simulation_factory=scientist_factory(directory/'worlds', p, root),
                    generators={'local-workflow-designer': generate}, count=1,
                    measurement_adapter=measurement(p, observer), measurement_contract=p['observer_contract'])
                observations += sum(o is not None for o in record['observations']); require_plan(root)
            save(root/'selection.json', selection(root, p, context))
            free.base.retain_observer_audit(root, observer)
            status = stage = 'closed'; free.base.progress(root, stage, None)
        except BaseException as error:
            save(root/'failure.json', {'stage': stage, 'error_type': type(error).__name__,
                'error': str(error), 'consumed_slots': consumed, 'no_retry': True})
            raise
        finally:
            save(root/'terminal.json', {'schema': SCHEMA+'.terminal', 'status': status, 'stage': stage,
                'consumed_slots': consumed, 'observations': observations, 'ended_utc': utc(),
                'no_retry': True, 'held_out_evaluation': False, 'publication_ready': False})


def prepare(args):
    free.base.require_environment(); source = pinned_revision(ROOT)
    origin = {'run': str(args.origin_run.resolve()), 'source': str(args.origin_source.resolve()),
        'source_commit': read(args.audit_one)['source_commit'],
        'audit_files': {str(v.resolve()): file_sha256(v) for v in (args.audit_one,args.audit_two)}}
    output = args.output.resolve()
    if output.exists() or output.is_relative_to(args.origin_run.resolve()):
        raise ValueError('fresh separate information-comparison output required')
    with (args.origin_run/'writer.lock').open('r') as owner:
        fcntl.flock(owner, fcntl.LOCK_EX|fcntl.LOCK_NB)
        original, audit = free.preceding_evidence(origin)
        if not Path(original['data_cache']).is_dir(): raise ValueError('existing offline corpus required')
        bank = preceding.collect(args.origin_run, args.audit_one, scope=preceding.TOPIC_SCOPE,
            source_root=args.origin_source)
        bank[OPTION] = PARAMETER_SCOPE; bank['content_sha256'] = digest(bank)
        evidence = {'run': str(args.origin_run.resolve()), 'source': str(args.origin_source.resolve()),
            'audit': str(args.audit_one.resolve()), 'audit_file_sha256': file_sha256(args.audit_one),
            'staging_scope': preceding.TOPIC_SCOPE, 'parameter_context_scope': PARAMETER_SCOPE}
        p = build_plan(original, audit, source=source, origin=origin,
            backend=backend_binding(original['designer']), observer_backend=backend_binding(original['scientist']),
            bank=bank, evidence=evidence,
            sources=native_sources(original['original_native_sources']['original_source'], source))
        output.mkdir(parents=True); save(output/'plan.json', p); require_plan(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('prepare','run')); parser.add_argument('--output', type=Path, required=True)
    for key in ('origin-run','origin-source','audit-one','audit-two'): parser.add_argument('--'+key, type=Path)
    args = parser.parse_args(); args.output = args.output.resolve()
    if args.stage == 'run': run(args.output); return
    if any(getattr(args,k) is None for k in ('origin_run','origin_source','audit_one','audit_two')):
        parser.error('exact closed original topic source/run and paired audits required')
    prepare(args)


if __name__ == '__main__': main()
