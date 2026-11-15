"""Finite objective-conditioned whole-system search with strong visible controls."""
import argparse
from contextlib import ExitStack
import fcntl
import os
from pathlib import Path

from scripts import run_native_legacy_topic_pilot_v1 as pilot
from scripts import run_native_workflow_objective_loop_v1 as base
from scripts.analyze_native_open_v7 import _inventory
from scripts.reports.stage_native_component_fixtures_v1 import collect, TOPIC_SCOPE
from utopia.optimization.blackbox import Suggestion, Observation
from utopia.optimization.common_content_observer import CommonContentObserver, LocalObserverBackend, make_contract
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign
from utopia.optimization.native_development_references import build_context
from utopia.optimization.native_designer_preflight import backend_binding, runtime_binding
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_parent_evidence_v46 import OPTION as PARENT_OPTION, MODE as PARENT_MODE
from utopia.optimization.native_resource_cost import measure as resource_measure
from utopia.optimization.native_topic_objectives_v1 import objective_specs, OBJECTIVES
from utopia.optimization.native_world import evaluate_native_suggestion
from utopia.optimization.native_institution_workflow_domain_v6 import (
    SCOPE, institution_workflow_design_space, require_institution_workflow_candidate,
    verify_institution_workflow_interval)
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import file_sha256

ROOT, SEED, staged_author = base.ROOT, pilot.SEED, base.staged_author
SCHEMA = 'scienceutopia.native-topic-free-optimization.v1'
AUDIT_SCHEMA = SCHEMA + '.audit'
PROTOCOL = 'research/protocols/campaigns/native-topic-free-optimization-v1.md'
AUDIT_SCRIPTS = ['scripts/run_native_topic_free_optimization_v1.py',
                 'scripts/audit_native_topic_free_optimization_v1.py']
AUTHOR_ADAPTERS = {
    'utopia/optimization/native_open_workflow_submission_v1.py': 'Explicit v5/v6 author compiler; historical v4/v5 authority unchanged',
    'utopia/optimization/native_workflow_staged_designer_v1.py': 'Explicit new developer component evidence scope',
    'utopia/system/native_capability_catalog.py': 'Author-facing original-topic action semantics and validator identities',
    'utopia/optimization/native_objective_view.py': 'Author-facing passive resource metric definitions; no world/loss change',
    'utopia/optimization/native_workflow_domain_v4.py': 'Explicit private opt-in institution-work authority; historical v4/v5 rejection unchanged',
}
read, save, utc = base.read, base.save, base.utc
scientist_factory, designer_for = base.scientist_factory, base.designer_for
history_keys, history_key = base.history_keys, base.history_key
history_directory, history_metadata = base.history_directory, base.history_metadata


def open_institutions(p):
    if (p.get('schema') != SCHEMA+'.plan' or p.get('protocol') != PROTOCOL
            or p.get('designer_mode') != staged_author.MODE
            or p.get('design_space', {}).get('world_law_scope') != SCOPE):
        raise ValueError('explicit prospective free-topic optimization scope required')
    return True


def require_candidate(anchor, candidate, *, structure_only=False):
    if structure_only:
        raise ValueError('this study is whole-system, not a structure-only comparator')
    return require_institution_workflow_candidate(anchor, candidate)


verify_interval = verify_institution_workflow_interval


def preceding_evidence(origin):
    raw, source = Path(origin['run']), Path(origin['source'])
    paths = [Path(p) for p in origin['audit_files']]
    if (len(paths) != 2 or len(set(paths)) != 2 or paths[0].read_bytes() != paths[1].read_bytes()
            or {str(p): file_sha256(p) for p in paths} != origin['audit_files']):
        raise ValueError('two distinct matching original topic audits required')
    p, audit = read(raw/'plan.json'), read(paths[0])
    if (p['schema'] != pilot.SCHEMA+'.plan' or audit['schema'] != 'scienceutopia.native-legacy-topic-pilot-audit.v1'
            or p['source_commit'] != pinned_revision(source) or audit['source_commit'] != p['source_commit']
            or origin['source_commit'] != p['source_commit'] or audit['plan_sha256'] != p['content_sha256']
            or audit['closure']['terminal'] != read(raw/'terminal.json')
            or audit['closure']['terminal']['status'] != 'closed'
            or audit['closure']['terminal']['completed_jobs'] != 2
            or audit['source_proof']['status'] != 'verified-exact-source-closure'
            or digest(_inventory(raw)) != audit['raw_inventory_sha256']
            or len(audit['worlds']) != 2 or any(w['status'] != 'complete' for w in audit['worlds'])
            or [j['condition'] for j in p['jobs']] != list(pilot.LABELS)
            or audit['automatic_invention'] or audit['policy_selection'] or audit['held_out_world_seeds']):
        raise ValueError('normally closed exact original developer topic pilot required')
    return p, audit


