#!/usr/bin/env python3
"""Live Qwen/native-world integration probe, not a replacement numeric world.

Uses original population initialization, RAG corpus/retrieval, researcher
prompts, submissions, reviews, acceptance, funding and yearly checkpoints.
The added code is a declared programmer-authored example, not claimed as an
LLM-discovered optimum. Supply --code-artifact for a different implementation.
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import threading
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2, allow_nan=False) + "\n")


def example_artifact():
    from utopia.system.code_mechanisms import CODE_SCHEMA
    return {"schema": CODE_SCHEMA, "label": "Research commons — native integration example",
        "inputs": {"observations": {"type": "object"}},
        "outputs": {"recommendations": {"type": "object"}}, "state_schema": {"type": "object"},
        "source": """def step(context):
    observed = context['inputs']['observations'][0]['payload']
    state = dict(context['state'])
    messages = []
    for actor in observed['ecosystem']['agents']:
        if actor.get('type') not in ('university', 'industry') or not actor['is_active']:
            continue
        papers = [p for p in observed['papers']['papers'] if p['author_id'] == actor['id']]
        recent = papers[-1] if papers else None
        messages.append({'actor_ids': [actor['id']], 'payload': {
            'kind': 'research-commons-plan',
            'current_project': actor['newest_direction'],
            'recent_paper': {'id': recent['id'], 'title': recent['title'], 'abstract': recent['abstract']} if recent else None,
            'proposal': 'Consider an independent replication or a falsifiable robustness test of the claims in your current project. Explain whether this information changes your research plan; it is not a required topic or an acceptance rule.'}})
    state['periods_observed'] = state.get('periods_observed', 0) + 1
    return {'outputs': {'recommendations': messages}, 'state': state}
