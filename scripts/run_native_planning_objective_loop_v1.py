"""Finite free planning/allocation T/U search in the original capacity world."""
import argparse
import fcntl
import json
import os
from pathlib import Path

from scripts.analyze_native_open_v7 import _inventory
from scripts.run_pre_scale_search_v1 import require_environment, ENVIRONMENT
from scripts.run_native_institution_loop_v1 import readiness
from scripts.run_native_objective_instrument_loop_v1 import factory_for, measure_with, feedback_for, progress, utc
from utopia.optimization.blackbox import Suggestion
from utopia.optimization.common_content_observer import CommonContentObserver, LocalObserverBackend, make_contract
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign
from utopia.optimization.native_benchmark_controls import objective_specs
from utopia.optimization.native_bounded_staged_designer import execute
from utopia.optimization.native_causal_design import OPTION, PRESENTATION
from utopia.optimization.native_development_references import build_context
from utopia.optimization.native_designer_preflight import runtime_binding, backend_binding
from utopia.optimization.native_designer_roles_v38 import validate_designer_binding
from utopia.optimization.native_fixed_production_domain import catalog_planning_design_space
from utopia.optimization.native_design_space import require_candidate_in_space
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.optimization.native_post_edit_feedback_v1 import OPTION as TEST_OPTION
from utopia.optimization.native_world import evaluate_native_suggestion
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest
from utopia.system.native_catalog_planning import catalog_contract
from utopia.system.native_planning_controls import ORDER, planning_controls
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'scienceutopia.native-planning-objective-loop.v1'
PROTOCOL = 'research/protocols/campaigns/native-planning-objective-loop-v1.md'
BANK_MANIFEST = 'research/data/native-resource-component-fixtures-v2/summary.json'
CONTENT_LOSS = 'research/objectives/losses/native-common-content-utility-v1.json'
SEED = 61001
OBJECTIVES = ('throughput', 'content-utility')


def read(path): return checked(json.loads(Path(path).read_text()))


def origin_evidence(origin):
    root, source = Path(origin['run']), Path(origin['source'])
    if pinned_revision(source) != origin['source_commit']: raise ValueError('original catalog source changed')
    audits = [read(path) for path in origin['audit_files']]
    if (len(audits) != 2 or audits[0] != audits[1]
            or any(file_sha256(Path(path)) != h for path, h in origin['audit_files'].items())):
        raise ValueError('two matching unchanged original catalog audits required')
    p, audit = read(root / 'plan.json'), audits[0]
    if (p['schema'] != 'scienceutopia.native-catalog-actuation.v1.plan'
            or audit['schema'] != 'scienceutopia.native-catalog-actuation-audit.v1'
            or audit['source_commit'] != p['source_commit'] or p['source_commit'] != origin['source_commit']
            or audit['plan_sha256'] != p['content_sha256'] or audit['closure']['terminal'] != read(root / 'terminal.json')
            or audit['closure']['terminal']['status'] != 'closed' or audit['closure']['terminal']['completed_jobs'] != 3
            or audit['source_proof']['status'] != 'verified-exact-source-closure'
            or audit['new_model_calls'] or audit['new_code_executions']
            or digest(_inventory(root)) != audit['raw_inventory_sha256']):
        raise ValueError('normally closed unchanged native catalog support required')
    operator_path = Path(p['origin']['run']) / 'plan.json'
    if file_sha256(operator_path) != origin['operator_plan_file_sha256']:
        raise ValueError('original operator/bank/support plan changed')
    return read(operator_path), p, audit


