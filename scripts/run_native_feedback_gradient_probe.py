#!/usr/bin/env python3
"""One paired full-native-loss gradient probe through changed researcher inputs.

Developer-authored advisory institution, not discovered source or full autograd.
Do not reroll equal-cost draws. Model weights and researcher personas stay fixed.
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
    parser.add_argument('--loss', type=Path, required=True)
    args = parser.parse_args()
    from utopia.system import MechanismSpec, MechanismFamily, PortSpec, ChannelKind
    from utopia.system.code_mechanisms import CODE_SCHEMA, CODE_IMPLEMENTATION, DockerCodeExecutor
    from utopia.system.native_kernel import legacy_world_system, WORLD_ARTIFACT
    from utopia.system.native_examples import connect_native_institution
    from utopia.optimization.loss import load_loss_spec
    from utopia.optimization.native_factory import LocalQwenNativeFactory
    from utopia.optimization.native_gradient import NativeScoreFunctionSearch, NativeGradientCampaign
    from utopia.utils.data_utils import write_json_atomic
    source = """def step(context):
    world = context['inputs']['observations'][0]['payload']
    strength = context['parameters']['exploration_weight']
    messages = []
    for a in world['ecosystem']['agents']:
        if a.get('can_author') and a.get('is_active'):
            messages.append({'payload': {'institution': 'declared advisory gradient probe',
                'observed_year': world['year'], 'observed_resources': a['resources'],
                'exploration_weight': strength,
                'advice': 'Consider this institutional exploration weight alongside your own research strategy when choosing the next direction; it is not a measurement of scientific quality.'},
                'actor_ids': [a['id']], 'artifact_ids': []})
    return {'outputs': {'messages': messages}, 'state': {'cycles': context['state'].get('cycles', 0) + 1}}
"""
    executor = DockerCodeExecutor()
    node = MechanismSpec('advisory-feedback', MechanismFamily.CUSTOM, CODE_IMPLEMENTATION,
        inputs=(PortSpec('observations', ChannelKind.ARTIFACT, WORLD_ARTIFACT),),
        outputs=(PortSpec('messages', ChannelKind.ARTIFACT, 'advisory-feedback-protocol', required=False),),
        parameters={'exploration_weight': 1., 'runtime_image_id': executor.image_id,
            'code_artifact': {'schema': CODE_SCHEMA, 'label': 'Developer advisory gradient probe', 'source': source,
                'inputs': {'observations': {'type': 'object'}}, 'outputs': {'messages': {'type': 'object'}}, 'state_schema': {'type': 'object'}}})
    system = connect_native_institution(legacy_world_system(seed=1301), node, phase=191, researcher_output='messages')
    index = next(i for i, n in enumerate(system.mechanisms) if n.mechanism_id == node.mechanism_id)
    bindings = [{'path': f'/mechanisms/{index}/parameters/exploration_weight', 'lower': 0., 'upper': 2.}]
    loss = load_loss_spec(args.loss)
    factory = LocalQwenNativeFactory(args.output / 'runs', args.data_cache, years=2, corpus_years=4,
        experiment_binding={'loss_spec': loss, 'method': 'paired-full-native-feedback-v2'})
    search = NativeScoreFunctionSearch(system, bindings, loss_spec=loss, sampling='antithetic', seed=42)
    campaign = NativeGradientCampaign(args.output / 'campaign', search, loss_spec=loss, seeds=[1301], world_binding={
        'source_commit': factory.source_commit, 'model': factory.model, 'model_digest': factory.model_digest,
        'corpus_sha256': factory.corpus_sha256, 'dataset_identity': factory.dataset_identity,
        'years': 2, 'corpus_years': 4, 'population': 'five-independent-balanced-researchers', 'scope': 'full native loss, smoothed design-distribution gradient, not pathwise autograd'})
    started = time.monotonic()
    if not campaign.state['reports']:
        campaign.advance(simulation_factory=factory, count=2)
    report = campaign.state['reports'][0]
    completion = {'source_commit': factory.source_commit, 'wall_seconds_this_process': time.monotonic() - started,
        'method': report['method'], 'status': report['status'], 'losses': report.get('losses'),
        'gradient': report['gradient'], 'mean_before': report['mean_before'], 'mean_after': report['mean_after'],
        'full_native_world_autograd': False, 'no_reroll_if_zero': True,
        'code_origin': 'developer-authored advisory diagnostic; not LLM invention'}
    write_json_atomic(args.output / 'completion.json', completion, allow_nan=False)
    print(json.dumps(completion), flush=True)


if __name__ == '__main__':
    main()
