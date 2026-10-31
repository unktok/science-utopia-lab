#!/usr/bin/env python3
"""First native source/protocol/wiring loop. Explicit example or LLM proposer.

Run only in a clean pinned experiment worktree. This pilot count objective is
gameable and is NOT endorsed as scientific value. No implicit policy veto.
"""
import argparse
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--data-cache', type=Path, required=True)
    parser.add_argument('--loss', type=Path, required=True, help='explicit LossSpec; no hidden default objective')
    parser.add_argument('--seed', type=int, default=1301)
    parser.add_argument('--years', type=int, default=4)
    parser.add_argument('--budget', type=int, default=2)
    parser.add_argument('--proposer', choices=['example', 'llm', 'llm-intent', 'endogenous', 'fixed', 'source-revision'], default='example')
    parser.add_argument('--record-wire', action='store_true', help='retain actual native cache-miss model inputs locally')
    parser.add_argument('--revision-node', help='existing free-source observation/messages node to revise')
    parser.add_argument('--designer-plan', action='store_true', help='record an explicit model diagnosis/algorithm plan before source emission')
    parser.add_argument('--system', type=Path, help='optional initial SystemSpec; required for endogenous proposer')
    parser.add_argument('--designer-brief', type=Path, help='additional versioned task for the LLM designer')
    parser.add_argument('--corpus-years', type=int, help='explicit corpus horizon >= native simulation years')
    parser.add_argument('--initial-provenance', type=Path, help='recorded upstream candidate-generation receipt')
    args = parser.parse_args()
    if args.budget < 1 or (args.proposer == 'example' and args.budget > 2):
        parser.error('positive budget; declared example has one joint graph/code proposal (budget <=2)')
    if args.proposer == 'endogenous' and args.system is None:
        parser.error('endogenous mode requires a system that actually emits design proposals')
    if args.proposer == 'fixed' and (args.budget != 1 or args.system is None):
        parser.error('fixed mode evaluates exactly one explicitly supplied system')
    if args.proposer == 'source-revision' and (not args.revision_node or args.system is None):
        parser.error('source-revision requires an initial system and explicit revision node')
    from utopia.optimization.loss import load_loss_spec
    from utopia.optimization.native_design import NativeDesignCampaign, LLMNativeDesignProposer, propose_from_native_world
    from utopia.optimization.native_factory import LocalQwenNativeFactory
    from utopia.system.code_mechanisms import DockerCodeExecutor
    from utopia.system.native_design_examples import deliberation_patch
    from utopia.system.native_kernel import legacy_world_system
    from utopia.system import SystemSpec
    from utopia.replay.native_design import native_design_view
    from utopia.utils.data_utils import write_json_atomic
    from utopia.system.design_patch import digest
    brief = args.designer_brief.read_text() if args.designer_brief else ''
    initial_provenance = json.loads(args.initial_provenance.read_text()) if args.initial_provenance else None
    loss = load_loss_spec(args.loss)
    factory = LocalQwenNativeFactory(args.output / 'runs', args.data_cache, years=args.years, corpus_years=args.corpus_years,
                                    experiment_binding={'loss_spec': loss, 'initial_provenance': initial_provenance}, record_wire=args.record_wire)
    initial = SystemSpec.from_dict(json.loads(args.system.read_text())) if args.system else legacy_world_system(seed=args.seed)
    if initial_provenance and initial_provenance['candidate_fingerprint'] != initial.fingerprint:
        parser.error('upstream proposal receipt and initial system differ')
    controller = NativeDesignCampaign(args.output / 'campaign', initial_system=initial,
        loss_spec=loss, seeds=[args.seed], world_binding={'source_commit': factory.source_commit,
            'model': factory.model, 'model_digest': factory.model_digest,
            'corpus_sha256': factory.corpus_sha256, 'dataset_identity': factory.dataset_identity,
            'years': args.years, 'corpus_years': factory.corpus_years, 'population': 'five-independent-balanced-researchers',
            'proposer': args.proposer, 'designer_plan': args.designer_plan, 'revision_node': args.revision_node,
            'record_wire': args.record_wire, 'data_cache': str(args.data_cache.resolve()),
            'designer_brief_sha256': digest(brief), 'initial_provenance_sha256': digest(initial_provenance)})
    executor = DockerCodeExecutor()
    def example(parent, history, index, loss_spec):
        # Explicitly uses previous native loss; this deliberately limited
        # example is not LLM invention or an unbounded structural optimizer.
        previous = history[-1]['observation']['loss']
        threshold = max(1., min(7., 4. + (previous or 0.) / 10.))
        return deliberation_patch(parent, image_id=executor.image_id, threshold=threshold)
    proposer = example
    if args.proposer == 'endogenous':
        proposer = propose_from_native_world
    if args.proposer in {'llm', 'llm-intent', 'source-revision'}:
        from utopia.models.models import VLLMServerModel
        from utopia.models.response_cache import CompletedResponseCache
        designer = VLLMServerModel(factory.model, base_url='http://127.0.0.1:11434/v1', server_backend='ollama',
            run_seed=args.seed, model_revision=factory.model_digest, thinking_override=False,
            max_tokens_override=8192, sdk_max_retries=0, request_timeout=240)
        designer.response_cache = CompletedResponseCache(args.output / 'designer-replies' / 'responses.sqlite', binding={
            'protocol': 'native-design-proposal-v1', 'cell': controller.initial.fingerprint,
            'model': factory.model, 'model_revision': factory.model_digest, 'corpus_sha256': factory.corpus_sha256,
            'seed': args.seed, 'science_config': {'source_commit': factory.source_commit, 'loss_spec': loss,
                           'thinking_override': False, 'max_tokens': 8192, 'designer_brief_sha256': digest(brief), 'designer_plan': args.designer_plan}})
        if args.proposer == 'source-revision':
            from utopia.optimization.native_feedback import NativeSourceRevisionProposer
            proposer = NativeSourceRevisionProposer(designer, executor, node_id=args.revision_node,
                receipts=args.output / 'design-proposals', instructions=brief, planning=args.designer_plan)
        else:
            from utopia.optimization.native_feedback import feedback_from_native_history
            proposer = LLMNativeDesignProposer(designer, instructions=(
            'Keep native annual research/submission/funding prerequisites valid. Native selection requires reviews. '
            'A new Python node uses implementation code.python.v1; parameters contain code_artifact with exactly '
            '{schema:scienceutopia.code-mechanism.v1,label,source,inputs,outputs,state_schema} and runtime_image_id=' + executor.image_id +
            '. step(context) returns {outputs:{port:[{payload:object,actor_ids:[],artifact_ids:[]}]},state:object}. '
            'Port schemas describe payloads. Code uses only standard-library Python, no network/host files. '
            'Native publication requires decisions for exactly submitted paper IDs with conference_id, accept/reject, finite final_score; '
            'an empty cycle needs {empty_cycle:true}. Do not change the world seed or fabricate artifacts/reviews. '
            'A code context has period, parameters, state and inputs: {port:[{payload,actor_ids,artifact_ids,...}]}. '
            'Native world observations contain year,ecosystem:{agents:[{id,type,resources,...}]},papers:{papers:[...]}, '
            'conferences:{conferences:[{conference_id,submitted_papers:[{id,...}],reviews:{paper_id:[{overall_score,...}]}}]},year_results. '
            'Connect a native phase world output to a new artifact input of type native-world-observation. '
            'Code internal state must be an object, not a list. Native stage order is 0..240 in increments of 20. '
            'A new node may run between existing stages. Metadata labels do not install capabilities. '
            'Optional ports that can emit nothing require required:false. '
            'To deliver new artifact content to real next-year researcher prompts, add an optional messages input '
            'on a node with implementation native.world.researcher-context.v1, family communication, no outputs, '
            'scheduled at 235; its artifact_type must match the source output. '
            'New producer and consumer schemas may be designed together.\nDESIGNER TASK:\n' + brief),
            receipts=args.output / 'design-proposals', named_edits=args.proposer == 'llm-intent',
            feedback_provider=feedback_from_native_history)
    started = time.monotonic()
    try:
        while len(controller.state['records']) < args.budget:
            record = controller.advance(simulation_factory=factory, proposer=proposer)
            write_json_atomic(args.output / 'design-view.json', native_design_view(controller), allow_nan=False)
            print(json.dumps({'completed': len(controller.state['records']), 'budget': args.budget,
                              'status': record['observation']['status'], 'loss': record['observation']['loss']}), flush=True)
    finally:
        if args.proposer in {'llm', 'llm-intent', 'source-revision'}:
            designer.response_cache.close()
    write_json_atomic(args.output / 'completion.json', {'status': 'budget-exhausted', 'wall_seconds_this_process': time.monotonic()-started,
        'source_commit': factory.source_commit, 'proposer': args.proposer, 'budget': args.budget,
        'complete_observations': sum(r['observation']['status'] == 'complete' for r in controller.state['records']),
        'failed_observations': sum(r['observation']['status'] != 'complete' for r in controller.state['records']),
        'incumbent': controller.incumbent(), 'interpretation': 'development engineering probe, not scientific-policy improvement'}, allow_nan=False)


if __name__ == '__main__':
    main()
