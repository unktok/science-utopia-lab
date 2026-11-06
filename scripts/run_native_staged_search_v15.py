#!/usr/bin/env python3
"""Explicitly authorized bounded staged-LLM/native searches, no manual answers."""
from __future__ import annotations

import argparse
import fcntl
import json
import os
from pathlib import Path
import sys
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_search_v15 import NativeStagedSearchQueue, make_search_plan
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import write_json_atomic
from utopia.optimization.native_designer_decoding_v24 import (
    decoding_contracts, STAGED_MAX_STEPS, STAGED_MAX_TOKENS)

SCHEMA = 'scienceutopia.staged-native-search-pilot.v15'
CLASSIFICATION = 'actual-local-qwen-native-file-workspace-development-v35'
ENGINEERING_REVISION = 'v35-a1'
SCHEDULE = (('throughput', 'native-joint-v5-throughput'),
            ('efficiency', 'native-reviewed-production-efficiency-v13'))


def build_plan(*, source_commit, initial_system, provider_binding, runtime_seed_binding):
    runs = []
    for identity, loss_id in SCHEDULE:
        loss = json.loads((ROOT / 'research/objectives/losses' / (loss_id + '.json')).read_text())
        request = {'schema': 'scienceutopia.native-search-request.v15',
            'initial_system': clone(initial_system), 'loss_spec': loss, 'seed': 42, 'years': 2,
            'method': 'blackbox', 'native_budget': 2,
            'designer': {'model': 'qwen3:8b', 'max_steps': STAGED_MAX_STEPS, 'max_tokens': STAGED_MAX_TOKENS}}
        plan = make_search_plan(request, source_commit=source_commit, provider_binding=provider_binding)
        runs.append({'id': identity, 'request': request, 'runtime_plan': plan, 'plan_sha256': digest(plan)})
    return {'schema': SCHEMA, 'classification': CLASSIFICATION, 'engineering_revision': ENGINEERING_REVISION,
        'source_commit': source_commit,
        'provider_binding': clone(provider_binding), 'runtime_seed_binding': clone(runtime_seed_binding),
        'initial_system': clone(initial_system), 'population': {'authors': 5, 'conference_setting': 1},
        'runs': runs, 'budget': {'scheduled_native_slots': 4, 'free_generations': 4,
            'maximum_generation_POSTs': 4 * STAGED_MAX_STEPS,
            'maximum_designer_digest_preflight_GETs': 4 * STAGED_MAX_STEPS,
            'per_generation_tool_steps': STAGED_MAX_STEPS, 'per_call_output_tokens': STAGED_MAX_TOKENS,
            'replacement_policy': 'none'},
        'authoring': 'local Qwen only; no human/Codex candidate implementation',
        'designer_decoding': decoding_contracts('staged-v15'),
        'metadata_preflights': 'Separate GET /api/tags during binding and each native-factory construction; repeated CLI startup can repeat metadata reads, never generation POSTs',
        'interface_certificate': 'Required before queue submission and author construction; current certificate '
            'is cold-replayed with live version/tags GETs before each designer POST. These additional '
            'metadata reads are not designer generations or scientific-world slots.',
        'continuation': 'failed engineering revisions remain separate; user authorizes further declared revisions until native loop works',
        'no_novelty_or_improvement_veto': True, 'same_society_adoption': False,
        'protocol': 'research/protocols/campaigns/native-file-workspace-v35-a1.md',
        'native_campaign_status': 'explicitly authorized two-objective two-generation native feedback pilot after V16 interface repair'}


