#!/usr/bin/env python3
"""Native-loss score-function design search, NOT native-world autograd."""
import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--data-cache', type=Path, required=True)
    parser.add_argument('--loss', type=Path, required=True)
    parser.add_argument('--system', type=Path, required=True)
    parser.add_argument('--bindings', type=Path, required=True, help='JSON list of explicit {path,lower,upper}')
    parser.add_argument('--seed', type=int, default=1301)
    parser.add_argument('--search-seed', type=int, default=42)
    parser.add_argument('--years', type=int, default=4)
    parser.add_argument('--samples', type=int, default=2)
    parser.add_argument('--batches', type=int, default=1)
    args = parser.parse_args()
    if args.samples < 2 or args.batches < 1:
        parser.error('samples>=2 and batches>=1 required')
    from utopia.system import SystemSpec
    from utopia.optimization.loss import load_loss_spec
    from utopia.optimization.native_factory import LocalQwenNativeFactory
    from utopia.optimization.native_gradient import NativeScoreFunctionSearch, NativeGradientCampaign
    loss = load_loss_spec(args.loss)
    factory = LocalQwenNativeFactory(args.output / 'runs', args.data_cache, years=args.years,
                                    experiment_binding={'loss_spec': loss})
    system = SystemSpec.from_dict(json.loads(args.system.read_text()))
    search = NativeScoreFunctionSearch(system, json.loads(args.bindings.read_text()), loss_spec=loss, seed=args.search_seed)
    campaign = NativeGradientCampaign(args.output / 'campaign', search, loss_spec=loss, seeds=[args.seed],
        world_binding={'source_commit': factory.source_commit, 'model_digest': factory.model_digest,
                       'corpus_sha256': factory.corpus_sha256, 'dataset_identity': factory.dataset_identity,
                       'years': args.years, 'data_cache': str(args.data_cache.resolve())})
    while len(campaign.state['reports']) < args.batches:
        report = campaign.advance(simulation_factory=factory, count=args.samples)
        print(json.dumps({key: report[key] for key in ['iteration', 'status', 'mean_before', 'mean_after', 'gradient']}), flush=True)


if __name__ == '__main__':
    main()
