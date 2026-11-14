"""Matched baseline/parent-trajectory access in the original native world.

Four isolated objective/arm histories share two fresh measured references.
Only R7 enters feedback. Both arms collect identical trace metadata; their
author projections differ. No host repair, scientific merit gate or refill.
"""
import argparse
import fcntl
import json
import os
from pathlib import Path

from scripts import run_native_workflow_objective_loop_v1 as base
from scripts.native_longitudinal_source_scope_v1 import source_scope, require_scope
from utopia.optimization.blackbox import Suggestion
from utopia.optimization.common_content_observer import CommonContentObserver, LocalObserverBackend
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign
from utopia.optimization.native_development_references import build_context
from utopia.optimization.native_designer_preflight import backend_binding, runtime_binding
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_longitudinal_feedback_v1 import (
    attach_projection, contract as access_contract, measurement_adapter)
from utopia.optimization.native_world import evaluate_native_suggestion
from utopia.system import SystemSpec
from utopia.system.design_patch import clone
from utopia.utils.data_utils import file_sha256

ROOT, SEED, staged_author = base.ROOT, base.SEED, base.staged_author
SCHEMA = 'scienceutopia.native-longitudinal-comparison.v1'
AUDIT_SCHEMA = 'scienceutopia.native-longitudinal-comparison-audit.v1'
PROTOCOL = 'research/protocols/campaigns/native-longitudinal-comparison-v1.md'
ARMS = ('scalar', 'parent-trajectory')
OBJECTIVES = ('throughput', 'content-utility')
RESERVED_UNUSED_SEED = 676047151
AUDIT_SCRIPTS = ['scripts/run_native_longitudinal_comparison_v1.py',
    'scripts/audit_native_longitudinal_comparison_v1.py']
read, save, utc = base.read, base.save, base.utc
scientist_factory, designer_for = base.scientist_factory, base.designer_for


def open_institutions(p):
    if (p.get('schema') != SCHEMA+'.plan' or p.get('protocol') != PROTOCOL
            or p.get('designer_mode') != staged_author.MODE or p.get('authoring_scope') != base.OPEN_SCOPE):
        raise ValueError('explicit prospective longitudinal/open-institution scope required')
    return True


def history_keys(p):
    return [(a, o) for a in p['arms'] for o in p['objectives']]


def history_key(slot): return slot['arm'], slot['objective']


def history_objective(key): return key[1]


def history_metadata(key): return {'arm': key[0]}


def history_directory(root, key):
    if not isinstance(key, tuple) or key[0] not in ARMS or key[1] not in OBJECTIVES:
        raise ValueError('declared arm/objective history required')
    return root/'search'/key[0]/key[1]


def build_plan(original, audit, *, source, origin, backend, observer_backend,
        prerequisite, declaration, component_bank, component_evidence, scientist_transport=None):
    require_scope(declaration, ROOT, source_commit=source)
    inherited = {'original_source': original['source_commit'],
        'comparison_base': declaration['base_native_source_commit'],
        'method': 'explicit-prospective-longitudinal-author-source-scope-v2',
        'declaration': clone(declaration), 'legacy_original_guard_reused': False}
    p = base.build_plan(original, audit, source=source, origin=origin, backend=backend,
        observer_backend=observer_backend, prerequisite=prerequisite, sources=inherited,
        designer_mode=staged_author.MODE, component_bank=component_bank,
        component_evidence=component_evidence, scientist_transport=scientist_transport)
    p.update(schema=SCHEMA+'.plan', protocol=PROTOCOL, protocol_sha256=file_sha256(ROOT/PROTOCOL),
        arms=list(ARMS), source_declaration=clone(declaration), reserved_unused_seeds=[RESERVED_UNUSED_SEED])
    p['experiment'] = {'protocol': PROTOCOL, 'role': 'matched-longitudinal-author-observation-access'}
    p['world'].update(experiment=clone(p['experiment']), classification='actual-native-longitudinal-comparison-v1')
    # No arm identifier enters world conditions, scientist generation settings,
    # corpus, loss or institution. The same optimizer seed is used in both arms.
    order = [(ARMS[0], OBJECTIVES[0]), (ARMS[1], OBJECTIVES[1]),
        (ARMS[0], OBJECTIVES[1]), (ARMS[1], OBJECTIVES[0])]
    p['schedule'] = [{'arm': a, 'objective': o, 'generation': g} for g in range(3)
        for a, o in (order if g % 2 == 0 else order[::-1])]
    config = p['author_settings']
    p['budget'].update(candidate_slots=12, native_worlds_upper_bound=14,
        readiness_sessions=13,
        designer_POSTs_upper_bound=13*config['calibration_maximum_posts']+12*config['proposal_maximum_posts'],
        component_probes_upper_bound=12*config['maximum_component_probes'])
    p['comparison'] = {'information_only': True, 'worlds_shared_only_for_references': True,
        'designer_context_tokens_both_arms': 65536, 'designer_output_tokens_both_arms': 8192,
        'context_revision': 'matched-bounded-author-64k-v1',
        'cross_arm_own_feedback': False, 'hand_reference_visible': False,
        'baseline_keeps_original_diagnostics_and_probes': True,
        'same_optimizer_seed_is_not_independent_replication': True,
        'automatic_truncation': False, 'require_improvement_or_novelty': False}
    return p