def build_plan(operator, catalog_plan, audit, *, source, backend, observer_backend, origin):
    validate_designer_binding(operator['designer'], scientist_binding=operator['scientist'])
    if (len(source) != 40 or any(c not in '0123456789abcdef' for c in source)
            or catalog_plan['scientist'] != operator['scientist']
            or catalog_plan['world']['world_conditions'] != operator['world']['world_conditions']):
        raise ValueError('exact source and unchanged original researcher/capacity bindings required')
    bank = checked(clone(operator['component_bank'])); manifest = read(ROOT / BANK_MANIFEST)
    image = operator['scientist']['image_id']
    if (operator['component_bank_file_sha256'] != manifest['bank_file_sha256']
            or bank['content_sha256'] != manifest['bank_content_sha256']
            or any(r['receipt']['image_id'] != image for r in bank['records'])):
        raise ValueError('literal historical component bank and pinned executor required')
    controls = planning_controls(image, seed=SEED); anchor = controls[ORDER[0]]
    if anchor.to_dict() != catalog_plan['jobs'][0]['system']:
        raise ValueError('literal previous cut agenda anchor required')
    domain = catalog_planning_design_space(anchor, 'code-and-graph')
    for spec in controls.values(): require_candidate_in_space(anchor, spec, domain)
    observer = make_contract(source_commit=source,
        provider={k: operator['scientist'][k] for k in ('model', 'model_digest')},
        backend=observer_backend, maximum_posts=1500, critics=3)
    experiment = {'protocol': PROTOCOL, 'role': 'objective-conditioned-native-planning-design'}
    post_edit = feedback_for(bank, source, image).contract
    world = {**clone(catalog_plan['world']), 'source_commit': source, 'experiment': experiment,
        'measurement_adapter_contract': observer, 'classification': 'actual-native-planning-objective-loop-v1'}
    return {'schema': SCHEMA + '.plan', 'source_commit': source, 'runtime': runtime_binding(),
        'protocol': PROTOCOL, 'protocol_sha256': file_sha256(ROOT / PROTOCOL), 'origin': clone(origin),
        'origin_audit_content_sha256': audit['content_sha256'], 'launch_environment': clone(ENVIRONMENT),
        **{k: clone(operator[k]) for k in ('scientist', 'designer', 'data_cache', 'component_support')},
        'backend': clone(backend), 'world': world, 'experiment': experiment, 'observer_contract': observer,
        'losses': {'throughput': objective_specs()['throughput'],
            'content-utility': json.loads((ROOT / CONTENT_LOSS).read_text())},
        'objectives': list(OBJECTIVES), 'generations': 3, 'optimizer_seed': 68011,
        'catalog': catalog_contract(), 'initial_system': anchor.to_dict(), 'design_space': domain,
        'reference_systems': {k: v.to_dict() for k, v in controls.items()}, 'reference_order': list(ORDER),
        'strategies': {'local-designer': {'kind': 'code-and-graph', 'protocol': PROTOCOL,
            OPTION: True, PRESENTATION: 'inline', TEST_OPTION: post_edit}},
        'component_bank': bank, 'component_bank_file_sha256': operator['component_bank_file_sha256'],
        'fixture_manifest_file_sha256': file_sha256(ROOT / BANK_MANIFEST), 'post_edit_contract': post_edit,
        'schedule': [{'objective': o, 'generation': g} for g in range(3)
            for o in (OBJECTIVES if g % 2 == 0 else OBJECTIVES[::-1])],
        'budget': {'reference_worlds': 8, 'candidate_slots': 6, 'native_worlds_upper_bound': 14,
            'scientist_HTTP_attempts_per_world': 1024, 'world_wall_seconds': 7200,
            'observer_POSTs_upper_bound': 1500, 'readiness_sessions': 7,
            'readiness_POSTs_per_session': 40, 'readiness_seconds': 1200,
            'proposal_POSTs_per_session': 16, 'proposal_seconds': 1800,
            'component_attempts_per_proposal': 64, 'replace_failed_slots': False},
        'reference_parent_policy': 'best assigned loss across fresh common references and own complete history',
        'final_selection_policy': 'earliest tied complete own literal submission; no automatic fallback',
        'development_seed_reused': True, 'held_out_evaluation': False, 'publication_ready': False,
        'P_is_an_objective_or_constraint': False, 'old_losses_reused_as_development_observations': False}