def execute(args):
    from utopia.optimization.native_factory import LocalQwenNativeFactory
    from utopia.optimization.native_staged_author_v15 import make_local_staged_generator
    from utopia.system.code_mechanisms import DockerCodeExecutor
    from utopia.system.native_open_examples import open_native_system
    source = pinned_revision(ROOT)
    factory_binding = LocalQwenNativeFactory(args.output / 'binding-only-no-worlds', args.data_cache,
        years=2, corpus_years=4)
    provider = {k: clone(getattr(factory_binding, k)) for k in
        ('model', 'model_digest', 'corpus_sha256', 'dataset_identity', 'corpus_years')}
    provider['image_id'] = DockerCodeExecutor().image_id
    from utopia.optimization.native_designer_preflight import require_certificate
    require_certificate(args.designer_preflight, provider, protocol='staged-v15')
    plan = build_plan(source_commit=source, initial_system=open_native_system(provider['image_id']).to_dict(),
        provider_binding=provider, runtime_seed_binding=factory_binding.runtime_seed_binding)
    path = args.output / 'plan.json'
    if path.exists():
        if json.loads(path.read_text()) != plan:
            raise ValueError('frozen staged native pilot changed; never rewrite it')
    else:
        write_json_atomic(path, plan, sort_keys=True, allow_nan=False)
    queue = NativeStagedSearchQueue(args.output / 'queue', provider_binding=provider)
    searches = {}
    # Freeze/validate every request before the first model generation. CLI
    # authorization supplies exact request-bound consent; not a browser claim.
    for entry in plan['runs']:
        checked = queue.validate(entry['request'], source_commit=source)
        queued = queue.submit(entry['request'], confirmed_request_sha256=checked['request_sha256'], source_commit=source)
        searches[entry['id']] = queued['search_id']
    identities = args.output / 'searches.json'
    if identities.exists() and json.loads(identities.read_text()) != searches:
        raise ValueError('immutable queued search identities changed')
    write_json_atomic(identities, searches, sort_keys=True, allow_nan=False)
    write_json_atomic(args.output / 'operator-config.json', {'provider_binding': provider},
        sort_keys=True, allow_nan=False)

    def snapshot(_controller=None):
        runs = {name: queue.get(identity) for name, identity in searches.items()}
        result = {'schema': SCHEMA + '.progress', 'classification': CLASSIFICATION,
            'source_commit': source, 'plan_sha256': digest(plan), 'runs': runs,
            'terminal': all(r['status'] in ('complete', 'failed') for r in runs.values()),
            'scheduled_native_slots': 4,
            'consumed_native_slots': sum(r['budget']['consumed'] for r in runs.values())}
        result['content_sha256'] = digest(result)
        write_json_atomic(args.output / 'progress.json', result, sort_keys=True, allow_nan=False)
        return result

    def factory(root, request):
        return LocalQwenNativeFactory(root / 'worlds', args.data_cache, years=request['years'], corpus_years=4,
            record_wire=True, record_code=True, inference_lock=args.output / 'queue/inference.lock',
            experiment_binding={'request_sha256': digest(request), 'loss_spec': request['loss_spec']})

    def author(root, request, binding):
        return make_local_staged_generator(root / 'authoring', image_id=binding['image_id'],
            provider_binding=binding, max_steps=request['designer']['max_steps'],
            max_tokens=request['designer']['max_tokens'], inference_lock=args.output / 'queue/inference.lock',
            preflight_certificate=args.designer_preflight)

    snapshot()
    try:
        for _ in plan['runs']:
            result = queue.run_one(factory, generator_builder=author, source_commit=source, after_stage=snapshot)
            if result is None:
                break
            print(json.dumps({'search_id': result['search_id'], 'status': result['status'],
                'budget': result['budget'], 'best_loss': result['best']['loss']}), flush=True)
    finally:
        state = snapshot()
    print(json.dumps({'terminal': state['terminal'], 'consumed_native_slots': state['consumed_native_slots'],
        'no_more_automatic_trials_in_this_revision': True}), flush=True)
    # Failed worker construction/queue execution is a technical abortion, not a
    # successful campaign merely because no more work will be dispatched here.
    return 1 if any(run['status'] == 'failed' for run in state['runs'].values()) else 0


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--start-authorized-search', action='store_true', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--data-cache', type=Path, required=True)
    parser.add_argument('--designer-preflight', type=Path, required=True,
        help='operator-owned successful current-source/current-backend interface certificate')
    parser.add_argument('--resume-existing-launch', action='store_true',
        help='explicit source-matched resume; consumes existing journals, never replenishes budgets')
    args = parser.parse_args()
    pinned_revision(ROOT)
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / 'pilot-writer.lock').open('a') as handle:
        fcntl.flock(handle, fcntl.LOCK_EX | fcntl.LOCK_NB)
        started = args.output / 'writer.started.json'
        ended = args.output / 'writer.ended.json'
        if started.exists():
            original = json.loads(started.read_text())
            if not args.resume_existing_launch or original['source_commit'] != pinned_revision(ROOT):
                raise ValueError('existing launch requires explicit same-source resume; preserve all original receipts')
            number = 1 + len(list(args.output.glob('writer-resume-*.started.json')))
            started = args.output / f'writer-resume-{number:03d}.started.json'
            ended = args.output / f'writer-resume-{number:03d}.ended.json'
        elif args.resume_existing_launch:
            raise ValueError('resume requires an existing launch; no new budget is implicit')
        receipt = {'schema': 'scienceutopia.native-staged-writer.v17',
            'source_commit': pinned_revision(ROOT), 'argv': sys.argv,
            'started_utc': datetime.now(timezone.utc).isoformat(),
            'environment': {key: os.environ.get(key) for key in
                ('CUDA_VISIBLE_DEVICES', 'PYTHONHASHSEED', 'HF_HUB_OFFLINE', 'TRANSFORMERS_OFFLINE')},
            'certificate': str(args.designer_preflight.resolve()), 'status': 'started'}
        write_json_atomic(started, receipt, sort_keys=True, allow_nan=False)
        try:
            code = execute(args)
        except BaseException as error:
            receipt.update(status='aborted', error=type(error).__name__ + ': ' + str(error),
                ended_utc=datetime.now(timezone.utc).isoformat())
            write_json_atomic(ended, receipt, sort_keys=True, allow_nan=False)
            raise
        receipt.update(status='exited', exit_code=code, ended_utc=datetime.now(timezone.utc).isoformat())
        write_json_atomic(ended, receipt, sort_keys=True, allow_nan=False)
        return code


if __name__ == '__main__':
    raise SystemExit(main())
