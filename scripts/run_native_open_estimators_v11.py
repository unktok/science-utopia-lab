#!/usr/bin/env python3
"""Eight-world open native design pilot: black-box vs expectation gradient.

No designer source is authored by this driver. External request-bound manifests
may invent code/protocol/wiring, preserving the original fixed-Qwen world.
"""
from __future__ import annotations

import argparse
import fcntl
import json
from pathlib import Path
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from utopia.optimization.loss import load_loss_spec
from utopia.optimization.native_adaptive_search import (
    EXPECTATION_ESTIMATOR, InboxVocabularyGenerator, NativeAdaptiveDesignCampaign)
from utopia.optimization.native_manifest_inbox import (
    ExternalAuthoringPending, ManifestInbox, audit_manifest_inbox)
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256, write_json_atomic

SCHEMA = 'scienceutopia.native-open-estimators-pilot.v11'
ACTUAL = 'actual-native-qwen-open-estimators-development-v11'
EXPERIMENT = {'protocol': 'native-open-estimators-v11', 'role': 'development-engineering'}
ARM_IDS = ('blackbox', 'score-control-variate')
GENERATIONS, DRAWS, SEED = 2, 2, 42
ESTIMATOR_CONFIG = {'name': EXPECTATION_ESTIMATOR, 'ridge': 1e-6}
INSTRUCTIONS = (
    'Optimize only the exact supplied LossSpec; no extra fairness, quality, novelty or promotion veto. '
    'The forward world is the original five fixed-Qwen researchers with real projects/papers/retrieval, '
    'language decisions, resource state and scientific activities. Do not substitute numeric science laws. '
    'You may invent arbitrary isolated Python institutional algorithms, new nodes/ports/protocols, '
    'connections, schedules and executable activity dependency/branch/repetition processes. Existing '
    'review/publication/funding institutions may be replaced or removed with explicit executable '
    'downstream contracts. No mandatory institution ID and no host catalogue of mechanism choices. '
    'All new code, ABI, capabilities, wires and schedules must be authored explicitly. No host semantic '
    'repair, inferred wiring, generated host execution, paid provider or privileged world mutation. '
    'A base_patch binds the exact parent fingerprint. Factor operations apply to its post-patch system. '
    'Continuous coordinates have exact ID/path/bounds/latent mean/sigma and must exist in every factor '
    'assignment. No invalid draw is filtered, replaced, penalized or rerolled. Empty factors or coordinates '
    'are legal; do not force diversity. Two generations of two IID draws is a fixed per-arm budget. '
    'Use only this request own-arm history and exact native losses. Explicitly carry useful learned '
    'logits/means into the next vocabulary, or explain a deliberate reset in provenance. No automatic '
    'dimensional transport. A prior fitted control variate is compatible only if executable source, '
    'topology, factor IDs/choices/edits, continuous IDs/order/paths/bounds/sigma and base state outside '
    'overwritten continuous fields are unchanged. Changing these is allowed but resets the surrogate '
    'to plain likelihood-ratio estimation. Distribution means/logits may change. Other-arm and future '
    'outcomes are not supplied. External author identity is self-reported, not authenticated. '
    'The blackbox arm uses loss-conditioned external redesign, not a claimed named Bayesian optimizer. '
    'The score arm uses a frozen-prior fitted surrogate with an exact expectation correction; the first '
    'batch without compatible prior data uses plain LR. Plain LR/LOO comparisons are recorded offline '
    'on the same draws, not extra native worlds. Do not claim variance reduction from two samples.'
)


def load_preregistered_loss(path):
    loss = load_loss_spec(path)
    expected = load_loss_spec(ROOT / 'research/objectives/losses/native-joint-v5-net-reviewed-utility.json')
    if loss != expected:
        raise ValueError('v11 requires exact preregistered native net-reviewed-utility loss')
    return loss


def advance_arms(campaigns, generators, *, simulation_factory, snapshot):
    waiting = {}
    if any(record_failed(record) for campaign in campaigns.values()
            for record in campaign.state['records']):
        snapshot()
        return waiting
    for generation in range(GENERATIONS):
        for arm in ARM_IDS:
            campaign = campaigns[arm]
            if arm in waiting or len(campaign.state['records']) > generation:
                continue
            try:
                record = campaign.advance(simulation_factory=simulation_factory,
                    generators={'design': generators[arm]}, count=DRAWS)
                if record_failed(record):
                    snapshot()
                    return waiting
            except ExternalAuthoringPending as error:
                waiting[arm] = error.to_dict()
            snapshot()
    return waiting


def record_failed(record):
    if record is None:  # Small orchestration fixtures return no record.
        return False
    return bool(record.get('generation_error') or
        any(draw.get('technical_error') for draw in record.get('draws', [])) or
        any(not observation or observation['status'] != 'complete' or
            observation['metadata'].get('technical_failures')
            for observation in record.get('observations', [])) or
        (record.get('report') or {}).get('status') == 'not-updated-estimator-failure')


