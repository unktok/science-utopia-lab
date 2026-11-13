"""Finite structural workflow design in the original native scientist world."""
import argparse
import fcntl
import json
import os
from pathlib import Path

from scripts.run_native_objective_instrument_loop_v1 import factory_for, measure_with, progress, utc
from scripts.run_native_planning_fixed_evaluation_v1 import origin_evidence
from scripts.run_native_parameter_comparator_v1 import AUTHOR_ONLY_DIFFERENCES
from scripts.run_pre_scale_search_v1 import require_environment, ENVIRONMENT
from utopia.optimization.blackbox import Suggestion
from utopia.optimization.common_content_observer import CommonContentObserver, LocalObserverBackend, make_contract
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign
from utopia.optimization.native_development_references import build_context
from utopia.optimization.native_designer_preflight import backend_binding, runtime_binding
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.optimization.native_workflow_designer_v1 import WorkflowDesigner, SETTINGS, generation_definition
from utopia.optimization.native_workflow_domain_v4 import (
    workflow_design_space, post_funding_cost_control, verify_workflow_interval)
from utopia.optimization.native_world import evaluate_native_suggestion
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = 'scienceutopia.native-workflow-objective-loop.v1'
PROTOCOL = 'research/protocols/campaigns/native-workflow-objective-loop-v1.md'
SEED = 61001


def read(path): return checked(json.loads(Path(path).read_text()))


def native_sources(source):
    import hashlib
    import io
    import subprocess
    exclusions = (*AUTHOR_ONLY_DIFFERENCES, 'utopia/optimization/native_design_space.py')
    names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', source, '--', 'utopia'],
        cwd=ROOT, text=True).splitlines()
    names += ['scripts/run_native_objective_instrument_loop_v1.py',
        'scripts/native_benchmark_physical.py', 'scripts/native_observer_physical_v1.py']
    names = [n for n in sorted(set(names)) if n.endswith('.py') and n not in exclusions]
    # Read the same immutable Git blobs in one subprocess. Recheck actual local
    # bytes on every call; do not cache a prior clean-source verdict.
    batch = subprocess.run(['git', 'cat-file', '--batch'], cwd=ROOT,
        input=''.join(source + ':' + n + '\n' for n in names).encode(),
        stdout=subprocess.PIPE, check=True).stdout
    stream = io.BytesIO(batch); files = {}
    for name in names:
        header = stream.readline().split()
        if len(header) != 3 or header[1] != b'blob':
            raise ValueError('original source Git blob is missing or not a file: ' + name)
        size = int(header[2]); raw = stream.read(size)
        if len(raw) != size or stream.read(1) != b'\n':
            raise ValueError('original source Git batch framing differs')
        path = ROOT / name
        if path.is_symlink() or not path.is_file() or path.read_bytes() != raw:
            raise ValueError('original scientist/effect source differs: ' + name)
        files[name] = hashlib.sha256(raw).hexdigest()
    if stream.read(): raise ValueError('unconsumed original source Git batch bytes')
    return {'original_source': source, 'literal_files': files, 'author_domain_only_exclusions': list(exclusions),
        'exclusion_role': 'designer context/transport or explicit design-domain guard, not native science',
        'global_semantic_equivalence_claimed': False}


def prerequisite_binding(directory):
    directory = Path(directory).resolve(); start = read(directory / 'started.json')
    if start['schema'] != 'scienceutopia.native-parameter-comparator-chain.v1':
        raise ValueError('explicit original numeric continuation required')
    return {'directory': str(directory), 'started_file_sha256': file_sha256(directory / 'started.json'),
        'pid': start['pid'], 'numeric_source_commit': start['numeric_source_commit']}