def native_sources(original, source):
    adapters = {path: {'source_commit': pilot.ADAPTER_SOURCE, 'role': role}
                for path, role in pilot.ADAPTERS.items()}
    adapters.update({path: {'source_commit': source, 'role': role} for path, role in AUTHOR_ADAPTERS.items()})
    return base.native_sources(original, adapters=adapters)


def build_plan(original, audit, *, source, origin, backend, observer_backend, bank, evidence, sources):
    if (original['schema'] != pilot.SCHEMA+'.plan' or original['objectives'] != list(OBJECTIVES[:2])
            or original['world']['years'] != 4 or [j['seed'] for j in original['jobs']] != [SEED, SEED]
            or original['automatic_invention'] or original['policy_selection']):
        raise ValueError('literal closed original-topic T/U developer study required')
    anchor = SystemSpec.from_dict(original['jobs'][0]['system'])
    bank = staged_author.require_bank(bank, evidence, anchor.to_dict())
    refs = {j['condition']: clone(j['system']) for j in original['jobs']}
    for spec in refs.values(): require_candidate(anchor, SystemSpec.from_dict(spec))
    observer = make_contract(source_commit=source,
        provider={k: original['scientist'][k] for k in ('model','model_digest')},
        backend=observer_backend, maximum_posts=6000, critics=3)
    ignored = {'source_commit','content_sha256','maximum_posts'}
    if ({k:v for k,v in observer.items() if k not in ignored}
            != {k:v for k,v in original['observer_contract'].items() if k not in ignored}):
        raise ValueError('literal original content observer required')
    feedback = staged_author.component_feedback(bank, original['designer'], source).contract
    experiment = {'protocol': PROTOCOL, 'role': 'objective-conditioned-free-original-topic-systems'}
    return {'schema': SCHEMA+'.plan', 'source_commit': source, 'runtime': runtime_binding(),
        'protocol': PROTOCOL, 'protocol_sha256': file_sha256(ROOT/PROTOCOL),
        'origin': clone(origin), 'origin_audit_content_sha256': audit['content_sha256'],
        'original_pilot_plan_sha256': original['content_sha256'], 'original_native_sources': clone(sources),
        **{k:clone(original[k]) for k in ('scientist','designer','data_cache','catalog',
            'scientist_transport','operational_protocol','launch_environment')},
        'additional_measurements': {**clone(original['additional_measurements']),
            'optimization_loss_changed': True, 'historical_losses_unchanged': True,
            'new_loss_id': 'native-topic-resource-aware-content-v1'},
        'backend': clone(backend), 'observer_contract': observer, 'experiment': experiment,
        'world': {**clone(original['world']), 'source_commit': source, 'experiment': experiment,
            'classification': 'actual-native-topic-free-optimization-v1', 'measurement_adapter_contract': observer},
        'initial_system': anchor.to_dict(), 'design_space': institution_workflow_design_space(anchor),
        'losses': objective_specs(original['losses']), 'objectives': list(OBJECTIVES),
        'reference_systems': refs, 'reference_order': list(pilot.LABELS),
        'optimizer_reference_labels': list(pilot.LABELS), 'generations': 2, 'optimizer_seed': 68011,
        'schedule': [{'objective': o, 'generation': g} for g in range(2)
                     for o in (OBJECTIVES if g == 0 else OBJECTIVES[::-1])],
        'designer_mode': staged_author.MODE, 'authoring_scope': base.OPEN_SCOPE,
        'author_settings': staged_author.settings(),
        'author_profile_protocol': {'path': staged_author.PROTOCOL,
                                   'sha256': file_sha256(ROOT/staged_author.PROTOCOL)},
        'component_bank': clone(bank), 'component_evidence': clone(evidence), 'post_edit_contract': feedback,
        'strategies': {'local-workflow-designer': {'protocol': PROTOCOL, 'method': staged_author.MODE,
            'post_edit_component_contract': clone(feedback), PARENT_OPTION: PARENT_MODE}},
        'budget': {'fresh_reference_worlds': 2, 'candidate_slots': 6, 'native_worlds_upper_bound': 8,
            'scientist_HTTP_attempts_per_world': 1024, 'world_wall_seconds': 7200,
            'observer_POSTs_upper_bound': 6000, 'designer_POSTs_upper_bound': 376,
            'readiness_sessions': 7, 'proposal_POSTs_per_session': 16,
            'readiness_POSTs_per_session': 40, 'component_probes_upper_bound': 384,
            'designer_session_wall_seconds': 1800, 'replace_failed_slots': False},
        'development_seed_reused': True, 'held_out_evaluation': False,
        'independent_optimizer_replications': False, 'publication_ready': False}