def require_plan(root):
    p = read(root/'plan.json')
    if p['source_commit'] != pinned_revision(ROOT) or p['runtime'] != runtime_binding():
        raise ValueError('exact clean prospective native comparison source/runtime required')
    original, audit = base.origin_evidence(p['origin'])
    if base.prerequisite_binding(p['prerequisite']['directory']) != p['prerequisite']:
        raise ValueError('prospective comparison prerequisite changed')
    expected = build_plan(original, audit, source=p['source_commit'], origin=p['origin'], backend=p['backend'],
        observer_backend=p['observer_contract']['backend'], prerequisite=p['prerequisite'],
        declaration=source_scope(ROOT, source_commit=p['source_commit']),
        component_bank=p['component_bank'], component_evidence=p['component_evidence'],
        scientist_transport=p.get('scientist_transport'))
    if expected != {k: v for k, v in p.items() if k != 'content_sha256'}:
        raise ValueError('literal prospective comparison reconstruction differs')
    return p


def reference_context(p, pairs):
    if [v['suggestion']['suggestion_id'] for v in pairs] != [
            'workflow-reference-'+label.lower() for label in p['reference_order']]:
        raise ValueError('complete ordered native references required')
    visible = [v for v in pairs if v['suggestion']['suggestion_id'] == 'workflow-reference-r7-original']
    if len(visible) != 1 or p['optimizer_reference_labels'] != ['R7-original']:
        raise ValueError('only declared original R7 may enter either arm')
    return build_context(visible, world=p['world'], seeds=[SEED], loss_spec=p['losses']['throughput'])


def campaign(root, p, key, context=None, *, prototype=False):
    if prototype:
        key = (ARMS[0], key)
    path = root/'initial-readiness/campaign' if prototype else history_directory(root, key)/'campaign'
    refs = [] if context is None else [pair['suggestion']['suggestion_id'] for pair in context['pairs']]
    return NativeAdaptiveDesignCampaign(path, initial_system=SystemSpec.from_dict(p['initial_system']),
        loss_spec=p['losses'][history_objective(key)], seeds=[SEED], world_binding=p['world'],
        strategies=p['strategies'], mode='blackbox', seed=p['optimizer_seed'], design_space=p['design_space'],
        longitudinal_access=access_contract(key[0], source_commit=p['source_commit'], seeds=[SEED], reference_ids=refs),
        **({} if context is None else {'development_references': context}))


def measurement(p, observer):
    return measurement_adapter(base.measurement(p, observer), source_commit=p['source_commit'], years=4)


def reconstruct_extra_measurement(p, state, rebuilt, run):
    from utopia.optimization.native_trajectory_projection_v1 import project_checkpoint
    view = project_checkpoint(state, source_commit=p['source_commit'],
        system_fingerprint=rebuilt['system_fingerprint'], seed=run['seed'], years=4,
        checkpoint_file_sha256=run['checkpoint_sha256'])
    return attach_projection(rebuilt, view, run=run)


def selection(root, p, context):
    selected = {}
    for key in history_keys(p):
        c = campaign(root, p, key, context)
        if c.state['pending'] is not None or len(c.state['records']) != 3:
            raise ValueError('all twelve own comparison slots required')
        pool = [o for r in c.state['records'] for o in r['observations'] if o and o['status'] == 'complete']
        best = min((o['loss'] for o in pool), default=None)
        ties = [o for o in pool if o['loss'] == best]
        selected['::'.join(key)] = {'arm': key[0], 'objective': key[1], 'loss': best,
            'completed_submissions': len(pool), 'all_tied_ids': [o['suggestion_id'] for o in ties],
            'selected_id': ties[0]['suggestion_id'] if ties else None,
            'system': clone(ties[0]['candidate']) if ties else None}
    return {'schema': SCHEMA+'.selection', 'plan_sha256': p['content_sha256'],
        'selected': selected, 'baseline_fallback': False, 'held_out_evaluation': False}


