#!/usr/bin/env python3
"""Freeze the separate two-slot UI authoring QA before any generation POST.

Preparation reads operator-owned model/corpus/image identities. It neither
submits a queue job nor creates a researcher simulation or designer response.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_search_v14 import make_search_plan
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import write_json_atomic


def build_manifest(*, source_commit, initial_system, loss_spec, provider_binding,
                   runtime_seed_binding, protocol_sha256):
    request = {'schema': 'scienceutopia.native-search-request.v14',
        'initial_system': clone(initial_system), 'loss_spec': clone(loss_spec),
        'seed': 42, 'years': 2, 'method': 'blackbox', 'native_budget': 2,
        'designer': {'model': 'qwen3:8b', 'max_attempts': 2, 'max_tokens': 4096}}
    plan = make_search_plan(request, source_commit=source_commit, provider_binding=provider_binding)
    return {'schema': 'scienceutopia.native-authoring-ir-technical-qa.v14',
        'classification': 'actual-ui-native-authoring-ir-engineering-qa-v14',
        'source_commit': source_commit, 'protocol_sha256': protocol_sha256,
        'request': request, 'request_sha256': digest(request),
        'operator_config': {'provider_binding': clone(provider_binding)},
        'search_plan': plan, 'plan_sha256': digest(plan),
        'runtime_seed_binding': clone(runtime_seed_binding),
        'population': {'authors': 5, 'conference_setting': 1},
        'budget': {'scheduled_native_slots': 2, 'free_generations': 2,
            'maximum_generation_POSTs': 4, 'maximum_digest_preflight_GETs': 4,
            'replacement_policy': 'none'},
        'native_experiment_binding': {'request_sha256': digest(request), 'loss_spec': clone(loss_spec)},
        'separate_from_closed_a1': True, 'no_calls_during_preparation': True,
        'success_or_novelty_required': False, 'same_society_adoption': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--data-cache', required=True, type=Path)
    args = parser.parse_args()
    source = pinned_revision(ROOT)
    from utopia.optimization.native_factory import LocalQwenNativeFactory
    from utopia.system.code_mechanisms import DockerCodeExecutor
    from utopia.system.native_open_examples import open_native_system
    output = args.output.resolve()
    if output.exists():
        raise ValueError('fresh prospective QA output directory required; never overwrite a frozen manifest')
    binding = LocalQwenNativeFactory(output / 'binding-only-no-worlds', args.data_cache,
        years=2, corpus_years=4)
    provider = {key: clone(getattr(binding, key)) for key in
        ('model', 'model_digest', 'corpus_sha256', 'dataset_identity', 'corpus_years')}
    provider['image_id'] = DockerCodeExecutor().image_id
    loss = json.loads((ROOT / 'research/objectives/losses/native-joint-v5-throughput.json').read_text())
    protocol = ROOT / 'research/protocols/campaigns/native-authoring-ir-v14-technical-qa.md'
    manifest = build_manifest(source_commit=source,
        initial_system=open_native_system(provider['image_id']).to_dict(), loss_spec=loss,
        provider_binding=provider, runtime_seed_binding=binding.runtime_seed_binding,
        protocol_sha256=hashlib.sha256(protocol.read_bytes()).hexdigest())
    manifest['content_sha256'] = digest(manifest)
    for name, value in [('manifest.json', manifest), ('request.json', manifest['request']),
                        ('operator-config.json', manifest['operator_config'])]:
        write_json_atomic(output / name, value, sort_keys=True, allow_nan=False)
    print(json.dumps({key: manifest[key] for key in
        ('source_commit', 'request_sha256', 'plan_sha256', 'content_sha256')}), flush=True)
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