def require_prerequisite(binding):
    from scripts.finish_native_institution_loop_v1 import same_files
    from scripts.run_pre_scale_completion_chain_v1 import process_identity
    root = Path(binding['directory'])
    if prerequisite_binding(root) != binding:
        raise ValueError('frozen prerequisite binding differs')
    end = read(root / 'ended.json')
    if (end['status'] != 'closed' or len(end['steps']) != 7 or any(s['exit_code'] for s in end['steps'])
            or process_identity(binding['pid']) is not None):
        raise ValueError('numeric continuation is not normally closed and absent; no workflow inference')
    audits = [read(root / ('audit-' + str(i) + '.json')) for i in (1, 2)]
    if (audits[0] != audits[1] or audits[0]['schema'] != 'scienceutopia.native-parameter-comparator-audit.v1'
            or audits[0]['source_commit'] != binding['numeric_source_commit']
            or audits[0]['source_proof']['status'] != 'verified-exact-source-closure'
            or audits[0]['closure']['terminal']['status'] != 'closed'
            or (root / 'costs-1.json').read_bytes() != (root / 'costs-2.json').read_bytes()
            or same_files(root / 'report-1', root / 'report-2') != end['report_files']):
        raise ValueError('original numeric double audit/cost/report closure differs')
    return {'ended_file_sha256': file_sha256(root / 'ended.json'),
        'audit_content_sha256': audits[0]['content_sha256']}


def build_plan(original, audit, *, source, origin, backend, observer_backend, prerequisite, sources):
    if (original['schema'] != 'scienceutopia.native-planning-objective-loop.v1.plan'
            or audit['schema'] != 'scienceutopia.native-planning-objective-loop-audit.v1'
            or audit['source_commit'] != original['source_commit'] or sources['original_source'] != original['source_commit']
            or original['objectives'] != ['throughput', 'content-utility'] or original['held_out_evaluation']):
        raise ValueError('normally closed original planning world/template required')
    anchor = SystemSpec.from_dict(original['reference_systems']['assignment-reserve21-no-review-all'])
    refs = {'R7-original': anchor.to_dict(), 'post-funding-cost': post_funding_cost_control(anchor).to_dict()}
    observer = make_contract(source_commit=source, provider={k: original['scientist'][k] for k in ('model', 'model_digest')},
        backend=observer_backend, maximum_posts=1500, critics=3)
    for key in original['observer_contract']:
        if key not in ('source_commit', 'content_sha256') and original['observer_contract'][key] != observer[key]:
            raise ValueError('original common content observer changed')
    experiment = {'protocol': PROTOCOL, 'role': 'objective-conditioned-native-workflow-design'}
    world = {**clone(original['world']), 'source_commit': source, 'experiment': experiment,
        'measurement_adapter_contract': observer, 'classification': 'actual-native-workflow-objective-loop-v1'}
    return {'schema': SCHEMA + '.plan', 'source_commit': source, 'runtime': runtime_binding(),
        'protocol': PROTOCOL, 'protocol_sha256': file_sha256(ROOT / PROTOCOL), 'origin': clone(origin),
        'origin_audit_content_sha256': audit['content_sha256'], 'original_native_sources': sources,
        'prerequisite': clone(prerequisite), 'launch_environment': clone(ENVIRONMENT),
        **{k: clone(original[k]) for k in ('scientist', 'designer', 'data_cache', 'losses', 'catalog')},
        'backend': clone(backend), 'world': world, 'experiment': experiment, 'observer_contract': observer,
        'initial_system': anchor.to_dict(), 'design_space': workflow_design_space(anchor),
        'authoring_scope': 'literal-existing-institutions-workflow-only', 'author_settings': clone(SETTINGS),
        'reference_order': list(refs), 'reference_systems': refs,
        'objectives': clone(original['objectives']), 'generations': 3, 'optimizer_seed': 68011,
        'strategies': {'local-workflow-designer': {'protocol': PROTOCOL, 'method': 'literal-local-workflow-submission'}},
        'schedule': [{'objective': o, 'generation': g} for g in range(3)
            for o in (original['objectives'] if g % 2 == 0 else original['objectives'][::-1])],
        'budget': {'fresh_reference_worlds': 2, 'candidate_slots': 6, 'native_worlds_upper_bound': 8,
            'scientist_HTTP_attempts_per_world': 1024, 'world_wall_seconds': 7200,
            'observer_POSTs_upper_bound': 1500, 'designer_POSTs_upper_bound': 13,
            'readiness_sessions': 7, 'proposal_POSTs_per_session': 1, 'replace_failed_slots': False},
        'held_out_evaluation': False, 'independent_optimizer_replications': False,
        'structural_freedom_causal_effect_claimed': False, 'publication_ready': False}


