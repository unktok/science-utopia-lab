#!/usr/bin/env python3
"""Fixed-LLM native REINFORCE over explicit arbitrary candidate SystemSpecs.

This learns design-selection probabilities, not source synthesis or pathwise
native derivatives. Every draw executes a fresh world; duplicate actions are
retained as distinct draws, never deduplicated or silently replaced.
"""
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
    parser.add_argument('--designs', type=Path, required=True, help='JSON list of complete SystemSpecs; any provenance must be recorded separately')
    parser.add_argument('--distribution', choices=['categorical', 'bernoulli'], default='categorical')
    parser.add_argument('--seed', type=int, default=1301)
    parser.add_argument('--search-seed', type=int, default=42)
    parser.add_argument('--samples', type=int, default=2)
    parser.add_argument('--batches', type=int, default=1)
    parser.add_argument('--years', type=int, default=3)
    parser.add_argument('--corpus-years', type=int)
    parser.add_argument('--learning-rate', type=float, default=0.1)
    parser.add_argument('--inference-lock', type=Path, required=True,
                        help='shared local inference queue lock; does not imply GPU concurrency')
    args = parser.parse_args()
    if args.samples < 1 or args.batches < 1:
        parser.error('positive explicit sample and batch budgets required')
    from utopia.optimization.loss import load_loss_spec
    from utopia.optimization.native_factory import LocalQwenNativeFactory
    from utopia.optimization.native_gradient import NativeGradientCampaign
    from utopia.optimization.native_discrete_policy import NativeDiscretePolicySearch
    from utopia.utils.data_utils import file_sha256
    loss = load_loss_spec(args.loss)
    factory = LocalQwenNativeFactory(args.output / 'runs', args.data_cache, years=args.years,
        corpus_years=args.corpus_years, experiment_binding={'loss_spec': loss, 'method': 'native-discrete-reinforce'},
        inference_lock=args.inference_lock)
    search = NativeDiscretePolicySearch(json.loads(args.designs.read_text()), loss_spec=loss,
        seed=args.search_seed, distribution=args.distribution, learning_rate=args.learning_rate)
    campaign = NativeGradientCampaign(args.output / 'campaign', search, loss_spec=loss, seeds=[args.seed],
        world_binding={'source_commit': factory.source_commit, 'model_digest': factory.model_digest,
            'corpus_sha256': factory.corpus_sha256, 'dataset_identity': factory.dataset_identity,
            'design_manifest_sha256': file_sha256(args.designs), 'years': args.years,
            'corpus_years': factory.corpus_years, 'data_cache': str(args.data_cache.resolve()),
            'candidate_origin': 'explicit input SystemSpecs, not automatically invented by this optimizer'})
    while len(campaign.state['reports']) < args.batches:
        result = campaign.advance(simulation_factory=factory, count=args.samples)
        print(json.dumps({k: result[k] for k in ('iteration', 'status', 'gradient', 'logits_before', 'logits_after')}), flush=True)


if __name__ == '__main__':
    main()