def require_plan(root):
    p = read(root/'plan.json')
    if p['source_commit'] != pinned_revision(ROOT) or p['runtime'] != runtime_binding():
        raise ValueError('exact clean free-topic source/runtime required')
    original, audit = preceding_evidence(p['origin'])
    expected = build_plan(original, audit, source=p['source_commit'], origin=p['origin'], backend=p['backend'],
        observer_backend=p['observer_contract']['backend'], bank=p['component_bank'], evidence=p['component_evidence'],
        sources=native_sources(original['original_native_sources']['original_source'], p['source_commit']))
    if expected != {k:v for k,v in p.items() if k != 'content_sha256'}:
        raise ValueError('literal free-topic objectives/parents/authority/budgets reconstruction differs')
    return p


def reference_context(p, pairs):
    expected = ['workflow-reference-'+label.lower() for label in p['reference_order']]
    if [v['suggestion']['suggestion_id'] for v in pairs] != expected:
        raise ValueError('complete ordered strong same-authority references required')
    return build_context(pairs, world=p['world'], seeds=[SEED], loss_spec=p['losses']['throughput'])


def campaign(root, p, objective, context=None, *, prototype=False):
    if objective not in p['objectives']: raise ValueError('declared objective required')
    directory = root/'initial-readiness/campaign' if prototype else history_directory(root, objective)/'campaign'
    return NativeAdaptiveDesignCampaign(directory, initial_system=SystemSpec.from_dict(p['initial_system']),
        loss_spec=p['losses'][objective], seeds=[SEED], world_binding=p['world'], strategies=p['strategies'],
        mode='blackbox', seed=p['optimizer_seed'], design_space=p['design_space'],
        **({} if context is None else {'development_references': context}))


def measurement(p, observer):
    original = base.measure_with(observer, p['observer_contract'])
    def apply(sim, value):
        result = resource_measure(sim, original(sim, value))
        return {**result, 'native_workflow_interval': verify_interval(SystemSpec.from_dict(p['initial_system']),
            sim.native_system.spec, sim.native_system.events, years=4)}
    return apply


def reconstruct_extra_measurement(p, state, rebuilt, run):
    return pilot.additional_from_checkpoints(rebuilt, Path(run['checkpoint_path']).parent)


def selection(root, p, context):
    selected = {}
    for objective in p['objectives']:
        c = campaign(root, p, objective, context)
        if c.state['pending'] is not None or len(c.state['records']) != p['generations']:
            raise ValueError('all six own terminal slots required')
        pool = [o for r in c.state['records'] for o in r['observations'] if o and o['status'] == 'complete']
        best = min((o['loss'] for o in pool), default=None)
        ties = [o for o in pool if o['loss'] == best]
        selected[objective] = {'loss': best, 'completed_submissions': len(pool),
            'all_tied_ids': [o['suggestion_id'] for o in ties],
            'selected_id': ties[0]['suggestion_id'] if ties else None,
            'system': clone(ties[0]['candidate']) if ties else None}
    return {'schema': SCHEMA+'.selection', 'plan_sha256': p['content_sha256'],
            'selected': selected, 'baseline_fallback': False, 'held_out_evaluation': False}


