"""Finite two-presentation T/U search in the original scientist world."""
import argparse
import fcntl
import json
import os
from pathlib import Path

from scripts import run_native_planning_objective_loop_v1 as base
from scripts.run_pre_scale_search_v1 import require_environment
from scripts.run_native_objective_instrument_loop_v1 import factory_for, measure_with, feedback_for, progress, utc
from utopia.optimization.blackbox import Suggestion
from utopia.optimization.common_content_observer import CommonContentObserver, LocalObserverBackend, make_contract
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign
from utopia.optimization.native_bounded_staged_designer import execute
from utopia.optimization.native_designer_decoding_v24 import decoding_contract
from utopia.optimization.native_designer_preflight import backend_binding, runtime_binding, planned_cases
from utopia.optimization.native_designer_tools_v25 import BOUNDED_AUTHORING
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.optimization.native_parent_evidence_v46 import MODE, OPTION
from utopia.optimization.native_post_edit_feedback_v1 import OPTION as TEST_OPTION
from utopia.optimization.native_world import evaluate_native_suggestion
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'scienceutopia.native-parent-presentation-loop.v1'
PROTOCOL = 'research/protocols/campaigns/native-parent-presentation-loop-v1.md'
BANK_MANIFEST, CONTENT_LOSS, SEED = base.BANK_MANIFEST, base.CONTENT_LOSS, base.SEED
MOTIVATION = 'research/data/native-planning-objective-loop-v1/report.json'
OBJECTIVES = ('throughput', 'content-utility')
PRESENTATIONS = ('control', 'literal')
ARM_ORDER = ('throughput-control', 'content-utility-literal',
             'content-utility-control', 'throughput-literal')


def read(path):
    return checked(json.loads(Path(path).read_text()))


def build_plan(operator, original, audit, *, source, backend, observer_backend, origin):
    p = base.build_plan(operator, original, audit, source=source, backend=backend,
        observer_backend=observer_backend, origin=origin)
    previous = read(ROOT/MOTIVATION)
    if (previous['schema'] != 'scienceutopia.native-planning-objective-report.v1'
            or len(previous['references']) != 8 or len(previous['slots']) != 6
            or any(row['status'] != 'complete' for row in previous['slots'])):
        raise ValueError('retained closed planning pilot required as motivation, not fresh observations')
    observer = make_contract(source_commit=source,
        provider={k: operator['scientist'][k] for k in ('model', 'model_digest')},
        backend=observer_backend, maximum_posts=3000, critics=3)
    experiment = {'protocol': PROTOCOL, 'role': 'objective-conditioned-parent-presentation-comparison'}
    control = clone(p['strategies'])
    control['local-designer']['protocol'] = PROTOCOL
    literal = clone(control)
    literal['local-designer'][OPTION] = MODE
    arms = {objective+'-'+presentation: {'objective': objective, 'presentation': presentation}
            for objective in OBJECTIVES for presentation in PRESENTATIONS}
    p.update(schema=SCHEMA+'.plan', protocol=PROTOCOL, protocol_sha256=file_sha256(ROOT/PROTOCOL),
        experiment=experiment, observer_contract=observer,
        world={**clone(p['world']), 'experiment': experiment, 'measurement_adapter_contract': observer,
               'classification': 'actual-native-parent-presentation-loop-v1'},
        presentations=list(PRESENTATIONS), arms=arms, arm_order=list(ARM_ORDER),
        strategies=control, strategies_by_presentation={'control': control, 'literal': literal},
        schedule=[{'arm': arm, **arms[arm], 'generation': g} for g in range(3)
                  for arm in (ARM_ORDER if g % 2 == 0 else ARM_ORDER[::-1])],
        motivation_evidence={'file': MOTIVATION, 'file_sha256': file_sha256(ROOT/MOTIVATION),
            'report_content_sha256': previous['content_sha256'], 'source_commit': previous['source_commit'],
            'reused_as_current_observation': False})
    p['budget'].update(candidate_slots=12, native_worlds_upper_bound=20,
        observer_POSTs_upper_bound=3000, readiness_sessions=14, initial_readiness_sessions=2,
        designer_http_timeout_seconds=decoding_contract('staged-v15', conversation_profile=BOUNDED_AUTHORING)['http_timeout_seconds'])
    return p