def require_plan(root):
    p = read(root / 'plan.json')
    if p['source_commit'] != pinned_revision(ROOT) or p['runtime'] != runtime_binding():
        raise ValueError('exact clean workflow study source/runtime required')
    original, audit = origin_evidence(p['origin'])
    if prerequisite_binding(p['prerequisite']['directory']) != p['prerequisite']:
        raise ValueError('workflow prerequisite changed')
    expected = build_plan(original, audit, source=p['source_commit'], origin=p['origin'], backend=p['backend'],
        observer_backend=p['observer_contract']['backend'], prerequisite=p['prerequisite'],
        sources=native_sources(original['source_commit']))
    if expected != {k: v for k, v in p.items() if k != 'content_sha256'}:
        raise ValueError('literal workflow plan reconstruction differs')
    return p


def campaign(root, p, objective, context=None, *, prototype=False):
    path = root / 'initial-readiness/campaign' if prototype else root / 'search' / objective / 'campaign'
    return NativeAdaptiveDesignCampaign(path, initial_system=SystemSpec.from_dict(p['initial_system']),
        loss_spec=p['losses'][objective], seeds=[SEED], world_binding=p['world'], strategies=p['strategies'],
        mode='blackbox', seed=p['optimizer_seed'], design_space=p['design_space'],
        **({} if context is None else {'development_references': context}))


def measurement(p, observer):
    anchor = SystemSpec.from_dict(p['initial_system']); measure = measure_with(observer, p['observer_contract'])
    def apply(sim, base):
        interval = verify_workflow_interval(anchor, sim.native_system.spec, sim.native_system.events, years=4)
        return {**measure(sim, base), 'native_workflow_interval': interval}
    return apply


def selection(root, p, context):
    selected = {}
    for objective in p['objectives']:
        c = campaign(root, p, objective, context)
        if c.state['pending'] is not None or len(c.state['records']) != 3:
            raise ValueError('six terminal own workflow slots required')
        pool = [o for r in c.state['records'] for o in r['observations'] if o and o['status'] == 'complete']
        best = min((o['loss'] for o in pool), default=None)
        ties = [o for o in pool if o['loss'] == best]
        selected[objective] = {'loss': best, 'all_tied_ids': [o['suggestion_id'] for o in ties],
            'selected_id': ties[0]['suggestion_id'] if ties else None,
            'system': clone(ties[0]['candidate']) if ties else None}
    return {'schema': SCHEMA + '.selection', 'plan_sha256': p['content_sha256'],
        'selected': selected, 'baseline_fallback': False, 'held_out_evaluation': False}