def require_plan(root):
    p = read(root / 'plan.json')
    if p['source_commit'] != pinned_revision(ROOT) or p['runtime'] != runtime_binding():
        raise ValueError('exact clean planning study source/runtime required')
    operator, original, audit = origin_evidence(p['origin'])
    expected = build_plan(operator, original, audit, source=p['source_commit'], backend=p['backend'],
        observer_backend=p['observer_contract']['backend'], origin=p['origin'])
    if expected != {k: v for k, v in p.items() if k != 'content_sha256'}:
        raise ValueError('literal planning study reconstruction differs')
    support = Path(p['component_support']['directory']); summary = read(support / 'summary.json')
    if (file_sha256(support / 'plan.json') != p['component_support']['plan_file_sha256']
            or file_sha256(support / 'summary.json') != p['component_support']['summary_file_sha256']
            or summary['status'] != 'closed' or len(summary['observations']) != 12
            or not all(o['original_result_matches'] for o in summary['observations'])
            or read(support / 'plan.json')['bank_file_sha256'] != p['component_bank_file_sha256']):
        raise ValueError('original twelve-call component support changed')
    return p


def campaign(root, p, objective, context=None, *, prototype=False):
    directory = root / 'initial-readiness/campaign' if prototype else root / 'search' / objective / 'campaign'
    kw = {} if context is None else {'development_references': context}
    return NativeAdaptiveDesignCampaign(directory, initial_system=SystemSpec.from_dict(p['initial_system']),
        loss_spec=p['losses'][objective], seeds=[SEED], world_binding=p['world'], strategies=p['strategies'],
        mode='blackbox', seed=p['optimizer_seed'], design_space=p['design_space'], **kw)


def selection(root, p, context, *, frozen_utc=None, campaign_loader=None):
    selected = {}; load = campaign if campaign_loader is None else campaign_loader
    for objective in p['objectives']:
        c = load(root, p, objective, context)
        if c.state['pending'] is not None or len(c.state['records']) != p['generations']:
            raise ValueError('all six terminal own proposals required')
        pool = [o for r in c.state['records'] for o in r['observations'] if o and o['status'] == 'complete' and o['loss'] is not None]
        best = min((o['loss'] for o in pool), default=None); ties = [o for o in pool if o['loss'] == best]
        selected[objective] = {'loss': best, 'all_tied_ids': [o['suggestion_id'] for o in ties],
            'selected_id': ties[0]['suggestion_id'] if ties else None, 'system': clone(ties[0]['candidate']) if ties else None,
            'completed_submissions': len(pool)}
    return {'schema': SCHEMA + '.selection', 'plan_sha256': p['content_sha256'], 'selected': selected,
        'baseline_fallback': False, 'frozen_utc': utc() if frozen_utc is None else frozen_utc, 'held_out_evaluation': False}


def observe(root, p, label, observer):
    directory = root / 'references' / label; identity = 'reference-' + label
    if (directory / 'started.json').exists(): raise ValueError('consumed reference; no redispatch')
    suggestion = Suggestion(identity, p['reference_systems'][label], 0, 'developer-reference')
    save(directory / 'started.json', {'suggestion': suggestion.to_dict(), 'seed': SEED, 'started_utc': utc()})
    result = evaluate_native_suggestion(suggestion, seeds=[SEED], simulation_factory=factory_for(directory / 'worlds', p, root),
        loss_spec=p['losses']['throughput'], measurement_adapter=measure_with(observer, p['observer_contract'])).to_dict()
    save(directory / 'observation.json', result)
    scores = {k: evaluate_loss(v, result['metadata']['measurements']) for k, v in p['losses'].items()}
    save(directory / 'cross-scores.json', scores)
    if result['status'] != 'complete' or any(v['status'] != 'complete' for v in scores.values()):
        raise ValueError('common reference failed; no refill or later inference')
    return {'suggestion': suggestion.to_dict(), 'observation': result}