def run(root):
    base.require_environment(); p = require_plan(root)
    with ExitStack() as stack:
        for path in sorted({root/'writer.lock', Path(p['origin']['run'])/'writer.lock'}):
            handle = stack.enter_context(path.open('a' if path == root/'writer.lock' else 'r'))
            fcntl.flock(handle, fcntl.LOCK_EX|fcntl.LOCK_NB)
        if (root/'started.json').exists(): raise ValueError('consumed free-topic study; no redispatch')
        save(root/'started.json', {'schema': SCHEMA+'.start', 'plan_sha256': p['content_sha256'],
            'pid': os.getpid(), 'started_utc': utc()})
        stage, consumed, observations, status = 'initial-readiness', 0, 0, 'stopped'
        try:
            c = campaign(root, p, OBJECTIVES[0], prototype=True)
            designer_for(root/'initial-readiness/author', p, root).calibrate(c._request([], c._validate(), 1))
            require_plan(root)
            observer = CommonContentObserver(root/'observer', p['observer_contract'],
                backend=LocalObserverBackend(inference_lock=root/'inference.lock'))
            pairs = []
            for label in p['reference_order']:
                stage = 'references'; base.progress(root, stage, label)
                directory = root/'references'/label
                s = Suggestion('workflow-reference-'+label.lower(), p['reference_systems'][label], 0, 'developer-reference')
                save(directory/'started.json', {'suggestion': s.to_dict(), 'seed': SEED, 'started_utc': utc()})
                o = evaluate_native_suggestion(s, seeds=[SEED], simulation_factory=scientist_factory(directory/'worlds', p, root),
                    loss_spec=p['losses']['throughput'], measurement_adapter=measurement(p, observer)).to_dict()
                save(directory/'observation.json', o)
                save(directory/'cross-scores.json', {k:evaluate_loss(v,o['metadata']['measurements']) for k,v in p['losses'].items()})
                if o['status'] != 'complete': raise ValueError('reference technical null; no refill')
                pairs.append({'suggestion':s.to_dict(),'observation':Observation.from_dict(o).to_dict()})
                observations += 1; require_plan(root)
            context = reference_context(p,pairs)
            save(root/'developer-reference-context.json', {k:v for k,v in context.items() if k != 'content_sha256'})
            for slot in p['schedule']:
                objective, generation = slot['objective'], slot['generation']
                c = campaign(root,p,objective,context)
                if c.state['pending'] is not None or len(c.state['records']) != generation:
                    raise ValueError('consumed/pending objective slot; no redispatch')
                request = c._request(c.state['records'],c._validate(),1)
                directory = history_directory(root,objective)
                author = designer_for(directory/'authoring',p,root)
                stage = 'readiness'; base.progress(root,stage,objective+':g'+str(generation))
                certificate = author.calibrate(request); require_plan(root)
                def generate(req):
                    if req != request: raise ValueError('proposal request differs from actual readiness')
                    return base.generation_definition(author.execute(req,purpose='proposal',certificate=certificate))
                stage = 'optimization'; base.progress(root,stage,objective+':g'+str(generation))
                record = c.advance(simulation_factory=scientist_factory(directory/'worlds',p,root),
                    generators={'local-workflow-designer':generate},count=1,
                    measurement_adapter=measurement(p,observer),measurement_contract=p['observer_contract'])
                consumed += 1; observations += sum(o is not None for o in record['observations']); require_plan(root)
            save(root/'selection.json',selection(root,p,context)); base.retain_observer_audit(root,observer)
            status = stage = 'closed'; base.progress(root,stage,None)
        except BaseException as error:
            save(root/'failure.json', {'error_type':type(error).__name__,'error':str(error),
                'stage':stage,'consumed_slots':consumed,'no_retry':True})
            raise
        finally:
            save(root/'terminal.json', {'schema': SCHEMA+'.terminal','status':status,'stage':stage,
                'consumed_slots':consumed,'observations':observations,'ended_utc':utc(),
                'no_retry':True,'held_out_evaluation':False,'publication_ready':False})


def prepare(args):
    base.require_environment(); source = pinned_revision(ROOT)
    origin = {'run':str(args.origin_run.resolve()),'source':str(args.origin_source.resolve()),
        'source_commit':read(args.audit_one)['source_commit'],
        'audit_files':{str(p.resolve()):file_sha256(p) for p in (args.audit_one,args.audit_two)}}
    output = args.output.resolve()
    if output.exists() or output.is_relative_to(args.origin_run.resolve()):
        raise ValueError('fresh separate free-topic root required')
    with (args.origin_run/'writer.lock').open('r') as handle:
        fcntl.flock(handle,fcntl.LOCK_EX|fcntl.LOCK_NB)
        original,audit = preceding_evidence(origin)
        if not Path(original['data_cache']).is_dir(): raise ValueError('existing offline corpus required')
        bank = collect(args.origin_run,args.audit_one,scope=TOPIC_SCOPE,source_root=args.origin_source)
        bank = {**bank,'content_sha256':digest(bank)}
        evidence = {'run':str(args.origin_run.resolve()),'source':str(args.origin_source.resolve()),
            'audit':str(args.audit_one.resolve()),'audit_file_sha256':file_sha256(args.audit_one),'staging_scope':TOPIC_SCOPE}
        p = build_plan(original,audit,source=source,origin=origin,
            backend=backend_binding(original['designer']),observer_backend=backend_binding(original['scientist']),
            bank=bank,evidence=evidence,sources=native_sources(original['original_native_sources']['original_source'],source))
        output.mkdir(parents=True); save(output/'plan.json',p); require_plan(output)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('stage',choices=('prepare','run')); parser.add_argument('--output',type=Path,required=True)
    for key in ('origin-run','origin-source','audit-one','audit-two'): parser.add_argument('--'+key,type=Path)
    args = parser.parse_args(); args.output = args.output.resolve()
    if args.stage == 'prepare':
        if any(getattr(args,key) is None for key in ('origin_run','origin_source','audit_one','audit_two')):
            parser.error('closed original topic pilot and paired original audits required')
        prepare(args)
    else: run(args.output)


if __name__ == '__main__': main()
