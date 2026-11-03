#!/usr/bin/env python3
"""Source-pinned eight-slot automatic-author/native pilot, no manual inbox."""
from __future__ import annotations

import argparse
import fcntl
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_search_v14 import NativeSearchController, make_search_plan
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import write_json_atomic

SCHEMA = 'scienceutopia.native-autonomous-search-pilot.v14'
CLASSIFICATION = 'actual-native-qwen-autonomous-search-development-v14'
EXPERIMENT = {'protocol': 'native-autonomous-search-v14', 'role': 'development-engineering'}
SCHEDULE = (
    ('throughput-blackbox', 'native-joint-v5-throughput', 'blackbox', 2),
    ('efficiency-blackbox', 'native-reviewed-production-efficiency-v13', 'blackbox', 2),
    ('efficiency-nested-lr', 'native-reviewed-production-efficiency-v13', 'nested-lr', 4),
)


def build_plan(*, source_commit, initial_system, provider_binding, runtime_seed_binding):
    losses = {name: json.loads((ROOT / 'research/objectives/losses' / (name + '.json')).read_text())
              for name in {entry[1] for entry in SCHEDULE}}
    runs = []
    for identity, loss, method, budget in SCHEDULE:
        request = {'schema': 'scienceutopia.native-search-request.v14',
            'initial_system': clone(initial_system), 'loss_spec': losses[loss],
            'seed': 42, 'years': 2, 'method': method, 'native_budget': budget,
            'designer': {'model': 'qwen3:8b', 'max_attempts': 2, 'max_tokens': 4096}}
        # Validate all three requests BEFORE the first author/provider call.
        make_search_plan(request, source_commit=source_commit, provider_binding=provider_binding)
        runs.append({'id': identity, 'request': request, 'directory': 'runs/' + identity})
    world = {**clone(provider_binding), 'source_commit': source_commit,
        'classification': CLASSIFICATION, 'years': 2, 'experiment': EXPERIMENT,
        'runtime_seed_binding': clone(runtime_seed_binding)}
    return {'schema': SCHEMA, 'classification': CLASSIFICATION, 'source_commit': source_commit,
        'experiment': EXPERIMENT, 'world': world, 'initial_system': clone(initial_system),
        'seed': 42, 'population': {'authors': 5, 'conference_setting': 1}, 'runs': runs,
        'designer_budget': {'generations': 6, 'max_attempts_per_generation': 2,
            'max_http_attempts': 12, 'http_budget_means': 'generation POSTs only; verification GETs separately',
            'max_verification_GETs': 12},
        'planned_native_world_budget': 8, 'replacement_policy': 'none',
        'completion_requires_useful_invention': False,
        'method_comparison': 'interface integration, not equal-budget method comparison'}


def run(args):
    from utopia.optimization.native_factory import LocalQwenNativeFactory
    from utopia.optimization.native_search_generator_v14 import make_local_vocabulary_generator
    from utopia.system.code_mechanisms import DockerCodeExecutor
    from utopia.system.native_open_examples import open_native_system

    source = pinned_revision(ROOT)
    executor = DockerCodeExecutor()
    binding_factory = LocalQwenNativeFactory(args.output / 'binding-only-no-worlds', args.data_cache,
        years=2, corpus_years=4, experiment_binding=EXPERIMENT,
        record_wire=True, record_code=True, inference_lock=args.inference_lock)
    provider = {key: clone(getattr(binding_factory, key)) for key in
        ('model', 'model_digest', 'corpus_sha256', 'dataset_identity', 'corpus_years')}
    provider['image_id'] = executor.image_id
    initial = open_native_system(executor.image_id)
    plan = build_plan(source_commit=source, initial_system=initial.to_dict(), provider_binding=provider,
        runtime_seed_binding=binding_factory.runtime_seed_binding)
    plan_path = args.output / 'plan.json'
    if plan_path.exists():
        if json.loads(plan_path.read_text()) != plan:
            raise ValueError('frozen actual autonomous pilot plan changed')
    else:
        write_json_atomic(plan_path, plan, sort_keys=True, allow_nan=False)
    controllers = {}
    for entry in plan['runs']:
        runtime_plan = make_search_plan(entry['request'], source_commit=source, provider_binding=provider)
        controllers[entry['id']] = NativeSearchController(args.output / entry['directory'],
            plan=runtime_plan, plan_sha256=digest(runtime_plan))

    def snapshot():
        projections = {}
        for entry in plan['runs']:
            controller = controllers[entry['id']]
            projection = controller.projection(search_id=entry['id'],
                status='complete' if controller.complete else 'running')
            projections[entry['id']] = projection
            write_json_atomic(args.output / entry['directory'] / 'progress.json', projection,
                              sort_keys=True, allow_nan=False)
        terminal = all(controller.complete for controller in controllers.values())
        result = {'schema': SCHEMA + '.progress', 'classification': CLASSIFICATION,
            'source_commit': source, 'plan_sha256': digest(plan),
            'status': 'complete' if terminal else 'in-progress',
            'runs': projections, 'budget_terminal': terminal,
            'consumed_native_slots': sum(v['budget']['consumed'] for v in projections.values()),
            'planned_native_world_budget': 8, 'no_manual_authoring': True,
            'model_weights_trained': False, 'same_society_adoption': False}
        result['content_sha256'] = digest(result)
        write_json_atomic(args.output / 'progress.json', result, sort_keys=True, allow_nan=False)
        return result

    snapshot()
    try:
        for entry in plan['runs']:
            controller = controllers[entry['id']]
            if controller.complete:
                continue  # terminal cold resume creates neither generating provider nor native factory
            root = args.output / entry['directory']
            factory = LocalQwenNativeFactory(root / 'worlds', args.data_cache,
                years=2, corpus_years=4, experiment_binding=EXPERIMENT,
                record_wire=True, record_code=True, inference_lock=args.inference_lock)
            actual = {key: clone(getattr(factory, key)) for key in provider if key != 'image_id'}
            if actual != {key: value for key, value in provider.items() if key != 'image_id'}:
                raise ValueError('native provider changed between automatic searches')
            generator = make_local_vocabulary_generator(root / 'authoring',
                image_id=executor.image_id, provider_binding=provider,
                max_attempts=2, max_tokens=4096, inference_lock=args.inference_lock)
            while not controller.complete:
                controller.advance(simulation_factory=factory, generator=generator)
                progress = snapshot()
                print(json.dumps({'run': entry['id'], 'consumed_native_slots': progress['consumed_native_slots'],
                    'run_budget': progress['runs'][entry['id']]['budget'],
                    'status': progress['runs'][entry['id']]['status']}), flush=True)
    except BaseException:
        snapshot()
        raise
    result = snapshot()
    print(json.dumps({'status': result['status'], 'consumed_native_slots': result['consumed_native_slots'],
        'planned_native_world_budget': 8, 'plan_sha256': digest(plan)}), flush=True)
    return 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--data-cache', type=Path, required=True)
    parser.add_argument('--inference-lock', type=Path,
        default=Path('/Users/shiro/unktok/dev/science-utopia-lab/outputs/native-parallel-v3-inference.lock'))
    args = parser.parse_args()
    pinned_revision(ROOT)
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / 'pilot-writer.lock').open('a') as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError as error:
            raise RuntimeError('another autonomous pilot owns this output') from error
        return run(args)


if __name__ == '__main__':
    raise SystemExit(main())
