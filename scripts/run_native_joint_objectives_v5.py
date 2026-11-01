#!/usr/bin/env python3
"""Small, resumable objective-conditioned joint institutional-code/graph loop.

One physical native baseline, two or more explicit logical losses. Every later
eligible authored system is freshly executed in the original researcher world.
Technical authoring failures are terminal null-score receipts, never penalties
or invitations to silently extend the declared drafting budget.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--data-cache', type=Path, required=True)
    parser.add_argument('--loss', type=Path, action='append', required=True)
    parser.add_argument('--inference-lock', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=1301)
    parser.add_argument('--years', type=int, default=2)
    parser.add_argument('--corpus-years', type=int, default=4)
    parser.add_argument('--budget', type=int, default=3, help='initial plus adaptive candidates per loss')
    parser.add_argument('--max-technical-drafts', type=int, default=3)
    parser.add_argument('--max-tokens', type=int, default=4096)
    parser.add_argument('--authoring-format', choices=['scoped-v5', 'boundary-v5a2', 'staged-v5'], default='scoped-v5')
    parser.add_argument('--designer-thinking', action='store_true',
        help='explicit designer-only reasoning; native researchers remain unchanged')
    args = parser.parse_args()
    if not 2 <= len(args.loss) <= 4 or not 2 <= args.budget <= 4:
        parser.error('bounded pilot requires 2..4 losses and 2..4 systems per loss')
    if not 1 <= args.max_technical_drafts <= 5 or not 512 <= args.max_tokens <= 8192:
        parser.error('invalid explicit authoring budget')
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT):
        parser.error('native experiments require a clean pinned source worktree')
    from utopia.optimization.loss import load_loss_spec, loss_spec_sha256
    from utopia.optimization.native_design import NativeDesignCampaign
    from utopia.optimization.native_factory import LocalQwenNativeFactory, serialize_native_http
    from utopia.optimization.native_code_trace import parent_context_provider
    from utopia.optimization.native_region_proposer_v5 import NativeRegionIRProposer
    from utopia.optimization.native_shared_initial import adopt_shared_initial
    from utopia.system.code_mechanisms import DockerCodeExecutor, sha
    from utopia.system.native_kernel import legacy_world_system
    from utopia.system.native_selection_slot import selection_source_slot
    from utopia.models.models import VLLMServerModel
    from utopia.models.response_cache import CompletedResponseCache
    from utopia.utils.data_utils import write_json_atomic
    from scripts.audit_native_objective_v5 import checkpoint_measurements

    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    losses = [load_loss_spec(path) for path in args.loss]
    arm_ids = [re.sub(r'[^a-zA-Z0-9_-]', '-', loss['id']) for loss in losses]
    if len(set(arm_ids)) != len(arm_ids) or len({loss_spec_sha256(l) for l in losses}) != len(losses):
        parser.error('distinct losses and distinct safe arm IDs required')
    protocol = {'schema': 'scienceutopia.native-joint-objectives.v5',
        'losses': losses, 'arm_ids': arm_ids, 'seed': args.seed, 'years': args.years,
        'corpus_years': args.corpus_years, 'budget_per_arm': args.budget,
        'max_technical_drafts': args.max_technical_drafts, 'max_tokens': args.max_tokens,
        'shared_initial': 'one-physical-trajectory-not-independent-replications',
        'population': 'five-independent-balanced-researchers',
        'designer': 'Qwen3:8b-scoped-free-Python-and-explicit-graph-v5',
        'no_hidden_merit_or_promotion_veto': True}
    if args.authoring_format != 'scoped-v5':
        protocol.update(authoring_format=args.authoring_format,
            designer='Qwen3:8b-alias-aligned-free-Python-and-explicit-graph-v5a2')
    if args.authoring_format == 'staged-v5':
        protocol.update(designer='Qwen3:8b-staged-graph-then-free-source-v5',
            plan_technical_drafts=args.max_technical_drafts,
            source_technical_drafts=args.max_technical_drafts)
    if args.designer_thinking:
        protocol['designer_thinking'] = True
    factory = LocalQwenNativeFactory(args.output / 'runs', args.data_cache,
        years=args.years, corpus_years=args.corpus_years,
        experiment_binding=protocol, record_wire=True, record_code=True,
        inference_lock=args.inference_lock)
    executor = DockerCodeExecutor()
    initial = selection_source_slot(legacy_world_system(seed=args.seed), image_id=executor.image_id)
    world = {'source_commit': factory.source_commit, 'model': factory.model,
        'model_digest': factory.model_digest, 'corpus_sha256': factory.corpus_sha256,
        'dataset_identity': factory.dataset_identity, 'years': args.years,
        'corpus_years': args.corpus_years, 'data_cache': str(args.data_cache.resolve()),
        'runtime_seed_binding': factory.runtime_seed_binding,
        'lab_inference_serialized': True, 'record_wire': True, 'record_code': True,
        'protocol': protocol, 'image_id': executor.image_id}
    binding = {'protocol': protocol, 'world': world, 'initial_fingerprint': initial.fingerprint}
    plan_path = args.output / 'plan.json'
    if plan_path.exists() and json.loads(plan_path.read_text()) != binding:
        raise ValueError('frozen joint experiment plan changed')
    write_json_atomic(plan_path, binding, sort_keys=True, allow_nan=False)
    controllers = [NativeDesignCampaign(args.output / 'arms' / arm / 'campaign',
        initial_system=initial, loss_spec=loss, seeds=[args.seed], world_binding=world)
        for arm, loss in zip(arm_ids, losses)]
    errors_path = args.output / 'terminal-authoring-errors.json'
    errors = json.loads(errors_path.read_text()) if errors_path.exists() else {}
    started = time.monotonic()
    def progress(status):
        value = {'schema': protocol['schema'], 'status': status,
            'source_commit': factory.source_commit, 'wall_seconds_this_process': time.monotonic() - started,
            'budget_per_arm': args.budget,
            'arms': {arm: {'logical_observations': len(c.state['records']),
                'loss_path': [r['observation']['loss'] for r in c.state['records']],
                'candidate_fingerprints': [r['observation']['metadata']['system_fingerprint'] for r in c.state['records']],
                'terminal_authoring_error': errors.get(arm),
                'pending': c.state['pending'] is not None} for arm, c in zip(arm_ids, controllers)},
            'physical_complete_runs': len({r['run_id'] for c in controllers for row in c.state['records']
                for r in row['observation']['metadata']['runs']}),
            'interpretation': 'engineering proxies, one development seed; no held-out or scientific-quality claim'}
        write_json_atomic(args.output / 'progress.json', value, sort_keys=True, allow_nan=False)
        print(json.dumps(value, sort_keys=True), flush=True)
        return value

    progress('running-shared-baseline')
    if not controllers[0].state['records']:
        record = controllers[0].advance(simulation_factory=factory)
        if record['observation']['status'] != 'complete':
            progress('failed-native-initial-no-comparison')
            raise ValueError('physical initial failed; no baseline adoption or authoring')
    for c in controllers[1:]:
        adopt_shared_initial(c, controllers[0], checkpoint_measurement=checkpoint_measurements)
    progress('running-objective-conditioned-search')
    context = parent_context_provider(args.output / 'runs', source_commit=factory.source_commit)
    designers = []
    try:
        proposers = []
        for arm, c in zip(arm_ids, controllers):
            model = VLLMServerModel(factory.model,
                base_url='http://127.0.0.1:11434/v1', server_backend='ollama',
                run_seed=args.seed, model_revision=factory.model_digest,
                thinking_override=args.designer_thinking, max_tokens_override=args.max_tokens,
                sdk_max_retries=0, request_timeout=240)
            model.response_cache = CompletedResponseCache(args.output / 'arms' / arm / 'designer-replies.sqlite',
                binding={'protocol': protocol['schema'], 'cell': initial.fingerprint,
                    'model': factory.model, 'model_revision': factory.model_digest,
                    'corpus_sha256': factory.corpus_sha256, 'seed': args.seed,
                    'science_config': {'source_commit': factory.source_commit,
                        'objective_campaign_binding': c.binding, 'protocol': protocol}})
            serialize_native_http(model, args.inference_lock)
            designers.append(model)
            proposer_class = NativeRegionIRProposer
            if args.authoring_format == 'boundary-v5a2':
                from utopia.optimization.native_region_proposer_v5a2 import NativeBoundaryRegionProposer
                proposer_class = NativeBoundaryRegionProposer
            elif args.authoring_format == 'staged-v5':
                from utopia.optimization.native_staged_region_proposer import NativeStagedRegionProposer
                proposer_class = NativeStagedRegionProposer
            proposers.append(proposer_class(model, executor,
                removed_nodes=['world.selection'], context_provider=context,
                receipts=args.output / 'arms' / arm / 'design-proposals',
                max_attempts=args.max_technical_drafts, max_tokens=args.max_tokens,
                instructions='Optimize the exact supplied LossSpec, not an assumed scientific-policy preference. '
                'You may freely change Python, number of internal institutions, intermediate protocols and explicit wiring. '
                'A one-node design is legal; there is no reward for cosmetic complexity. '
                'Q is the sum of actual raw peer-review means over accepted decisions, A actual accept count, '
                'R actual review records; your final_score cannot manufacture Q. '
                'After native feedback, diagnose what happened and propose the next actual executable design.'))
        for index in range(1, args.budget):
            for arm, c, proposer in zip(arm_ids, controllers, proposers):
                if arm in errors or len(c.state['records']) > index:
                    continue
                try:
                    c.advance(simulation_factory=factory, proposer=proposer)
                except Exception as error:
                    # Only the declared exhausted technical-draft budget is a
                    # terminal authoring result. Cache/transport/checkpoint or
                    # integrity errors must remain resumable (or fail closed),
                    # especially once an exact pending native run is saved.
                    if (c.state['pending'] is not None or not isinstance(error, ValueError)
                            or str(error) != 'bounded region technical drafts exhausted; no native loss fabricated'):
                        progress('interrupted-preserve-pending-and-exact-drafts')
                        raise
                    errors[arm] = {'proposal_index': index,
                        'error_type': type(error).__name__, 'error': str(error)[:4000],
                        'loss': None, 'automatic_redraft': False}
                    write_json_atomic(errors_path, errors, sort_keys=True, allow_nan=False)
                progress('running-objective-conditioned-search')
    finally:
        for model in designers:
            model.response_cache.close()
    complete = all(len(c.state['records']) == args.budget for c in controllers)
    terminal = progress('declared-budget-complete' if complete else 'terminal-with-preserved-failures')
    for arm, c in zip(arm_ids, controllers):
        write_json_atomic(args.output / 'arms' / arm / 'completion.json', {
            'status': 'declared-budget-complete' if len(c.state['records']) == args.budget
                else 'terminal-authoring-failure-not-budget-complete',
            'budget': len(c.state['records']), 'declared_budget': args.budget,
            'logical_observations': len(c.state['records']),
            'terminal_authoring_error': errors.get(arm),
            'source_commit': factory.source_commit}, sort_keys=True, allow_nan=False)
    write_json_atomic(args.output / 'completion.json', terminal, sort_keys=True, allow_nan=False)


if __name__ == '__main__':
    main()