def summarize(output, plan, campaigns):
    output = Path(output)
    complete = failures = committed = 0
    arms = {}
    for name, campaign in campaigns.items():
        arms[name] = {'binding': campaign.binding, 'records': campaign.state['records'],
            'pending': campaign.state['pending'],
            'authoring': audit_manifest_inbox(output / 'arms' / name / 'authoring')}
        for record in campaign.state['records']:
            failures += bool(record['generation_error'])
            failures += (record.get('report') or {}).get('status') == 'not-updated-estimator-failure'
            for draw, observation in zip(record['draws'], record['observations']):
                committed += 1
                valid = observation and observation['status'] == 'complete' and not observation['metadata'].get('technical_failures')
                complete += bool(valid)
                failures += not bool(valid)
    terminal = all(len(c.state['records']) == GENERATIONS and c.state['pending'] is None
        for c in campaigns.values())
    stopped = any(record_failed(record) for c in campaigns.values() for record in c.state['records'])
    caches = []
    for path in sorted((output / 'worlds').glob('*/replies/responses.sqlite')):
        with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as db:
            counts = dict(db.execute('SELECT outcome,COUNT(*) FROM replies GROUP BY outcome').fetchall())
        caches.append({'path': str(path.resolve()), 'sha256': file_sha256(path), 'outcomes': counts})
    replies = sum(c['outcomes'].get('response', 0) for c in caches)
    value = {'schema': SCHEMA, 'classification': plan['world']['classification'],
        'source_commit': plan['world']['source_commit'], 'plan': plan,
        'status': 'technically-stopped' if stopped else 'complete' if terminal and complete == 8 and not failures else
            'budget-complete-with-failures' if terminal else 'in-progress',
        'budget_terminal': terminal, 'planned_native_world_budget': 8,
        'stopped_on_technical_failure': stopped,
        'committed_draws': committed, 'complete_native_worlds': complete,
        'technical_failures': failures, 'configured_researcher_provider': 'qwen3:8b',
        'physical_reply_count': replies, 'physical_response_caches': caches, 'arms': arms,
        'claims': {'live_fixed_Qwen_researchers': replies > 0, 'scripted_researcher_HTTP': False,
            'held_out': False, 'causal_institutional_benefit': False, 'scientific_value': False,
            'designer_improvement_established': False, 'full_native_world_pathwise_autograd': False,
            'variance_reduction_established': False, 'external_authorship_authenticated': False}}
    value['content_sha256'] = digest(value)
    write_json_atomic(output / 'evidence.json', value, sort_keys=True, allow_nan=False)
    return value


def run(args):
    loss = load_preregistered_loss(args.loss)
    from utopia.optimization.native_factory import LocalQwenNativeFactory
    from utopia.system.code_mechanisms import DockerCodeExecutor
    from utopia.system.native_open_examples import open_native_system
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
        'world': world, 'arm_ids': list(ARM_IDS), 'loss_spec': loss, 'seed': SEED,
        'generations': GENERATIONS, 'draws_per_generation': DRAWS,
        'population': {'authors': 5, 'conference_setting': 1},
        'methods': {'blackbox': {'mode': 'blackbox', 'expectation_estimator': None},
            'score-control-variate': {'mode': 'score', 'expectation_estimator': ESTIMATOR_CONFIG}},
        'initial_system': initial.to_dict(), 'instructions': INSTRUCTIONS,
        'scientific_benefit_required': False, 'structural_novelty_reward': False,
        'shared_physical_trajectories': False,
        'external_designer_provider': 'self-reported Codex specialist'}
    path = args.output / 'plan.json'
    if path.exists() and json.loads(path.read_text()) != plan:
        raise ValueError('frozen native open-estimator plan changed')
    if not path.exists():
        write_json_atomic(path, plan, sort_keys=True, allow_nan=False)
    strategies = {'design': {'kind': 'external-codex-authoring', 'provider_authenticated': False}}
    campaigns = {arm: NativeAdaptiveDesignCampaign(args.output / 'arms' / arm / 'campaign',
        initial_system=initial, loss_spec=loss, seeds=[SEED], world_binding=world,
        strategies=strategies, seed=SEED, **plan['methods'][arm]) for arm in ARM_IDS}
    generators = {arm: InboxVocabularyGenerator(ManifestInbox(args.output / 'arms' / arm / 'authoring'),
        instructions=INSTRUCTIONS) for arm in ARM_IDS}
    snapshot = lambda: summarize(args.output, plan, campaigns)
    try:
        waiting = advance_arms(campaigns, generators, simulation_factory=factory, snapshot=snapshot)
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
    parser.add_argument('--loss', type=Path, required=True)
    args = parser.parse_args()
    if subprocess.check_output(['git', 'status', '--porcelain'], cwd=ROOT):
        parser.error('experiments require a clean pinned source worktree')
    args.output = args.output.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    with (args.output / 'pilot-writer.lock').open('a') as owner:
        try:
            fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise RuntimeError('another native open-estimator writer owns this output')
        return run(args)


if __name__ == '__main__':
    raise SystemExit(main())
