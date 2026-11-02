#!/usr/bin/env python3
"""Six-world, loss-conditioned free redesign on the original researcher world.

Every generation asks an external author for complete executable source/graph
data. This driver contains no catalogue, source inventor or novelty reward.
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
from utopia.optimization.native_manifest_inbox import ExternalAuthoringPending, ManifestInbox, audit_manifest_inbox
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256, write_json_atomic

SCHEMA = 'scienceutopia.native-objective-redesign-pilot.v12'
ACTUAL = 'actual-native-qwen-objective-redesign-development-v12'
EXPERIMENT = {'protocol': 'native-objective-redesign-v12', 'role': 'development-engineering'}
GENERATIONS, DRAWS, SEED = 3, 1, 42
INSTRUCTIONS = (
    'Optimize only the supplied exact LossSpec, not its definition. Preserve the original researcher '
    'world, fixed Qwen weights, native projects/papers/retrieval/resources and language decisions; '
    'do not replace science with numeric toy laws. Return a complete freely authored executable '
    'institution vocabulary, not a choice from a host catalogue. New Python algorithms, mechanisms, '
    'actors/artifacts using registered capabilities, protocols, ports, wires, schedules and activity '
    'dependency/guard/repetition processes may be created, removed, replaced or retained. Existing '
    'review/publication/funding institutions are not mandatory if explicit downstream contracts '
    'keep the native world executable. All source and connections must be explicit. Code runs only '
    'in the pinned networkless sandbox, never as generated host functions or privileged world writes. '
    'Base patches bind this exact parent, preserving JSON integer/float distinctions; factors apply '
    'to the post-base-patch graph. No host repairs missing ABI, ports, process dependencies or wires. '
    'Use only this arm own completed history and technical failures. Future and other-arm results '
    'are not available. Explain retained or changed algorithms, graph, processes and state in '
    'provenance; a new label/hash alone is not institutional invention. Empty factor/continuous '
    'lists and unchanged designs are legal. No forced diversity, novelty reward, quality/fairness '
    'veto or promotion policy. Three generations of one draw is the fixed per-objective budget. '
    'Every failed/null attempt is retained, not scored as a penalty or replaced. A later scheduled '
    'generation may respond to that failure, not reroll it. The method is derivative-free '
    'loss-conditioned external redesign, not a claimed Bayesian optimizer or gradient of source '
    'invention. External author provenance is self-reported, not provider authenticated. Useful '
    'invention, improved designer ability, generalization and scientific value are not assumed.'
)


def load_preregistered_losses(paths):
    losses = [load_loss_spec(path) for path in paths]
    expected = [load_loss_spec(ROOT / 'research/objectives/losses' / name) for name in (
        'native-joint-v5-throughput.json', 'native-joint-v5-net-reviewed-utility.json')]
    if losses != expected:
        raise ValueError('v12 requires exact preregistered throughput/utility losses in order')
    return losses


def advance_arms(arms, campaigns, generators, *, simulation_factory, snapshot):
    waiting = {}
    for generation in range(GENERATIONS):
        for arm in arms:
            campaign = campaigns[arm]
            if arm in waiting or len(campaign.state['records']) > generation:
                continue
            try:
                campaign.advance(simulation_factory=simulation_factory,
                    generators={'design': generators[arm]}, count=DRAWS)
            except ExternalAuthoringPending as error:
                waiting[arm] = error.to_dict()
            snapshot()
    return waiting


def summarize(output, plan, campaigns):
    output = Path(output)
    complete = failures = draws = 0
    arms = {}
    for name, campaign in campaigns.items():
        arms[name] = {'binding': campaign.binding, 'records': campaign.state['records'],
            'pending': campaign.state['pending'],
            'authoring': audit_manifest_inbox(output / 'arms' / name / 'authoring')}
        for record in campaign.state['records']:
            failures += bool(record['generation_error'])
            for draw, observation in zip(record['draws'], record['observations']):
                draws += 1
                valid = observation and observation['status'] == 'complete' and not observation['metadata'].get('technical_failures')
                complete += bool(valid)
                failures += not bool(valid)
    terminal = all(len(c.state['records']) == GENERATIONS and c.state['pending'] is None for c in campaigns.values())
    caches = []
    for path in sorted((output / 'worlds').glob('*/replies/responses.sqlite')):
        with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as db:
            counts = dict(db.execute('SELECT outcome,COUNT(*) FROM replies GROUP BY outcome').fetchall())
        caches.append({'path': str(path.resolve()), 'sha256': file_sha256(path), 'outcomes': counts})
    replies = sum(c['outcomes'].get('response', 0) for c in caches)
    result = {'schema': SCHEMA, 'classification': plan['world']['classification'],
        'source_commit': plan['world']['source_commit'], 'plan': plan, 'budget_terminal': terminal,
        'status': 'complete' if terminal and complete == 6 and not failures else
            'budget-complete-with-failures' if terminal else 'in-progress',
        'planned_native_world_budget': 6, 'committed_draws': draws,
        'complete_native_worlds': complete, 'technical_failures': failures,
        'configured_researcher_provider': 'qwen3:8b', 'physical_reply_count': replies,
        'physical_response_caches': caches, 'arms': arms,
        'claims': {'live_fixed_Qwen_researchers': replies > 0, 'scripted_researcher_HTTP': False,
            'held_out': False, 'causal_institutional_benefit': False, 'scientific_value': False,
            'designer_improvement_established': False, 'full_native_world_pathwise_autograd': False,
            'variance_reduction_established': False, 'external_authorship_authenticated': False}}
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
        raise ValueError('two distinct loss definitions and safe arm IDs required')
    executor = DockerCodeExecutor()
    initial = open_native_system(executor.image_id)
    factory = LocalQwenNativeFactory(args.output / 'worlds', args.data_cache,
        years=2, corpus_years=4, experiment_binding=EXPERIMENT,
        record_wire=True, record_code=True, inference_lock=args.inference_lock)
    world = {'source_commit': factory.source_commit, 'model_digest': factory.model_digest,
        'corpus_sha256': factory.corpus_sha256, 'years': 2, 'corpus_years': 4,
        'runtime_seed_binding': factory.runtime_seed_binding, 'experiment': EXPERIMENT,
        'image_id': executor.image_id, 'classification': ACTUAL}
    plan = {'schema': SCHEMA, 'classification': ACTUAL, 'experiment': EXPERIMENT,
        'world': world, 'arm_ids': arms, 'losses': losses, 'seed': SEED,
        'generations': GENERATIONS, 'draws_per_generation': DRAWS,
        'population': {'authors': 5, 'conference_setting': 1}, 'mode': 'blackbox',
        'initial_system': initial.to_dict(), 'instructions': INSTRUCTIONS,
        'scientific_benefit_required': False, 'structural_novelty_reward': False,
        'shared_physical_trajectories': False, 'external_designer_provider': 'self-reported Codex specialist'}
    path = args.output / 'plan.json'
    if path.exists() and json.loads(path.read_text()) != plan:
        raise ValueError('frozen native objective/redesign plan changed')
    if not path.exists():
        write_json_atomic(path, plan, sort_keys=True, allow_nan=False)
    strategies = {'design': {'kind': 'external-codex-authoring', 'provider_authenticated': False}}
    campaigns = {arm: NativeAdaptiveDesignCampaign(args.output / 'arms' / arm / 'campaign',
        initial_system=initial, loss_spec=loss, seeds=[SEED], world_binding=world,
        strategies=strategies, mode='blackbox', seed=SEED) for arm, loss in zip(arms, losses)}
    generators = {arm: InboxVocabularyGenerator(ManifestInbox(args.output / 'arms' / arm / 'authoring'),
        instructions=INSTRUCTIONS) for arm in arms}
    snapshot = lambda: summarize(args.output, plan, campaigns)
    try:
        waiting = advance_arms(arms, campaigns, generators, simulation_factory=factory, snapshot=snapshot)
    except BaseException:
        snapshot()
        raise
    evidence = snapshot()
    print(json.dumps({'status': 'waiting-for-external-authoring' if waiting else evidence['status'],
        'pending': waiting, 'complete_native_worlds': evidence['complete_native_worlds'],
        'physical_reply_count': evidence['physical_reply_count'], 'content_sha256': evidence['content_sha256']}), flush=True)
    return 3 if waiting else 0 if evidence['status'] == 'complete' else 2


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
            raise RuntimeError('another native objective/redesign writer owns this output')
        return run(args)


if __name__ == '__main__':
    raise SystemExit(main())
