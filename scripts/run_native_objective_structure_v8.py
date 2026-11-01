#!/usr/bin/env python3
"""Two explicit objectives, open structural generation, fixed native researchers.

The runner authors no scientific mechanism and rewards no structural novelty.
Two generations x two conditional IID draws x two losses is a fixed eight-world
budget, not a success-conditioned budget. Missing external source is resumable.
"""
from __future__ import annotations

import argparse
import fcntl
import json
from pathlib import Path
import re
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from utopia.optimization.loss import load_loss_spec, loss_spec_sha256
from utopia.optimization.native_adaptive_search import NativeAdaptiveDesignCampaign, InboxVocabularyGenerator
from utopia.optimization.native_manifest_inbox import ManifestInbox, ExternalAuthoringPending, audit_manifest_inbox
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256, write_json_atomic

SCHEMA = 'scienceutopia.native-objective-structure-pilot.v8'
ACTUAL = 'actual-native-qwen-objective-structure-development-v8'
EXPERIMENT = {'protocol': 'native-objective-structure-v8', 'role': 'development-engineering'}
GENERATIONS, DRAWS, SEED = 2, 2, 42
INSTRUCTIONS = (
    'Optimize only the exact supplied loss, not the objective definition. The original scientific researcher '
    'world and fixed Qwen weights must remain the forward environment. Author arbitrary new Python algorithms, '
    'protocols, nodes, ports, edges and activity dependency/branch/repetition processes, or retain an existing '
    'system if justified. You may remove/replace the developer open-source, tensor or other institutional '
    'nodes; no instrumented institution ID is mandatory. Retain original researcher agents and actual '
    'research/project/paper/RAG/resource state and effects, not replacement numeric science laws. '
    'Institutions including review, selection and funding may be omitted or replaced when explicit '
    'downstream-compatible contracts keep the resulting native world executable. New source executes only in the pinned networkless '
    'container; no generated host functions, paid APIs or privileged world writes. All newly needed wires, '
    'artifact types, schedules, domain capabilities and output ABI must be explicitly authored. '
    'Base patch binds the exact parent fingerprint; factor operations apply to the post-base-patch system. '
    'No host fills missing wires or repairs invalid candidates. Use actual loss and failure history; carry '
    'learned means/logits only with explicit dimension transport. No forced diversity, hidden quality/fairness '
    'veto, novelty reward or claim of scientific benefit. Return a complete evolving mixed vocabulary, not '
    'a choice from a host catalogue. Empty factor/continuous lists and unchanged designs are legal. '
    'Other arm outcomes and future outcomes are not included in this request. Technical failures are null, '
    'not scored penalties or invitations to silently replace an executed draw.'
)


def load_preregistered_losses(paths):
    losses = [load_loss_spec(path) for path in paths]
    expected = [load_loss_spec(ROOT / 'research/objectives/losses' / name) for name in (
        'native-joint-v5-throughput.json', 'native-joint-v5-net-reviewed-utility.json')]
    if losses != expected:
        raise ValueError('v8 requires the exact preregistered throughput/utility losses in that order')
    return losses


def advance_arms(arms, campaigns, generators, *, simulation_factory, snapshot):
    """Round-robin durable advances; never convert unexpected errors to losses."""
    pending = {}
    for generation in range(GENERATIONS):
        for arm in arms:
            campaign = campaigns[arm]
            if arm in pending or len(campaign.state['records']) > generation:
                continue
            try:
                campaign.advance(simulation_factory=simulation_factory,
                    generators={key: generators[arm] for key in campaign.binding['strategies']}, count=DRAWS)
            except ExternalAuthoringPending as waiting:
                pending[arm] = waiting.to_dict()
            snapshot()
    return pending


def summarize(output, plan, campaigns):
    output = Path(output)
    arms = {name: {'binding': c.binding, 'records': c.state['records'], 'pending': c.state['pending'],
        'authoring': audit_manifest_inbox(output / 'arms' / name / 'authoring')}
        for name, c in campaigns.items()}
    complete, failures, draws = 0, 0, 0
    for c in campaigns.values():
        for record in c.state['records']:
            if record['generation_error']:
                failures += 1
            for draw, obs in zip(record['draws'], record['observations']):
                draws += 1
                if obs and obs['status'] == 'complete' and not obs['metadata'].get('technical_failures'):
                    complete += 1
                else:
                    failures += 1
    terminal = all(len(c.state['records']) == GENERATIONS and c.state['pending'] is None for c in campaigns.values())
    caches = []
    for path in sorted((output / 'worlds').glob('*/replies/responses.sqlite')):
        with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as db:
            counts = dict(db.execute('SELECT outcome,COUNT(*) FROM replies GROUP BY outcome').fetchall())
        caches.append({'path': str(path.resolve()), 'sha256': file_sha256(path), 'outcomes': counts})
    replies = sum(c['outcomes'].get('response', 0) for c in caches)
    result = {'schema': SCHEMA, 'classification': plan['world']['classification'],
        'source_commit': plan['world']['source_commit'], 'plan': plan,
        'status': 'complete' if terminal and complete == 8 and not failures else
            'budget-complete-with-failures' if terminal else 'in-progress',
        'budget_terminal': terminal, 'planned_native_world_budget': 8,
        'committed_draws': draws, 'complete_native_worlds': complete, 'technical_failures': failures,
        'configured_researcher_provider': 'qwen3:8b', 'physical_reply_count': replies,
        'physical_response_caches': caches, 'arms': arms,
        'claims': {'live_fixed_Qwen_researchers': replies > 0, 'scripted_researcher_HTTP': False,
            'held_out': False, 'causal_institutional_benefit': False, 'scientific_value': False,
            'designer_improvement_established': False, 'full_native_world_pathwise_autograd': False,
            'external_authorship_authenticated': False}}
    result['content_sha256'] = digest(result)
    write_json_atomic(output / 'evidence.json', result, sort_keys=True, allow_nan=False)
    return result


