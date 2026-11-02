#!/usr/bin/env python3
"""Finite eight-slot objective-conditioned nested free institutional search."""
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
from utopia.optimization.native_adaptive_search import InboxVocabularyGenerator
from utopia.optimization.native_manifest_inbox import ExternalAuthoringPending, ManifestInbox, audit_manifest_inbox
from utopia.optimization.native_nested_search import NativeNestedDesignCampaign, STAGES, COUNTS
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256, write_json_atomic

SCHEMA = 'scienceutopia.native-nested-search-pilot.v13'
ACTUAL = 'actual-native-qwen-nested-search-development-v13'
EXPERIMENT = {'protocol': 'native-nested-search-v13', 'role': 'development-engineering'}
SEED = 42
LOSS_NAMES = ('native-joint-v5-throughput.json', 'native-reviewed-production-efficiency-v13.json')
INSTRUCTIONS = (
    'Optimize only the supplied exact LossSpec. Preserve the original native researcher world, '
    'projects/papers/retrieval/resources and language decisions; fixed researcher Qwen weights do '
    'not imply fixed replies. Do not substitute numerical toy world laws. Freely author executable '
    'Python algorithms, mechanisms, protocols, ports, wires, schedules and activity dependency, '
    'guard and repetition processes using registered native capabilities. All institutional source '
    'runs in the existing pinned networkless sandbox, never as generated host functions. Existing '
    'evaluation/publication/funding are optional when explicit downstream contracts remain valid. '
    'Registered pre-review routing may explicitly choose native eligible reviewer tasks, including '
    'none. Legacy selection cannot consume unreviewed papers; such designs must explicitly author '
    'their own compatible selection source. The host never repairs missing selection, ports, '
    'protocols, process dependencies or reviewer tasks. '
    'The per-arm budget is G0 two IID native draws, exactly one LOO conditional likelihood-ratio '
    'update, one fresh forward-only draw from the exact resulting G0 vocabulary/weights, then '
    'external G1 free redesign and one forward-only native draw. G1 sees all three own prior '
    'observations, null failures and the saved update. It may replace source, support, coordinates '
    'and wiring, but must explicitly declare its own initial weights; no incompatible gradient or '
    'control state is transported implicitly. Use only own exact request/history, never another '
    'arm or future results. Parent is earliest exact best own complete observation, with all ties '
    'retained. Empty factor/coordinate lists and retention are legal. No forced novelty, quality, '
    'fairness or participation veto, hidden promotion policy or reward beyond the supplied loss. '
    'Invalid/null slots consume budget without numeric penalties, retries or replacement samples. '
    'New names/hashes alone are not useful invention. Source/LLM/world pathwise differentiation, '
    'estimator superiority, scientific value, generalization and improved designer are not claimed. '
    'External author provenance is self-reported, not provider-authenticated.'
)


def load_preregistered_losses(paths):
    losses = [load_loss_spec(path) for path in paths]
    expected = [load_loss_spec(ROOT / 'research/objectives/losses' / name) for name in LOSS_NAMES]
    if losses != expected:
        raise ValueError('v13 requires exact preregistered throughput/production-efficiency losses in order')
    return losses


def advance_arms(arms, campaigns, generators, *, simulation_factory, snapshot):
    waiting = {}
    for index, stage in enumerate(STAGES):
        for arm in arms:
            campaign = campaigns[arm]
            if arm in waiting or len(campaign.state['records']) > index:
                continue
            try:
                campaign.advance(simulation_factory=simulation_factory, generator=generators[arm])
            except ExternalAuthoringPending as error:
                waiting[arm] = error.to_dict()
            snapshot()
    return waiting


def summarize(output, plan, campaigns):
    output = Path(output)
    complete = failures = draws = slots = 0
    arms = {}
    for name, campaign in campaigns.items():
        arms[name] = {'binding': campaign.binding, 'records': campaign.state['records'],
            'pending': campaign.state['pending'],
            'authoring': audit_manifest_inbox(output / 'arms' / name / 'authoring')}
        for record in campaign.state['records']:
            slots += record['request']['count']
            if record['generation_error']:
                failures += record['request']['count']
            for draw, observation in zip(record['draws'], record['observations']):
                draws += 1
                valid = observation and observation['status'] == 'complete' and not observation['metadata'].get('technical_failures')
                complete += bool(valid)
                failures += not bool(valid)
    terminal = all(len(c.state['records']) == len(STAGES) and c.state['pending'] is None for c in campaigns.values())
    caches = []
    for path in sorted((output / 'worlds').glob('*/replies/responses.sqlite')):
        with sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True) as db:
            counts = dict(db.execute('SELECT outcome,COUNT(*) FROM replies GROUP BY outcome').fetchall())
        caches.append({'path': str(path.resolve()), 'sha256': file_sha256(path), 'outcomes': counts})
    replies = sum(c['outcomes'].get('response', 0) for c in caches)
    result = {'schema': SCHEMA, 'classification': plan['world']['classification'],
        'source_commit': plan['world']['source_commit'], 'plan': plan, 'budget_terminal': terminal,
        'status': 'complete' if terminal and complete == 8 and not failures else
            'budget-complete-with-failures' if terminal else 'in-progress',
        'planned_native_world_budget': 8, 'consumed_native_slots': slots, 'committed_draws': draws,
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
        raise ValueError('two distinct exact losses and safe arm IDs required')
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
        'stages': list(STAGES), 'stage_counts': list(COUNTS),
        'population': {'authors': 5, 'conference_setting': 1},
        'mode': 'free-vocabulary-LOO-update-forward-free-redesign-forward',
        'learning_rate': .1, 'initial_system': initial.to_dict(), 'instructions': INSTRUCTIONS,
        'scientific_benefit_required': False, 'structural_novelty_reward': False,
        'shared_physical_trajectories': False, 'external_designer_provider': 'self-reported Codex specialist'}
    path = args.output / 'plan.json'
    if path.exists() and json.loads(path.read_text()) != plan:
        raise ValueError('frozen nested native plan changed')
    if not path.exists():
        write_json_atomic(path, plan, sort_keys=True, allow_nan=False)
    campaigns = {arm: NativeNestedDesignCampaign(args.output / 'arms' / arm / 'campaign',
        initial_system=initial, loss_spec=loss, seeds=[SEED], world_binding=world,
        seed=SEED, learning_rate=.1) for arm, loss in zip(arms, losses)}
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
        'consumed_native_slots': evidence['consumed_native_slots'],
        'physical_reply_count': evidence['physical_reply_count'], 'content_sha256': evidence['content_sha256']}), flush=True)
    return 3 if waiting else 0 if evidence['status'] == 'complete' else 2


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--data-cache', type=Path, required=True)
    parser.add_argument('--inference-lock', type=Path,
        default=Path('/Users/shiro/unktok/dev/science-utopia-lab/outputs/native-parallel-v3-inference.lock'))
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
            raise RuntimeError('another nested native writer owns this output')
        return run(args)


if __name__ == '__main__':
    raise SystemExit(main())