def run(root):
    require_environment(); p = require_plan(root)
    require_prerequisite(p['prerequisite'])
    with (root / 'writer.lock').open('a') as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        if (root / 'started.json').exists(): raise ValueError('consumed workflow study; no redispatch')
        save(root / 'started.json', {'schema': SCHEMA + '.start', 'plan_sha256': p['content_sha256'],
            'pid': os.getpid(), 'started_utc': utc()})
        stage, consumed, observations, status = 'initial-readiness', 0, 0, 'stopped'
        try:
            author = WorkflowDesigner(root / 'initial-readiness/author', provider=p['designer'],
                backend=p['backend'], inference_lock=root / 'inference.lock')
            c = campaign(root, p, p['objectives'][0], prototype=True)
            author.calibrate(c._request([], c._validate(), 1)); require_plan(root)
            observer = CommonContentObserver(root / 'observer', p['observer_contract'],
                backend=LocalObserverBackend(inference_lock=root / 'inference.lock'))
            pairs = []
            for label in p['reference_order']:
                stage = 'references'; progress(root, stage, label)
                directory = root / 'references' / label
                s = Suggestion('workflow-reference-' + label.lower(), p['reference_systems'][label], 0, 'developer-reference')
                save(directory / 'started.json', {'suggestion': s.to_dict(), 'seed': SEED, 'started_utc': utc()})
                o = evaluate_native_suggestion(s, seeds=[SEED], simulation_factory=factory_for(directory / 'worlds', p, root),
                    loss_spec=p['losses']['throughput'], measurement_adapter=measurement(p, observer)).to_dict()
                save(directory / 'observation.json', o)
                save(directory / 'cross-scores.json', {k: evaluate_loss(v, o['metadata']['measurements']) for k, v in p['losses'].items()})
                if o['status'] != 'complete': raise ValueError('workflow reference failed; no refill')
                pairs.append({'suggestion': s.to_dict(), 'observation': o}); observations += 1; require_plan(root)
            context = build_context(pairs, world=p['world'], seeds=[SEED], loss_spec=p['losses']['throughput'])
            save(root / 'developer-reference-context.json', {k: v for k, v in context.items() if k != 'content_sha256'})
            for slot in p['schedule']:
                objective, generation = slot['objective'], slot['generation']
                c = campaign(root, p, objective, context)
                if c.state['pending'] is not None or len(c.state['records']) != generation:
                    raise ValueError('consumed/pending workflow generation; no redispatch')
                request = c._request(c.state['records'], c._validate(), 1)
                directory = root / 'search' / objective
                author = WorkflowDesigner(directory / 'authoring', provider=p['designer'], backend=p['backend'],
                    inference_lock=root / 'inference.lock')
                stage = 'readiness'; progress(root, stage, objective + ':g' + str(generation))
                certificate = author.calibrate(request); require_plan(root)
                def generate(req):
                    if req != request: raise ValueError('actual workflow generation request differs from calibration')
                    return generation_definition(author.execute(req, purpose='proposal', certificate=certificate))
                stage = 'optimization'; progress(root, stage, objective + ':g' + str(generation))
                record = c.advance(simulation_factory=factory_for(directory / 'worlds', p, root),
                    generators={'local-workflow-designer': generate}, count=1, measurement_adapter=measurement(p, observer),
                    measurement_contract=p['observer_contract'])
                consumed += 1; observations += sum(o is not None for o in record['observations']); require_plan(root)
            save(root / 'selection.json', selection(root, p, context))
            save(root / 'observer-audit.json', observer.audit()); status = stage = 'closed'; progress(root, stage, None)
        except BaseException as error:
            save(root / 'terminal.json', {'schema': SCHEMA + '.terminal', 'status': status, 'stage': stage,
                'consumed_slots': consumed, 'observations': observations, 'ended_utc': utc(),
                'error_type': type(error).__name__, 'error': str(error), 'no_retry': True})
            raise
        save(root / 'terminal.json', {'schema': SCHEMA + '.terminal', 'status': status, 'stage': stage,
            'consumed_slots': consumed, 'observations': observations, 'ended_utc': utc(), 'no_retry': True})


def prepare(args):
    require_environment(); source = pinned_revision(ROOT)
    if args.output.exists(): raise ValueError('fresh workflow output required')
    original_audit = read(args.audit_one)
    origin = {'run': str(args.origin_run.resolve()), 'source': str(args.origin_source.resolve()),
        'source_commit': original_audit['source_commit'],
        'audit_files': {str(v.resolve()): file_sha256(v) for v in (args.audit_one, args.audit_two)}}
    original, audit = origin_evidence(origin)
    p = build_plan(original, audit, source=source, origin=origin, backend=backend_binding(original['designer']),
        observer_backend=backend_binding(original['scientist']), prerequisite=prerequisite_binding(args.after_numeric_chain),
        sources=native_sources(original['source_commit']))
    args.output.mkdir(parents=True); save(args.output / 'plan.json', p); require_plan(args.output)
    print(json.dumps({'prepared_source': source, 'native_worlds_upper_bound': 8, 'new_model_POSTs': 0}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest='command', required=True)
    p = sub.add_parser('prepare')
    for name in ('origin-run', 'origin-source', 'audit-one', 'audit-two', 'after-numeric-chain'):
        p.add_argument('--' + name, type=Path, required=True)
    p.add_argument('--output', type=Path, required=True)
    p = sub.add_parser('run'); p.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.command == 'prepare': prepare(args)
    else: run(args.output)


if __name__ == '__main__': main()