def run(args):
    losses = load_preregistered_losses(args.loss)
    from utopia.optimization.native_factory import LocalQwenNativeFactory
    from utopia.system.code_mechanisms import DockerCodeExecutor
    from utopia.system.native_open_examples import open_native_system

    arms = [re.sub(r'[^a-zA-Z0-9_-]', '-', loss['id']) for loss in losses]
    if len(set(arms)) != 2 or len({loss_spec_sha256(loss) for loss in losses}) != 2:
        raise ValueError('two distinct explicit loss definitions and safe arm IDs required')
    executor = DockerCodeExecutor()
    initial = open_native_system(executor.image_id)
    factory = LocalQwenNativeFactory(args.output / 'worlds', args.data_cache,
        years=2, corpus_years=4, experiment_binding=EXPERIMENT,
        record_wire=True, record_code=True, inference_lock=args.inference_lock)
    world = {'source_commit': factory.source_commit, 'model_digest': factory.model_digest,
        'corpus_sha256': factory.corpus_sha256, 'years': 2, 'corpus_years': 4,
        'runtime_seed_binding': factory.runtime_seed_binding, 'experiment': EXPERIMENT,
        'image_id': executor.image_id, 'classification': ACTUAL}
    plan = {'schema': SCHEMA, 'classification': ACTUAL, 'experiment': EXPERIMENT, 'world': world, 'arm_ids': arms,
        'losses': losses, 'seed': SEED, 'generations': GENERATIONS, 'draws_per_generation': DRAWS,
        'population': {'authors': 5, 'conference_setting': 1}, 'mode': 'hybrid',
        'initial_system': initial.to_dict(), 'instructions': INSTRUCTIONS,
        'scientific_benefit_required': False, 'structural_novelty_reward': False,
        'shared_physical_trajectories': False, 'external_designer_provider': 'self-reported Codex specialist'}
    path = args.output / 'plan.json'
    if path.exists() and json.loads(path.read_text()) != plan:
        raise ValueError('frozen native objective/structure plan changed')
    if not path.exists():
        write_json_atomic(path, plan, sort_keys=True, allow_nan=False)
    strategies = {name: {'kind': 'external-codex-authoring', 'scope': name, 'provider_authenticated': False}
        for name in ('invent', 'revise')}
    campaigns = {arm: NativeAdaptiveDesignCampaign(args.output / 'arms' / arm / 'campaign',
        initial_system=initial, loss_spec=loss, seeds=[SEED], world_binding=world,
        strategies=strategies, mode='hybrid', seed=SEED) for arm, loss in zip(arms, losses)}
    generators = {arm: InboxVocabularyGenerator(ManifestInbox(args.output / 'arms' / arm / 'authoring'),
        instructions=INSTRUCTIONS) for arm in arms}
    snapshot = lambda: summarize(args.output, plan, campaigns)
    try:
        pending = advance_arms(arms, campaigns, generators, simulation_factory=factory, snapshot=snapshot)
    except BaseException:
        snapshot()
        raise
    evidence = snapshot()
    print(json.dumps({'status': 'waiting-for-external-authoring' if pending else evidence['status'],
        'pending': pending, 'complete_native_worlds': evidence['complete_native_worlds'],
        'physical_reply_count': evidence['physical_reply_count'], 'content_sha256': evidence['content_sha256']}), flush=True)
    return 3 if pending else 0 if evidence['status'] == 'complete' else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--data-cache', type=Path, required=True)
    parser.add_argument('--inference-lock', type=Path, required=True)
    parser.add_argument('--loss', type=Path, action='append', required=True)
    args = parser.parse_args()
    if len(args.loss) != 2:
        parser.error('exactly two loss files required')
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT):
        parser.error('experiments require a clean pinned source worktree')
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / 'pilot-writer.lock').open('a') as owner:
        try:
            fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('another native objective/structure writer owns this output')
        return run(args)


if __name__ == '__main__':
    raise SystemExit(main())