def require_plan(root):
    p = read(root/'plan.json')
    if p['source_commit'] != pinned_revision(ROOT) or p['runtime'] != runtime_binding():
        raise ValueError('exact clean presentation study source/runtime required')
    operator, original, audit = base.origin_evidence(p['origin'])
    expected = build_plan(operator, original, audit, source=p['source_commit'], backend=p['backend'],
        observer_backend=p['observer_contract']['backend'], origin=p['origin'])
    if expected != {k: v for k, v in p.items() if k != 'content_sha256'}:
        raise ValueError('literal presentation study reconstruction differs')
    support = Path(p['component_support']['directory'])
    summary = read(support/'summary.json')
    if (file_sha256(support/'plan.json') != p['component_support']['plan_file_sha256']
            or file_sha256(support/'summary.json') != p['component_support']['summary_file_sha256']
            or summary['status'] != 'closed' or len(summary['observations']) != 12
            or not all(o['original_result_matches'] for o in summary['observations'])
            or read(support/'plan.json')['bank_file_sha256'] != p['component_bank_file_sha256']):
        raise ValueError('original twelve-call component support changed')
    return p


def campaign(root, p, arm, context=None, *, prototype=False):
    assignment = p['arms'][arm]
    presentation, objective = assignment['presentation'], assignment['objective']
    directory = (root/'initial-readiness'/presentation/'campaign' if prototype
                 else root/'search'/arm/'campaign')
    return NativeAdaptiveDesignCampaign(directory, initial_system=SystemSpec.from_dict(p['initial_system']),
        loss_spec=p['losses'][objective], seeds=[SEED], world_binding=p['world'],
        strategies=p['strategies_by_presentation'][presentation], mode='blackbox', seed=p['optimizer_seed'],
        design_space=p['design_space'], **({} if context is None else {'development_references': context}))


def selection(root, p, context, *, frozen_utc=None, campaign_loader=None):
    selected = {}
    load = campaign if campaign_loader is None else campaign_loader
    for arm in p['arm_order']:
        c = load(root, p, arm, context)
        if c.state['pending'] is not None or len(c.state['records']) != p['generations']:
            raise ValueError('all twelve terminal own slots required')
        pool = [o for r in c.state['records'] for o in r['observations']
                if o and o['status'] == 'complete' and o['loss'] is not None]
        best = min((o['loss'] for o in pool), default=None)
        ties = [o for o in pool if o['loss'] == best]
        selected[arm] = {'loss': best, 'all_tied_ids': [o['suggestion_id'] for o in ties],
            'selected_id': ties[0]['suggestion_id'] if ties else None,
            'system': clone(ties[0]['candidate']) if ties else None, 'completed_submissions': len(pool)}
    return {'schema': SCHEMA+'.selection', 'plan_sha256': p['content_sha256'], 'selected': selected,
        'baseline_fallback': False, 'frozen_utc': utc() if frozen_utc is None else frozen_utc,
        'held_out_evaluation': False}


def readiness(root, p, *, request, target):
    count = len(planned_cases(request, 'staged-v15', BOUNDED_AUTHORING))
    if count > p['budget']['readiness_POSTs_per_session']:
        raise ValueError('readiness exceeds declared POST ceiling')
    result = execute(target/'editor-readiness', kind='calibration', request=request,
        provider=p['designer'], source_commit=p['source_commit'], maximum_posts=count,
        seconds=p['budget']['readiness_seconds'], inference_lock=root/'inference.lock')
    certificate = target/'editor-readiness/calibration/certificate.json'
    if not result['passed']:
        raise ValueError('fresh presentation readiness failed; no replacement')
    saved = read(certificate)
    if saved['plan']['backend'] != p['backend'] or saved['plan']['request'] != request:
        raise ValueError('presentation readiness backend/request differs')
    return certificate


def observe(root, p, label, observer):
    directory = root/'references'/label
    if (directory/'started.json').exists():
        raise ValueError('consumed reference; no redispatch')
    suggestion = Suggestion('reference-'+label, p['reference_systems'][label], 0, 'developer-reference')
    save(directory/'started.json', {'suggestion': suggestion.to_dict(), 'seed': SEED, 'started_utc': utc()})
    result = evaluate_native_suggestion(suggestion, seeds=[SEED],
        simulation_factory=factory_for(directory/'worlds', p, root), loss_spec=p['losses']['throughput'],
        measurement_adapter=measure_with(observer, p['observer_contract'])).to_dict()
    save(directory/'observation.json', result)
    scores = {k: evaluate_loss(v, result['metadata']['measurements']) for k, v in p['losses'].items()}
    save(directory/'cross-scores.json', scores)
    if result['status'] != 'complete' or any(v['status'] != 'complete' for v in scores.values()):
        raise ValueError('common reference failed; no refill or later inference')
    return {'suggestion': suggestion.to_dict(), 'observation': result}