def run(root):
    base.require_environment(); p = require_plan(root); base.require_prerequisite(p['prerequisite'])
    with (root/'writer.lock').open('a') as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (root/'started.json').exists(): raise ValueError('consumed comparison; no redispatch')
        save(root/'started.json', {'schema': SCHEMA+'.start', 'plan_sha256': p['content_sha256'],
            'pid': os.getpid(), 'started_utc': utc()})
        stage, consumed, observations, status = 'initial-readiness', 0, 0, 'stopped'
        try:
            author = designer_for(root/'initial-readiness/author', p, root)
            c = campaign(root, p, OBJECTIVES[0], prototype=True)
            author.calibrate(c._request([], c._validate(), 1)); require_plan(root)
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
                save(directory/'cross-scores.json', {k: evaluate_loss(v, o['metadata']['measurements']) for k, v in p['losses'].items()})
                if o['status'] != 'complete': raise ValueError('comparison reference failed; no refill')
                pairs.append({'suggestion': s.to_dict(), 'observation': o}); observations += 1; require_plan(root)
            context = reference_context(p, pairs)
            save(root/'developer-reference-context.json', {k: v for k, v in context.items() if k != 'content_sha256'})
            for slot in p['schedule']:
                key, g = history_key(slot), slot['generation']; c = campaign(root, p, key, context)
                if c.state['pending'] is not None or len(c.state['records']) != g:
                    raise ValueError('consumed/pending comparison generation; no redispatch')
                request = c._request(c.state['records'], c._validate(), 1)
                directory = history_directory(root, key); author = designer_for(directory/'authoring', p, root)
                stage = 'readiness'; base.progress(root, stage, '::'.join(key)+':g'+str(g))
                certificate = author.calibrate(request); require_plan(root)
                def generate(req):
                    if req != request: raise ValueError('generation request differs from actual calibration')
                    return base.generation_definition(author.execute(req, purpose='proposal', certificate=certificate))
                stage = 'optimization'; base.progress(root, stage, '::'.join(key)+':g'+str(g))
                record = c.advance(simulation_factory=scientist_factory(directory/'worlds', p, root),
                    generators={'local-workflow-designer': generate}, count=1,
                    measurement_adapter=measurement(p, observer), measurement_contract=p['observer_contract'])
                consumed += 1; observations += sum(o is not None for o in record['observations']); require_plan(root)
            save(root/'selection.json', selection(root, p, context))
            base.retain_observer_audit(root, observer); status = stage = 'closed'; base.progress(root, stage, None)
        except BaseException as error:
            save(root/'terminal.json', {'schema': SCHEMA+'.terminal', 'status': status, 'stage': stage,
                'consumed_slots': consumed, 'observations': observations, 'ended_utc': utc(),
                'error_type': type(error).__name__, 'error': str(error), 'no_retry': True})
            raise
        save(root/'terminal.json', {'schema': SCHEMA+'.terminal', 'status': status, 'stage': stage,
            'consumed_slots': consumed, 'observations': observations, 'ended_utc': utc(), 'no_retry': True})


def prepare(args):
    base.require_environment(); source = pinned_revision(ROOT)
    if args.output.exists(): raise ValueError('fresh separate comparison output required')
    a = read(args.audit_one)
    origin = {'run': str(args.origin_run.resolve()), 'source': str(args.origin_source.resolve()),
        'source_commit': a['source_commit'], 'audit_files': {
            str(v.resolve()): file_sha256(v) for v in (args.audit_one, args.audit_two)}}
    original, audit = base.origin_evidence(origin)
    from utopia.optimization.native_scientist_transport_v1 import contract as transport_contract
    p = build_plan(original, audit, source=source, origin=origin,
        backend=backend_binding(original['designer']), observer_backend=backend_binding(original['scientist']),
        prerequisite=base.prerequisite_binding(args.after_numeric_dispatch),
        declaration=source_scope(ROOT, source_commit=source), component_bank=read(args.component_bank),
        component_evidence={'run': str(args.component_run.resolve()), 'source': str(args.component_source.resolve()),
            'audit': str(args.component_audit.resolve()), 'audit_file_sha256': file_sha256(args.component_audit)},
        scientist_transport=transport_contract(read_seconds=900))
    args.output.mkdir(parents=True); save(args.output/'plan.json', p); require_plan(args.output)
    print(json.dumps({'source': source, 'native_worlds_upper_bound': 14, 'new_model_POSTs': 0}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('prepare')
    for name in ('origin-run', 'origin-source', 'audit-one', 'audit-two', 'after-numeric-dispatch',
            'component-bank', 'component-run', 'component-source', 'component-audit', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    p = sub.add_parser('run'); p.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'prepare': prepare(args)
    else: run(args.output)


if __name__ == '__main__': main()
