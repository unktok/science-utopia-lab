#!/usr/bin/env python3
"""Native hard institution -> actual trace -> soft fit -> fresh native world."""
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
    parser.add_argument('--loss', type=Path, required=True)
    parser.add_argument('--seed', type=int, default=1301)
    parser.add_argument('--years', type=int, default=2)
    parser.add_argument('--steps', type=int, default=30)
    parser.add_argument('--corpus-years', type=int, help='explicit fixed corpus horizon, >= simulation years')
    args = parser.parse_args()
    from utopia.optimization.loss import load_loss_spec, loss_spec_sha256
    from utopia.optimization.native_design import NativeDesignCampaign
    from utopia.optimization.native_factory import LocalQwenNativeFactory
    from utopia.optimization.native_relaxation import native_tensor_trace, fit_native_tensor_trace
    from utopia.runtime.checkpointing import read_portable_checkpoint
    from utopia.system.native_kernel import legacy_world_system
    from utopia.system.native_tensor_examples import tensor_selection_system
    from utopia.system.code_mechanisms import DockerCodeExecutor
    from utopia.system.design_patch import make_patch, digest
    from utopia.system.tensor_program import IMPLEMENTATION
    from utopia.utils.data_utils import write_json_atomic, file_sha256
    loss = load_loss_spec(args.loss)
    # This bridge supports only this declared engineering target; no surrogate
    # for an arbitrary LossSpec is invented or silently substituted.
    if loss_spec_sha256(loss) != loss_spec_sha256(load_loss_spec(ROOT / 'research/objectives/losses/native-accepted-count-engineering-v1.json')):
        parser.error('this pilot requires the explicit accepted-count engineering LossSpec')
    initial = tensor_selection_system(legacy_world_system(seed=args.seed), image_id=DockerCodeExecutor().image_id)
    factory = LocalQwenNativeFactory(args.output / 'runs', args.data_cache, years=args.years, corpus_years=args.corpus_years,
        experiment_binding={'loss_spec': loss, 'method': 'native-trace-relaxation-v1', 'steps': args.steps})
    controller = NativeDesignCampaign(args.output / 'campaign', initial_system=initial, loss_spec=loss,
        seeds=[args.seed], world_binding={'source_commit': factory.source_commit, 'model': factory.model,
            'model_digest': factory.model_digest, 'corpus_sha256': factory.corpus_sha256,
            'dataset_identity': factory.dataset_identity, 'years': args.years, 'corpus_years': factory.corpus_years,
            'population': 'five-independent-balanced-researchers', 'steps': args.steps,
            'method': 'native-trace-relaxation-v1', 'data_cache': str(args.data_cache.resolve())})
    def propose(parent, history, index, loss_spec):
        observation = history[-1]['observation']
        if observation['status'] != 'complete':
            raise ValueError('no completed native trace to relax; failure retains null loss')
        evidence = observation['metadata']['runs'][0]
        if file_sha256(evidence['checkpoint_path']) != evidence['checkpoint_sha256']:
            raise ValueError('native training checkpoint changed')
        saved = read_portable_checkpoint(evidence['checkpoint_path'])['native_system']
        trace = native_tensor_trace(saved['events'])
        programs = {n.mechanism_id: n.parameters['program'] for n in parent.mechanisms if n.implementation == IMPLEMENTATION}
        fit = fit_native_tensor_trace(trace, programs, trainable={'addressed-selection': ['keys', 'thresholds', 'bias']},
            terms=[{'mechanism': 'addressed-selection', 'output': 'accept', 'coefficient': -1.}],
            steps=args.steps, temperature=0.8, learning_rate=0.1)
        fit['native_training_observation_id'] = observation['observation_id']
        fit['checkpoint_sha256'] = evidence['checkpoint_sha256']
        write_json_atomic(args.output / 'relaxation.json', fit, allow_nan=False)
        write_json_atomic(args.output / 'native-training-trace.json', trace, allow_nan=False)
        operations = [{'op': 'replace', 'path': f'/mechanisms/{i}/parameters/program',
            'value': fit['programs'][n.mechanism_id]} for i, n in enumerate(parent.mechanisms) if n.mechanism_id in fit['programs']]
        return make_patch(parent, operations, rationale='Autograd on actual native trace through addressed memory/branch/state; fresh native evaluation required')
    started = time.monotonic()
    while len(controller.state['records']) < 2:
        record = controller.advance(simulation_factory=factory, proposer=propose)
        print(json.dumps({'completed': len(controller.state['records']), 'status': record['observation']['status'],
                          'native_loss': record['observation']['loss']}), flush=True)
    write_json_atomic(args.output / 'completion.json', {'status': 'budget-exhausted', 'budget': 2,
        'source_commit': factory.source_commit, 'wall_seconds_this_process': time.monotonic() - started,
        'records_sha256': digest(controller.state['records']),
        'incumbent_suggestion_id': controller.incumbent()['suggestion']['suggestion_id'] if controller.incumbent() else None,
        'interpretation': 'conditional tensor autograd proposal followed by fresh native evaluation; not full native-world autograd'}, allow_nan=False)


if __name__ == '__main__':
    main()