def run(root):
    require_environment()
    p = require_plan(root)
    with (root/'writer.lock').open('a') as owner, (Path(p['origin']['run'])/'writer.lock').open('r') as previous:
        for handle in (owner, previous):
            fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (root/'started.json').exists():
            raise ValueError('consumed study; no redispatch')
        save(root/'started.json', {'schema': SCHEMA+'.start', 'plan_sha256': p['content_sha256'],
            'pid': os.getpid(), 'started_utc': utc()})
        status, stage, complete, failure = 'stopped', 'initial-readiness', 0, {}
        try:
            for presentation in p['presentations']:
                arm = 'throughput-'+presentation
                c = campaign(root, p, arm, prototype=True)
                progress(root, stage, presentation)
                readiness(root, p, request=c._request([], c._validate(), 1),
                    target=root/'initial-readiness'/presentation)
                require_plan(root)
            observer = CommonContentObserver(root/'observer', p['observer_contract'],
                backend=LocalObserverBackend(inference_lock=root/'inference.lock'))
            pairs = []
            for label in p['reference_order']:
                stage = 'references'; progress(root, stage, label)
                pairs.append(observe(root, p, label, observer)); complete += 1
                require_plan(root)
            context = base.build_context(pairs, world=p['world'], seeds=[SEED], loss_spec=p['losses']['throughput'])
            save(root/'developer-reference-context.json', {k:v for k,v in context.items() if k != 'content_sha256'})
            save(root/'developer-reference-context-ready.json', {'context_sha256': context['content_sha256'],
                'complete_references': len(p['reference_order']), 'completed_utc': utc()})
            for slot in p['schedule']:
                arm, g = slot['arm'], slot['generation']
                c = campaign(root, p, arm, context)
                if c.state['pending'] is not None or len(c.state['records']) != g:
                    raise ValueError('pending/consumed arm slot')
                request = c._request(c.state['records'], c._validate(), 1)
                directory = root/'search'/arm
                stage = 'readiness'; progress(root, stage, arm+':g'+str(g))
                cert = readiness(root, p, request=request, target=directory/f'readiness-{g}')
                def generate(req):
                    return execute(directory/'authoring'/('generation-'+digest(req)), kind='proposal', request=req,
                        provider=p['designer'], source_commit=p['source_commit'], certificate=cert,
                        seconds=p['budget']['proposal_seconds'], maximum_posts=p['budget']['proposal_POSTs_per_session'],
                        inference_lock=root/'inference.lock', post_edit_bank=p['component_bank'])
                stage = 'optimization'; progress(root, stage, arm+':g'+str(g))
                c.advance(simulation_factory=factory_for(directory/'worlds', p, root),
                    generators={'local-designer': generate}, count=1, measurement_adapter=observer.measure,
                    measurement_contract=p['observer_contract'])
                require_plan(root)
            save(root/'selection.json', selection(root, p, context))
            audit = observer.audit()
            save(root/'observer-audit.json', {k:v for k,v in audit.items() if k != 'content_sha256'})
            if read(root/'observer-audit.json') != audit:
                raise ValueError('public observer audit retention differs')
            status = stage = 'closed'; progress(root, stage)
        except BaseException as error:
            failure = {'error_type': type(error).__name__, 'error': str(error)}
            raise
        finally:
            save(root/'terminal.json', {'schema': SCHEMA+'.terminal', 'status': status, 'stage': stage,
                'complete_references': complete, 'ended_utc': utc(), 'held_out_evaluation': False,
                'publication_ready': False, **failure})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('prepare', 'run'))
    parser.add_argument('--output', type=Path, required=True)
    for name in ('origin-run', 'origin-source', 'audit-one', 'audit-two'):
        parser.add_argument('--'+name, type=Path)
    args = parser.parse_args(); args.output = args.output.resolve()
    if args.stage == 'run':
        run(args.output); return
    require_environment()
    if args.output.exists() or any(getattr(args, k) is None for k in ('origin_run', 'origin_source', 'audit_one', 'audit_two')):
        parser.error('fresh output and closed original catalog source/audits required')
    original = read(args.origin_run/'plan.json'); audit = read(args.audit_one)
    origin = {'run': str(args.origin_run.resolve()), 'source': str(args.origin_source.resolve()),
        'source_commit': audit['source_commit'],
        'audit_files': {str(path.resolve()): file_sha256(path) for path in (args.audit_one, args.audit_two)},
        'operator_plan_file_sha256': file_sha256(Path(original['origin']['run'])/'plan.json')}
    with (args.origin_run/'writer.lock').open('r') as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        operator, old, audit = base.origin_evidence(origin)
        if not Path(operator['data_cache']).is_dir():
            raise ValueError('existing offline corpus required')
        p = build_plan(operator, old, audit, source=pinned_revision(ROOT), backend=backend_binding(operator['designer']),
            observer_backend=backend_binding({k: operator['scientist'][k] for k in ('model', 'model_digest')}), origin=origin)
        args.output.mkdir(parents=True); save(args.output/'plan.json', p); require_plan(args.output)
    print(json.dumps({'prepared_source': p['source_commit'], 'native_worlds_upper_bound': 20, 'new_model_calls': 0}), flush=True)


if __name__ == '__main__':
    main()