"""}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--data-cache', type=Path, required=True)
    parser.add_argument('--years', type=int, default=4)
    parser.add_argument('--seed', type=int, default=1301)
    parser.add_argument('--code-artifact', type=Path)
    parser.add_argument('--allow-dirty-development', action='store_true')
    args = parser.parse_args()
    dirty = bool(subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT))
    if dirty and not args.allow_dirty_development:
        parser.error('recorded native probes require clean source')
    if args.output.exists() and any(args.output.iterdir()):
        parser.error('choose a new output directory; no completed run is overwritten')
    import requests
    from utopia.arguments import parse_arguments
    from utopia.models.models import VLLMServerModel
    from utopia.simulation import Simulation
    from utopia.system import ChannelKind, MechanismFamily, MechanismSpec, PortSpec
    from utopia.system.code_mechanisms import CODE_IMPLEMENTATION, DockerCodeExecutor, validate_code_artifact
    from utopia.system.native_kernel import NativeScienceKernel, WORLD_ARTIFACT, legacy_world_system
    from utopia.system.native_examples import connect_native_institution
    from utopia.optimization.native_world import measure_native_world
    from utopia.utils.seeding import set_seed

    model_name = 'qwen3:8b'
    tags = requests.get('http://localhost:11434/api/tags', timeout=10).json()['models']
    digest = next(m['digest'] for m in tags if m['name'] == model_name)
    executor = DockerCodeExecutor()
    artifact = json.loads(args.code_artifact.read_text()) if args.code_artifact else example_artifact()
    validate_code_artifact(artifact)
    node = MechanismSpec('research-commons', MechanismFamily.CUSTOM, CODE_IMPLEMENTATION,
        inputs=(PortSpec('observations', ChannelKind.ARTIFACT, WORLD_ARTIFACT),),
        outputs=(PortSpec('recommendations', ChannelKind.ARTIFACT, 'research-commons-plan'),),
        parameters={'code_artifact': artifact, 'runtime_image_id': executor.image_id})
    spec = connect_native_institution(legacy_world_system(seed=args.seed), node,
                                      researcher_output='recommendations')
    write(args.output / 'system-spec.json', spec.to_dict())
    native_args = parse_arguments([
        '--model', model_name, '--vllm_url', 'http://127.0.0.1:11434/v1', '--api-backend', 'ollama',
        '--num_years', str(args.years), '--seed', str(args.seed),
        '--population_mode', 'university_only', '--num_institutions', '5',
        '--researchers_per_institution', '1', '--num_conferences', '1',
        '--experiment_stage', 'smoke', '--run-id', 'native-kernel-probe', '--strategy_mix', 'balanced',
        '--funding_allocation_mode', 'fixed', '--experiment_name', 'default_native_kernel_probe',
        '--output-dir', str(args.output / 'simulation'), '--data-cache-dir', str(args.data_cache),
        '--science-system-spec', str(args.output / 'system-spec.json'), '--rag_device', 'cpu',
        '--batch_size', '1', '--max_retries', '2',
    ], create_dirs=True)
    model = VLLMServerModel(model_name, base_url='http://127.0.0.1:11434/v1', server_backend='ollama',
        max_concurrent_requests=1, run_seed=args.seed,
        model_revision=digest, max_tokens_override=768,
        thinking_override=False, sdk_max_retries=0, request_timeout=120)
    set_seed(args.seed)
    started = time.monotonic()
    sim = Simulation(model, num_years=args.years, output_dir=native_args.output_dir, args=native_args,
        funding_allocation_mode='fixed', experiment_name=native_args.experiment_name,
        always_rerun=False, max_retries=2)
    # Record actual cache-miss HTTP payloads, not merely constructed prompts.
    # Full inputs remain raw local evidence; only counts/hashes enter Git.
    wire_receipts = []
    wire_lock = threading.Lock()
    complete = model.client.chat.completions.create
    def recorded_completion(**payload):
        encoded = json.dumps(payload, ensure_ascii=False, sort_keys=True, allow_nan=False)
        frame = sim.native_system._frame
        receipt = {'year': frame['year'] if frame else None,
            'payload_sha256': hashlib.sha256(encoded.encode()).hexdigest(),
            'contains_institutional_context': 'research-commons-plan' in encoded,
            'payload': payload}
        with wire_lock:
            with (args.output / 'wire-requests.jsonl').open('a') as stream:
                stream.write(json.dumps(receipt, ensure_ascii=False, allow_nan=False) + '\n')
        response = complete(**payload)
        receipt.pop('payload')
        receipt['response_sha256'] = hashlib.sha256(response.model_dump_json().encode()).hexdigest()
        with wire_lock:
            wire_receipts.append(receipt)
        return response
    model.client.chat.completions.create = recorded_completion
    # Bind the actual ordered native corpus, not a placeholder hash. Restore
    # RNG after this read; Phase 2 still invokes the original load/index path.
    from utopia.runtime.checkpointing import capture_rng, restore_rng
    before = capture_rng()
    sim.rag.load_documents(num_years=args.years)
    restore_rng(before)
    binding = {'protocol': 'native-science-kernel-integration-v1', 'cell': spec.fingerprint,
        'model': model_name, 'model_revision': digest, 'corpus_sha256': sim.rag.document_identity,
        'science_config': {'years': args.years, 'seed': args.seed, 'system_fingerprint': spec.fingerprint,
                           'thinking_override': False, 'max_tokens': 768, 'concurrency': 1,
                           'population': {'institutions': 5, 'researchers_per_institution': 1,
                                          'strategy_mix': 'balanced'}}, 'seed': args.seed}
    from utopia.models.response_cache import CompletedResponseCache
    model.response_cache = CompletedResponseCache(args.output / 'replies' / 'responses.sqlite', binding=binding)
    sim.enable_portable_checkpoints(binding)
    report = {'schema': 'scienceutopia.native-world-probe.v1',
        'source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=ROOT, text=True).strip(),
        'dirty_development': dirty, 'system_fingerprint': spec.fingerprint, 'model_digest': digest,
        'population': binding['science_config']['population'],
        'world': 'original-Simulation-no-phase-or-corpus-substitution',
        'code_origin': 'supplied-artifact' if args.code_artifact else 'programmer-authored-example-not-discovery',
        'kernel_gradient_contract': sim.native_system.gradient_contract(), 'status': 'running'}
    write(args.output / 'manifest.json', report)
    try:
        sim.run()
        from utopia.runtime.checkpointing import read_portable_checkpoint
        kernel = sim.native_system.to_dict()
        checkpoint_path = Path(sim.output_dir) / f'portable_checkpoint_year_{args.years}.json.gz'
        restored = read_portable_checkpoint(checkpoint_path)
        NativeScienceKernel(spec, checkpoint=restored['native_system'])
        from utopia.replay import ArtifactBundle, convert_artifacts
        events = convert_artifacts(ArtifactBundle.discover(checkpoint_path))
        write(args.output / 'canonical-events.json', [e.to_dict() for e in events])
        write(args.output / 'kernel.json', kernel)
        report.update(status='complete', wall_seconds=time.monotonic()-started,
            measurements=measure_native_world(sim, run_id='native-world-probe'),
            checkpoint_kernel_restore_passed=True,
            native_context_receipts=sum(e.event_type=='native.system.context_delivered' for e in sim.native_system.events),
            actual_http_requests=len(wire_receipts),
            actual_http_with_context_by_year={str(y): sum(r['year']==y and r['contains_institutional_context']
                for r in wire_receipts) for y in range(1, args.years+1)},
            wire_requests_sha256=hashlib.sha256((args.output / 'wire-requests.jsonl').read_bytes()).hexdigest(),
            model_call_stats=model.call_stats,
            dataset_identity=sim.rag.dataset_identity,
            ordered_documents_sha256=sim.rag.document_identity,
            checkpoint_path=str(checkpoint_path.resolve()),
            checkpoint_sha256=hashlib.sha256(checkpoint_path.read_bytes()).hexdigest())
    except BaseException as error:
        report.update(status='failed', error_type=type(error).__name__, error=str(error)[:4000],
                      wall_seconds=time.monotonic()-started)
        raise
    finally:
        model.response_cache.close()
        write(args.output / 'manifest.json', report)
    print(json.dumps({'status': report['status'], 'wall_seconds': report['wall_seconds'],
                      'native_context_receipts': report['native_context_receipts']}))


if __name__ == '__main__':
    main()
