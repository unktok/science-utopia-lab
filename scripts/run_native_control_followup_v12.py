#!/usr/bin/env python3
"""Two forward-only native draws from the audited final v11 CV proposal.

This is a new experiment, never an append to v11. No optimizer update, source
invention, causal comparison or variance-reduction inference is performed.
"""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.analyze_native_open_v7 import _inventory
from scripts.run_native_open_estimators_v11 import load_preregistered_loss
from utopia.optimization.blackbox import Observation, Suggestion
from utopia.optimization.loss import evaluate_loss, loss_spec_sha256
from utopia.optimization.native_adaptive_search import GeneratedMixedDesign, expectation_compatibility
from utopia.optimization.native_discrete_policy import verify_native_observation
from utopia.optimization.native_world import evaluate_native_suggestion
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import file_sha256, write_json_atomic

SCHEMA = 'scienceutopia.native-control-followup.v12'
ACTUAL = 'actual-native-qwen-final-v11-control-followup-v12'
EXPERIMENT = {'protocol': 'native-control-followup-v12', 'role': 'development-engineering'}
PARENT_SOURCE = 'acf3a2e4b995f8a04f4b0b56011a7051fe73a112'
PARENT_AUDIT_SHA256 = '98bc7c3e4b2aa32fcedbe1f413c7311a2a71e5034824bb427f21eef8ea5f677d'
PARENT_CONTENT_SHA256 = '0d75a366dc32b8f75dab96ca32d7daa90a91c6e98db140df28bbbc21d6547426'
FINAL_WEIGHTS = {'continuous_mean': [-0.1150163404137367],
    'logits': {'review-aggregation': [-0.06055868973308312, 0.06055868973308312]}}
WORLD_SEED, DRAW_SEED, DRAWS = 42, 43, 2
OPTIMIZER_EXTENSION_SOURCE = '16f4d606bfa30231c1ae818a6700220511f29b04'
OPTIMIZER_EXTENSION_SHA256 = '8cd0d96f60e90b1e8d1395d641cc602e4e5040116bd5eb1900b49399e7c57b69'
OPTIMIZER_FILE = 'utopia/optimization/native_adaptive_search.py'


def compatible_source_proof(root=ROOT, *, allow_optimizer_extension=True):
    """Only the separately reviewed opt-in singleton optimizer extension differs.

    It adds an opt-in black-box one-draw path, unused here. Every actual forward
    runtime and all other optimizer blobs remain exactly the v11 bytes. Unknown
    optimizer modifications are rejected, not assumed semantically compatible.
    """
    root = Path(root)
    names = subprocess.check_output(['git', 'ls-tree', '-r', '--name-only', PARENT_SOURCE,
        '--', 'utopia'], cwd=root, text=True).splitlines()
    current_names = subprocess.check_output(['git', 'ls-files', '--', 'utopia'],
        cwd=root, text=True).splitlines()
    if not names or names != current_names:
        raise ValueError('followup native runtime file set differs from frozen v11')
    proofs, exceptions = {}, {}
    for name in names:
        pinned = subprocess.check_output(['git', 'show', f'{PARENT_SOURCE}:{name}'], cwd=root)
        sha = hashlib.sha256(pinned).hexdigest()
        current = file_sha256(root / name)
        if current != sha:
            if not (allow_optimizer_extension and name == OPTIMIZER_FILE and current == OPTIMIZER_EXTENSION_SHA256):
                raise ValueError(f'followup native runtime source differs from frozen v11: {name}')
            exceptions[name] = {'parent_sha256': sha, 'current_sha256': current,
                'reviewed_extension_commit': OPTIMIZER_EXTENSION_SOURCE,
                'scope': 'opt-in singleton black-box path, unused in this two-draw no-update followup'}
        proofs[name] = current
    return {'status': 'native-forward-identical-explicit-optimizer-extension' if exceptions else
        'all-native-runtime-blobs-identical', 'parent_source_commit': PARENT_SOURCE,
        'files': proofs, 'files_sha256': digest(proofs), 'reviewed_exceptions': exceptions}