def run(root):
    require_environment(); p = require_plan(root)
    with (root / 'writer.lock').open('a') as owner, (Path(p['origin']['run']) / 'writer.lock').open('r') as previous:
        for handle in (owner, previous): fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (root / 'started.json').exists(): raise ValueError('consumed study; no redispatch')
        save(root / 'started.json', {'schema': SCHEMA + '.start', 'plan_sha256': p['content_sha256'], 'pid': os.getpid(), 'started_utc': utc()})
        status, stage, complete, failure = 'stopped', 'initial-readiness', 0, {}
        try:
            c = campaign(root, p, 'throughput', prototype=True); progress(root, stage)
            readiness(root, p, request=c._request([], c._validate(), 1), numeric=False, target=root / 'initial-readiness')
            observer = CommonContentObserver(root / 'observer', p['observer_contract'],
                backend=LocalObserverBackend(inference_lock=root / 'inference.lock'))
            pairs = []
            for label in p['reference_order']:
                stage = 'references'; progress(root, stage, label)
                pairs.append(observe(root, p, label, observer)); complete += 1; require_plan(root)
            context = build_context(pairs, world=p['world'], seeds=[SEED], loss_spec=p['losses']['throughput'])
            save(root / 'developer-reference-context.json', {k: v for k, v in context.items() if k != 'content_sha256'})
            save(root / 'developer-reference-context-ready.json', {'context_sha256': context['content_sha256'],
                'complete_references': len(p['reference_order']), 'completed_utc': utc()})
            for slot in p['schedule']:
                objective, g = slot['objective'], slot['generation']; c = campaign(root, p, objective, context)
                if c.state['pending'] is not None or len(c.state['records']) != g: raise ValueError('pending/consumed slot')
                request = c._request(c.state['records'], c._validate(), 1); directory = root / 'search' / objective
                stage = 'readiness'; progress(root, stage, objective + ':g' + str(g))
                cert = readiness(root, p, request=request, numeric=False, target=directory / f'readiness-{g}')
                def generate(req):
                    return execute(directory / 'authoring' / ('generation-' + digest(req)), kind='proposal', request=req,
                        provider=p['designer'], source_commit=p['source_commit'], certificate=cert, seconds=1800,
                        inference_lock=root / 'inference.lock', post_edit_bank=p['component_bank'])
                stage = 'optimization'; progress(root, stage, objective + ':g' + str(g))
                c.advance(simulation_factory=factory_for(directory / 'worlds', p, root), generators={'local-designer': generate},
                    count=1, measurement_adapter=observer.measure, measurement_contract=p['observer_contract'])
                require_plan(root)
            save(root / 'selection.json', selection(root, p, context)); audit = observer.audit()
            save(root / 'observer-audit.json', {k: v for k, v in audit.items() if k != 'content_sha256'})
            if read(root / 'observer-audit.json') != audit: raise ValueError('public observer audit retention differs')
            status = stage = 'closed'; progress(root, stage)
        except BaseException as error:
            failure = {'error_type': type(error).__name__, 'error': str(error)}; raise
        finally:
            save(root / 'terminal.json', {'schema': SCHEMA + '.terminal', 'status': status, 'stage': stage,
                'complete_references': complete, 'ended_utc': utc(), 'held_out_evaluation': False, 'publication_ready': False, **failure})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage', choices=('prepare', 'run')); parser.add_argument('--output', type=Path, required=True)
    for name in ('origin-run', 'origin-source', 'audit-one', 'audit-two'): parser.add_argument('--' + name, type=Path)
    args = parser.parse_args(); args.output = args.output.resolve()
    if args.stage == 'run': run(args.output); return
    require_environment()
    if args.output.exists() or any(getattr(args, k) is None for k in ('origin_run', 'origin_source', 'audit_one', 'audit_two')):
        parser.error('fresh output and closed original catalog source/audits required')
    raw_plan = read(args.origin_run / 'plan.json'); audit = read(args.audit_one)
    origin = {'run': str(args.origin_run.resolve()), 'source': str(args.origin_source.resolve()), 'source_commit': audit['source_commit'],
        'audit_files': {str(path.resolve()): file_sha256(path) for path in (args.audit_one, args.audit_two)},
        'operator_plan_file_sha256': file_sha256(Path(raw_plan['origin']['run']) / 'plan.json')}
    with (args.origin_run / 'writer.lock').open('r') as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB); operator, old, audit = origin_evidence(origin)
        if not Path(operator['data_cache']).is_dir(): raise ValueError('existing offline corpus required')
        p = build_plan(operator, old, audit, source=pinned_revision(ROOT), backend=backend_binding(operator['designer']),
            observer_backend=backend_binding({k: operator['scientist'][k] for k in ('model', 'model_digest')}), origin=origin)
        args.output.mkdir(parents=True); save(args.output / 'plan.json', p); require_plan(args.output)
    print(json.dumps({'prepared_source': p['source_commit'], 'native_worlds_upper_bound': 14, 'new_model_calls': 0}), flush=True)


if __name__ == '__main__': main()
