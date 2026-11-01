#!/usr/bin/env python3
"""Optional external-designer inbox; fixed local Qwen native researchers.

No external provider API is called. Run only after explicit authorization and
preregistration from a clean pinned experiment worktree. Missing external
manifests are resumable waiting states, not failed scientific observations.
"""
import argparse
import fcntl
import json
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def advance_arms(arm_ids, controllers, proposers, *, simulation_factory, budget, errors):
    from utopia.optimization.native_manifest_inbox import ExternalAuthoringPending
    pending = {}
    for index in range(1, budget):
        for arm, controller, proposer in zip(arm_ids, controllers, proposers):
            if arm in errors or arm in pending or len(controller.state['records']) > index:
                continue
            try:
                controller.advance(simulation_factory=simulation_factory, proposer=proposer)
            except ExternalAuthoringPending as wait:
                pending[arm] = wait.to_dict()
            except ValueError as error:
                if (controller.state['pending'] is not None
                        or str(error) != 'bounded region technical drafts exhausted; no native loss fabricated'):
                    raise
                errors[arm] = {'proposal_index': index, 'error_type': type(error).__name__,
                    'error': str(error), 'loss': None, 'automatic_redraft': False}
    terminal = all(len(c.state['records']) >= budget or arm in errors for arm, c in zip(arm_ids, controllers))
    return {'terminal': terminal, 'pending_external_authoring': pending,
        'status': ('declared-budget-complete' if all(len(c.state['records']) >= budget for c in controllers)
            else 'terminal-with-preserved-failures' if terminal else 'waiting-for-external-authoring')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--data-cache', type=Path, required=True)
    parser.add_argument('--loss', type=Path, action='append', required=True)
    parser.add_argument('--inference-lock', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=1301)
    parser.add_argument('--years', type=int, default=2)
    parser.add_argument('--corpus-years', type=int, default=4)
    parser.add_argument('--budget', type=int, default=3)
    parser.add_argument('--max-technical-drafts', type=int, default=3)
    args = parser.parse_args()
    if len(args.loss) != 2 or not 2 <= args.budget <= 4 or not 1 <= args.max_technical_drafts <= 5:
        parser.error('exactly two explicit losses, budget2..4, and drafting budget1..5 required')
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT):
        parser.error('native experiments require a clean pinned source worktree')
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    lock = (args.output / '.driver.lock').open('a+')
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        parser.error('another external-native driver already owns this output directory')
    from utopia.optimization.loss import load_loss_spec, loss_spec_sha256
    from utopia.optimization.native_code_trace import parent_context_provider
    from utopia.optimization.native_design import NativeDesignCampaign
    from utopia.optimization.native_factory import LocalQwenNativeFactory
    from utopia.optimization.native_manifest_inbox import ManifestInbox
    from utopia.optimization.native_region_proposer_v5a2 import NativeBoundaryRegionProposer
    from utopia.optimization.native_shared_initial import adopt_shared_initial
    from utopia.system.code_mechanisms import DockerCodeExecutor
    from utopia.system.native_kernel import legacy_world_system
    from utopia.system.native_selection_slot import selection_source_slot
    from utopia.utils.data_utils import write_json_atomic
    from scripts.audit_native_objective_v5 import checkpoint_measurements
    losses = [load_loss_spec(path) for path in args.loss]
    arms = [re.sub(r'[^a-zA-Z0-9_-]', '-', loss['id']) for loss in losses]
    if len(set(arms)) != 2 or len({loss_spec_sha256(loss) for loss in losses}) != 2:
        parser.error('distinct losses and safe arm IDs required')
    protocol = {'schema': 'scienceutopia.external-native-objectives.v5',
        'kind': 'externalnative-v5', 'authoring_format': 'boundary-v5a2-external-manifest',
        'designer_transport': 'hash-bound-file-inbox-no-provider-API',
        'researcher_model': 'qwen3:8b', 'losses': losses, 'arm_ids': arms,
        'seed': args.seed, 'years': args.years, 'corpus_years': args.corpus_years,
        'budget_per_arm': args.budget, 'max_technical_drafts': args.max_technical_drafts,
        'requested_designer_max_tokens': 4096, 'population': 'five-independent-balanced-researchers',
        'shared_initial': 'one-physical-trajectory-not-independent-replications',
        'no_hidden_merit_or_promotion_veto': True}
    inboxes = [ManifestInbox(args.output / 'arms' / arm / 'authoring-inbox') for arm in arms]
    factory = LocalQwenNativeFactory(args.output / 'runs', args.data_cache,
        years=args.years, corpus_years=args.corpus_years, experiment_binding=protocol,
        record_wire=True, record_code=True, inference_lock=args.inference_lock)
    executor = DockerCodeExecutor()
    initial = selection_source_slot(legacy_world_system(seed=args.seed), image_id=executor.image_id)
    world = {'source_commit': factory.source_commit, 'model': factory.model,
        'model_digest': factory.model_digest, 'corpus_sha256': factory.corpus_sha256,
        'dataset_identity': factory.dataset_identity, 'years': args.years,
        'corpus_years': args.corpus_years, 'data_cache': str(args.data_cache.resolve()),
        'runtime_seed_binding': factory.runtime_seed_binding, 'lab_inference_serialized': True,
        'record_wire': True, 'record_code': True, 'protocol': protocol, 'image_id': executor.image_id}
    binding = {'protocol': protocol, 'world': world, 'initial_fingerprint': initial.fingerprint}
    path = args.output / 'plan.json'
    if path.exists() and json.loads(path.read_text()) != binding:
        raise ValueError('frozen external-native experiment plan changed')
    write_json_atomic(path, binding, sort_keys=True, allow_nan=False)
    controllers = [NativeDesignCampaign(args.output / 'arms' / arm / 'campaign',
        initial_system=initial, loss_spec=loss, seeds=[args.seed], world_binding=world)
        for arm, loss in zip(arms, losses)]
    if not controllers[0].state['records']:
        initial_record = controllers[0].advance(simulation_factory=factory)
        if initial_record['observation']['status'] != 'complete':
            raise ValueError('physical initial failed; no adoption or external authoring')
    for controller in controllers[1:]:
        adopt_shared_initial(controller, controllers[0], checkpoint_measurement=checkpoint_measurements)
    context = parent_context_provider(args.output / 'runs', source_commit=factory.source_commit)
    proposers = [NativeBoundaryRegionProposer(inbox, executor,
        removed_nodes=['world.selection'], context_provider=context,
        receipts=args.output / 'arms' / arm / 'design-proposals',
        max_attempts=args.max_technical_drafts, max_tokens=4096,
        instructions='Optimize only the supplied exact loss. Invent arbitrary Python institutions, protocols and explicit wiring. Original researcher agents stay fixed local Qwen3:8b. A one-node system is legal; no cosmetic complexity reward. '
        'IMPORTANT: old prompt projections can replace deeply nested arrays with omission-diagnostic dictionaries. These diagnostics are NOT the runtime ABI. '
        "Real access is context['inputs'][YOUR_PORT][0]['payload']; payload['conferences'] is a DICT containing payload['conferences']['conferences'], a LIST of conference dictionaries. "
        "Each conf['submitted_papers'] is a LIST of paper dictionaries. conf['reviews'] is a DICT mapping actual paper IDs to LISTS of review dictionaries; each review['overall_score'] is numeric. "
        'Use your chosen local input/output port names and explicit wires, not export aliases or omitted diagnostic keys. Native empty years require the actual empty_cycle marker. '
        'Q means sum of actual raw peer-review means over accepted decisions; generated final_score cannot fabricate Q. This request is externally authored, never evidence of Qwen designer authorship.')
        for arm, inbox in zip(arms, inboxes)]
    error_path = args.output / 'terminal-authoring-errors.json'
    errors = json.loads(error_path.read_text()) if error_path.exists() else {}
    outcome = advance_arms(arms, controllers, proposers, simulation_factory=factory,
        budget=args.budget, errors=errors)
    progress = {'schema': protocol['schema'], **outcome, 'source_commit': factory.source_commit,
        'arms': {arm: {'logical_observations': len(c.state['records']),
            'loss_path': [r['observation']['loss'] for r in c.state['records']],
            'pending_native_execution': c.state['pending'] is not None,
            'terminal_authoring_error': errors.get(arm)} for arm, c in zip(arms, controllers)},
        'interpretation': 'external author metadata is a claim, not provider authentication; no held-out/scientific-quality claim'}
    write_json_atomic(error_path, errors, sort_keys=True, allow_nan=False)
    write_json_atomic(args.output / 'progress.json', progress, sort_keys=True, allow_nan=False)
    if outcome['terminal']:
        write_json_atomic(args.output / 'completion.json', progress, sort_keys=True, allow_nan=False)
    print(json.dumps(progress, sort_keys=True), flush=True)
    lock.close()


if __name__ == '__main__':
    main()