def reaudit_parent(parent_run, audit_source):
    """Execute only the original read-only auditor from clean old source.

    A subprocess avoids importing the extended optimizer into old replay math.
    JSON roundtrip normalizes integer object keys exactly as the archived file.
    """
    audit_source = Path(audit_source).resolve()
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=audit_source):
        raise ValueError('parent re-audit requires clean old source worktree')
    source_commit = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=audit_source, text=True).strip()
    source_proof = compatible_source_proof(audit_source, allow_optimizer_extension=False)
    program = ('import json,sys; sys.path.insert(0,sys.argv[1]); '
        'from scripts.analyze_native_open_estimators_v11 import analyze; '
        'print(json.dumps(analyze(sys.argv[2],expected_source=sys.argv[3]),sort_keys=True,allow_nan=False))')
    encoded = subprocess.check_output([sys.executable, '-B', '-c', program, str(audit_source),
        str(parent_run), PARENT_SOURCE], cwd=audit_source, text=True)
    if (subprocess.check_output(['git', 'status', '--porcelain'], cwd=audit_source) or
            subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=audit_source, text=True).strip() != source_commit or
            compatible_source_proof(audit_source, allow_optimizer_extension=False) != source_proof):
        raise ValueError('old audit source changed during read-only parent replay')
    result = json.loads(encoded)
    proof = {'root': str(audit_source), 'source_commit': source_commit,
        'native_runtime': source_proof, 'new_model_calls': 0, 'new_container_executions': 0}
    return result, proof


def guard_parent(parent_run, parent_audit, receipt):
    """Read-only guard; also invoked around every new forward and on resume."""
    if (file_sha256(parent_audit) != receipt['audit_file_sha256'] or
            _inventory(parent_run) != receipt['raw_input_sha256s']):
        raise ValueError('immutable parent audit/raw evidence changed')


def load_parent(parent_run, parent_audit, audit_source):
    parent_run, parent_audit = Path(parent_run).resolve(), Path(parent_audit).resolve()
    if file_sha256(parent_audit) != PARENT_AUDIT_SHA256:
        raise ValueError('pinned independently audited v11 file SHA differs')
    report = json.loads(parent_audit.read_text())
    if (report.get('content_sha256') != PARENT_CONTENT_SHA256 or
            digest({k: v for k, v in report.items() if k != 'content_sha256'}) != PARENT_CONTENT_SHA256 or
            report.get('source_commit') != PARENT_SOURCE or report.get('status') != 'complete' or
            report.get('physical_native_worlds') != 8 or report.get('physical_researcher_responses') != 742 or
            report.get('classification') != 'actual-native-qwen-open-estimators-development-v11'):
        raise ValueError('parent must be the exact completed actual v11 independent audit')
    if Path(report['audit']['raw_root']).resolve() != parent_run:
        raise ValueError('parent raw path differs from pinned independent audit')
    receipt = {'source_commit': PARENT_SOURCE, 'audit_file_sha256': PARENT_AUDIT_SHA256,
        'audit_content_sha256': PARENT_CONTENT_SHA256, 'raw_root': str(parent_run),
        'raw_input_sha256s': clone(report['audit']['raw_input_sha256s']),
        'raw_inventory_sha256': report['audit']['raw_inventory_sha256']}
    guard_parent(parent_run, parent_audit, receipt)
    repeated, audit_source_proof = reaudit_parent(parent_run, audit_source)
    if repeated != report:
        raise ValueError('read-only parent source/native/update re-audit differs from pinned report')
    final = report['arms']['score-control-variate']['records'][-1]
    mixed_report = final['report']['mixed']
    if (final['request']['generation'] != 1 or final['generation_error'] is not None or
            mixed_report['status'] != 'score-updated' or
            mixed_report['expectation_estimator']['estimator'] != 'frozen-prior-control-variate-lr' or
            mixed_report['weights_after'] != FINAL_WEIGHTS):
        raise ValueError('parent final update is not the preregistered corrected-control proposal')
    definition = clone(final['definition'])
    definition['logits'] = clone(mixed_report['weights_after']['logits'])
    for coordinate, mean in zip(definition['continuous'], mixed_report['weights_after']['continuous_mean']):
        coordinate['mean'] = mean
    parent = SystemSpec.from_dict(final['request']['parent_system'])
    mixed = GeneratedMixedDesign(parent, definition, loss_spec=report['loss_spec'], seed=DRAW_SEED)
    compatibility = expectation_compatibility(mixed)
    if (mixed.weights() != FINAL_WEIGHTS or
            compatibility != mixed_report['expectation_estimator']['compatibility_sha256']):
        raise ValueError('final proposal changed source, ports, wires, factors or coordinate meaning')
    receipt.update(final_request_sha256=final['request_sha256'],
        final_version_sha256=final['version_sha256'], final_weights=clone(FINAL_WEIGHTS),
        final_update=clone(mixed_report), compatibility_sha256=compatibility,
        parent_system_fingerprint=parent.fingerprint, source_runtime=compatible_source_proof(),
        reaudit_source=audit_source_proof)
    guard_parent(parent_run, parent_audit, receipt)
    return receipt, parent, definition, clone(report['loss_spec'])


def make_plan(receipt, parent, definition, loss, world):
    if world['classification'] == ACTUAL:
        parent_world = json.loads((Path(receipt['raw_root']) / 'plan.json').read_text())['world']
        for key in ('model_digest', 'corpus_sha256', 'years', 'corpus_years', 'image_id', 'runtime_seed_binding'):
            if world[key] != parent_world[key]:
                raise ValueError(f'followup actual world differs from parent: {key}')
    return {'schema': SCHEMA, 'classification': world['classification'], 'world': clone(world),
        'experiment': clone(EXPERIMENT), 'parent': clone(receipt), 'parent_system': parent.to_dict(),
        'definition': clone(definition), 'loss_spec': clone(loss), 'world_seed': WORLD_SEED,
        'draw_seed': DRAW_SEED, 'planned_native_world_budget': DRAWS,
        'population': {'authors': 5, 'conference_setting': 1}, 'optimizer_update': False,
        'new_source_or_topology_invention': False, 'causal_comparison': False,
        'scope': 'new forward-only sampling from final saved v11 conditional proposal; no expected-loss, variance-reduction or improvement inference from two outcomes'}


def compile_draws(plan):
    mixed = GeneratedMixedDesign(SystemSpec.from_dict(plan['parent_system']), plan['definition'],
        loss_spec=plan['loss_spec'], seed=plan['draw_seed'])
    if expectation_compatibility(mixed) != plan['parent']['compatibility_sha256']:
        raise ValueError('followup source/ports/wires/coordinate compatibility changed')
    version = digest({'schema': SCHEMA, 'parent': plan['parent']['audit_content_sha256'],
        'weights': mixed.weights(), 'draw_seed': plan['draw_seed'], 'definition': mixed.definition_sha256})
    return mixed.draw(DRAWS, version_sha256=version, proposal_start=4), version


def valid_observation(value):
    return value is not None and value['status'] == 'complete' and not value['metadata'].get('technical_failures')


def check_observation(value, draw, plan):
    if draw['suggestion'] is None:
        if value is not None:
            raise ValueError('invalid draw cannot receive an observation or numeric loss')
        return
    if value is None:
        raise ValueError('valid draw cannot be silently skipped')
    observation = Observation.from_dict(value)
    evaluation = evaluate_loss(plan['loss_spec'], observation.metadata.get('measurements', []))
    if (observation.suggestion_id != draw['suggestion']['suggestion_id'] or
            observation.candidate != draw['suggestion']['candidate'] or
            observation.metadata.get('world_backend') != 'native-research-world' or
            observation.metadata.get('loss_spec_sha256') != loss_spec_sha256(plan['loss_spec']) or
            observation.metadata.get('loss_evaluation') != evaluation or
            observation.loss != (evaluation['loss'] if evaluation['status'] == 'complete' else None) or
            (observation.status == 'complete') != (evaluation['status'] == 'complete')):
        raise ValueError('followup saved native observation/loss/design differs')
    verify_native_observation(observation, plan['world'], [WORLD_SEED])


def advance(output, plan, *, simulation_factory, parent_guard):
    """Persist a batch before execution and each native outcome before next draw."""
    parent_guard()
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    draws, version = compile_draws(plan)
    plan_path, state_path = output / 'plan.json', output / 'state.json'
    if plan_path.exists() and json.loads(plan_path.read_text()) != plan:
        raise ValueError('immutable v12 followup plan changed')
    if not plan_path.exists():
        write_json_atomic(plan_path, plan, sort_keys=True, allow_nan=False)
    initial = {'schema': SCHEMA, 'plan_sha256': digest(plan), 'version_sha256': version,
        'draws': draws, 'observations': []}
    state = json.loads(state_path.read_text()) if state_path.exists() else initial
    if ({k: v for k, v in state.items() if k != 'observations'} !=
            {k: v for k, v in initial.items() if k != 'observations'} or
            not isinstance(state['observations'], list) or len(state['observations']) > DRAWS):
        raise ValueError('followup immutable batch, likelihoods, draws or source changed')
    for index, observation in enumerate(state['observations']):
        check_observation(observation, draws[index], plan)
        if not valid_observation(observation) and index != len(state['observations']) - 1:
            raise ValueError('followup continued after a technical failure')
    parent_guard()
    write_json_atomic(state_path, state, sort_keys=True, allow_nan=False)
    if state['observations'] and not valid_observation(state['observations'][-1]):
        return state
    for draw in draws[len(state['observations']):]:
        parent_guard()
        observation = (evaluate_native_suggestion(Suggestion.from_dict(draw['suggestion']),
            loss_spec=plan['loss_spec'], seeds=[WORLD_SEED], simulation_factory=simulation_factory).to_dict()
            if draw['suggestion'] is not None else None)
        parent_guard()
        check_observation(observation, draw, plan)
        state['observations'].append(observation)
        write_json_atomic(state_path, state, sort_keys=True, allow_nan=False)
        if not valid_observation(observation):
            break
    parent_guard()
    return state


def summarize(output, plan):
    output = Path(output)
    state = json.loads((output / 'state.json').read_text()) if (output / 'state.json').exists() else None
    observations = state['observations'] if state else []
    complete = sum(valid_observation(o) for o in observations)
    stopped = bool(observations and not valid_observation(observations[-1]))
    caches = []
    for path in sorted((output / 'worlds').glob('*/replies/responses.sqlite')):
        with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as db:
            counts = dict(db.execute('SELECT outcome,COUNT(*) FROM replies GROUP BY outcome').fetchall())
        caches.append({'path': str(path.resolve()), 'sha256': file_sha256(path), 'outcomes': counts})
    replies = sum(c['outcomes'].get('response', 0) for c in caches)
    value = {'schema': SCHEMA, 'classification': plan['classification'], 'plan': plan,
        'source_commit': plan['world']['source_commit'],
        'status': 'technically-stopped' if stopped else 'complete' if complete == DRAWS else 'in-progress',
        'planned_native_world_budget': DRAWS, 'committed_draws': len(observations),
        'complete_native_worlds': complete, 'technical_failures': int(stopped),
        'physical_reply_count': replies, 'physical_response_caches': caches, 'state': state,
        'claims': {'post_final_cv_proposal_native_evaluated': complete > 0,
            'live_fixed_Qwen_researchers': plan['classification'] == ACTUAL and replies > 0,
            'held_out': False, 'gradient_update_after_followup': False,
            'causal_institutional_benefit': False, 'variance_reduction_established': False,
            'designer_improvement_established': False, 'full_native_world_pathwise_autograd': False}}
    value['content_sha256'] = digest(value)
    write_json_atomic(output / 'evidence.json', value, sort_keys=True, allow_nan=False)
    return value


def run(args):
    receipt, parent, definition, loss = load_parent(args.parent_run, args.parent_audit, args.parent_audit_source)
    if load_preregistered_loss(ROOT / 'research/objectives/losses/native-joint-v5-net-reviewed-utility.json') != loss:
        raise ValueError('followup loss differs from exact parent native utility loss')
    from utopia.optimization.native_factory import LocalQwenNativeFactory
    factory = LocalQwenNativeFactory(args.output / 'worlds', args.data_cache, years=2, corpus_years=4,
        experiment_binding=EXPERIMENT, record_wire=True, record_code=True, inference_lock=args.inference_lock)
    parent_world = json.loads((args.parent_run / 'plan.json').read_text())['world']
    world = {'source_commit': factory.source_commit, 'model_digest': factory.model_digest,
        'corpus_sha256': factory.corpus_sha256, 'years': 2, 'corpus_years': 4,
        'runtime_seed_binding': factory.runtime_seed_binding, 'experiment': EXPERIMENT,
        'image_id': parent_world['image_id'], 'classification': ACTUAL}
    plan = make_plan(receipt, parent, definition, loss, world)
    guard = lambda: guard_parent(args.parent_run, args.parent_audit, receipt)
    try:
        advance(args.output, plan, simulation_factory=factory, parent_guard=guard)
    finally:
        guard()
        evidence = summarize(args.output, plan)
    print(json.dumps({k: evidence[k] for k in ('status', 'complete_native_worlds',
        'physical_reply_count', 'content_sha256')}), flush=True)
    return 0 if evidence['status'] == 'complete' else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('parent-run', 'parent-audit', 'parent-audit-source', 'output', 'data-cache', 'inference-lock'):
        parser.add_argument('--' + name, type=Path, required=True)
    args = parser.parse_args()
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT):
        parser.error('experiments require a clean pinned source worktree')
    for key, value in vars(args).items():
        setattr(args, key, value.resolve())
    # Reject output overlap BEFORE mkdir/lock/factory: v11 remains truly read-only.
    if (args.output == args.parent_run or args.parent_run in args.output.parents or
            args.output in args.parent_run.parents or args.output == args.parent_audit or
            args.output in args.parent_audit.parents or args.output == args.parent_audit_source or
            args.parent_audit_source in args.output.parents or args.output in args.parent_audit_source.parents):
        parser.error('new followup output must not overlap immutable parent raw/audit')
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / 'followup-writer.lock').open('a') as owner:
        try:
            fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('another v12 followup writer owns this output')
        return run(args)


if __name__ == '__main__':
    raise SystemExit(main())
