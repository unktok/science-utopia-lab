#!/usr/bin/env python3
"""Read-only, fail-closed audit of the actual native method-path v10 pilot."""
from __future__ import annotations

import argparse
from copy import deepcopy
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.analyze_native_qwen_response_v9 import (
    _audit_endpoint, inventory,
)
from utopia.optimization.loss import load_loss_spec, loss_spec_sha256
from utopia.optimization.native_method_paths import (
    ACTUAL, EXPERIMENT, GRADIENT_RULE, SCHEMA as RAW_SCHEMA, SCHEDULE,
    historical_observations, load_path_operator, load_shared_historical, read,
)
from utopia.optimization.native_path_policies import validate_state
from utopia.optimization.native_response_prefix import prepare_common_prefix
from utopia.system import SystemSpec
from utopia.system.design_patch import digest
from utopia.system.native_response_examples import DECLARATIONS, TERMS, response_gradient_system
from utopia.utils.data_utils import file_sha256, write_json_atomic

SCHEMA = 'scienceutopia.native-method-paths-audit.v10'
OBJECTIVE_PATH = ROOT/'research/objectives/losses/native-joint-v5-net-reviewed-utility.json'
PROTOCOL_PATH = ROOT/'research/protocols/campaigns/native-method-paths-v10.md'
SOURCE_PATHS = (
    'scripts/run_native_method_paths_v10.py',
    'scripts/analyze_native_qwen_response_v9.py',
    'utopia/optimization/native_method_paths.py',
    'utopia/optimization/native_path_policies.py',
    'utopia/optimization/native_qwen_response.py',
    'utopia/optimization/native_response_fidelity.py',
    'utopia/optimization/native_response_prefix.py',
    'utopia/optimization/native_hybrid.py',
    'utopia/optimization/native_relaxation.py',
    'utopia/system/native_response_examples.py',
    'utopia/system/native_review_context.py',
    'utopia/system/native_review_identity.py',
    'utopia/system/native_kernel.py',
    'utopia/system/native_tensor_examples.py',
    'utopia/system/tensor_program.py',
    'utopia/simulation.py',
    'utopia/models/models.py',
    'research/objectives/losses/native-joint-v5-net-reviewed-utility.json',
    'research/protocols/campaigns/native-method-paths-v10.md',
)


def _source_proof(expected_source):
    if not isinstance(expected_source, str) or len(expected_source) != 40:
        raise ValueError('full expected source commit required')
    result = {}
    for relative in SOURCE_PATHS:
        historical = subprocess.check_output(
            ['git', 'show', f'{expected_source}:{relative}'], cwd=ROOT)
        current = (ROOT/relative).read_bytes()
        if historical != current:
            raise ValueError('current scientific/method source differs from experiment: '+relative)
        result[relative] = hashlib.sha256(current).hexdigest()
    return result


def _validate_plan(plan, expected_source):
    objective = load_loss_spec(OBJECTIVE_PATH)
    world = plan.get('world', {})
    if (plan.get('schema') != RAW_SCHEMA or plan.get('classification') != ACTUAL
            or world.get('source_commit') != expected_source
            or world.get('classification') != ACTUAL or world.get('experiment') != EXPERIMENT
            or world.get('seed') != 42 or world.get('years') != 2 or world.get('corpus_years') != 4
            or plan.get('population') != {'authors': 5, 'institutions': 5}
            or plan.get('loss_spec') != objective or plan.get('declarations') != DECLARATIONS
            or plan.get('terms') != TERMS or plan.get('schedule') != SCHEDULE
            or plan.get('fresh_budget_per_arm') != 3 or plan.get('initial_current_theta') != .5
            or plan.get('domain') != [.2, .8]
            or plan.get('method_configs') != {'gradient': GRADIENT_RULE,
                'blackbox': {'rule': 'incumbent-adjacent widest-interval bisection; lower interval and earliest observation ties'}}
            or plan.get('protocol_sha256') != file_sha256(PROTOCOL_PATH)
            or not isinstance(plan.get('image_id'), str) or not plan['image_id']
            or not isinstance(world.get('runtime_seed_binding'), dict)
            or not all(isinstance(world.get(k), str) and len(world[k]) == 64
                       for k in ('model_digest', 'corpus_sha256'))):
        raise ValueError('fixed v10 plan/objective/world/method budget differs')
    base = response_gradient_system(plan['image_id'])
    if plan.get('system') != base.to_dict():
        raise ValueError('fixed response-gradient native system differs')
    shared = load_shared_historical(plan['shared_historical']['audit_path'])
    if shared != plan.get('shared_historical'):
        raise ValueError('shared historical receipt/raw inventory differs')
    coupling = plan.get('response_coupling', {})
    if (coupling.get('mode') != 'actual-common-prefix-replay'
            or coupling.get('unique_anchor_prefix_calls') != 53
            or coupling.get('prepared', {}).get('prefix_count') != 53
            or coupling['prepared'].get('anchor_endpoint') != shared['anchor_endpoint']):
        raise ValueError('common-prefix plan differs from exact historical anchor')
    reconstructed = prepare_common_prefix(shared['anchor_world_dir'], shared['anchor_endpoint'])
    if coupling['prepared'] != reconstructed:
        raise ValueError('complete common-prefix manifest does not reconstruct from unchanged anchor raw')
    return objective, base, world, shared, coupling


def _physical_ledger(root, completed_names, world, coupling):
    """Count every v10 logical/fresh response without v9 name globals."""
    declared = {item['name'] for item in SCHEDULE}
    worlds = root/'worlds'
    directories = sorted(p for p in worlds.iterdir() if p.is_dir()) if worlds.exists() else []
    if any(path.name not in declared for path in directories):
        raise ValueError('undeclared v10 physical world directory exists')
    ledger = []
    for cell in directories:
        journal, wire_path = cell/'replies/responses.sqlite', cell/'wire-requests.jsonl'
        if not journal.exists():
            ledger.append({'name': cell.name, 'status': 'partial-before-response-journal',
                'loss': None, 'response_count': 0, 'logical_response_count': 0,
                'fresh_physical_reply_count': 0, 'replayed_response_count': 0,
                'outcomes': {}, 'journal_sha256': None})
            continue
        if not wire_path.is_file():
            raise ValueError(f'{cell.name}: response journal lacks wire provenance')
        before = file_sha256(journal)
        with sqlite3.connect(journal.resolve().as_uri()+'?mode=ro', uri=True) as db:
            metadata = db.execute('SELECT binding FROM metadata').fetchall()
            outcomes = dict(db.execute('SELECT outcome,COUNT(*) FROM replies GROUP BY outcome').fetchall())
            rows = db.execute('SELECT rowid,identity,payload_sha,outcome,data,data_sha FROM replies ORDER BY rowid').fetchall()
        wires = [json.loads(line) for line in wire_path.read_text().splitlines()]
        binding = json.loads(metadata[0][0]) if len(metadata) == 1 else {}
        sha = lambda value: isinstance(value, str) and len(value) == 64 and all(c in '0123456789abcdef' for c in value)
        if (len(metadata) != 1 or file_sha256(journal) != before
                or binding.get('seed') != world['seed']
                or binding.get('model_revision') != world['model_digest']
                or binding.get('corpus_sha256') != world['corpus_sha256']
                or binding.get('science_config', {}).get('source_commit') != world['source_commit']
                or len(rows) != sum(outcomes.values()) or len(rows) != len(wires)
                or any(not sha(row[1]) or not sha(row[2]) or not sha(row[5])
                    or hashlib.sha256(row[4].encode()).hexdigest() != row[5] for row in rows)
                or any(row[3] not in {'response','error'} for row in rows)
                or [row[2] for row in rows] != [wire.get('payload_sha256') for wire in wires]):
            raise ValueError(f'{cell.name}: physical response binding/rows differ')
        replayed = sum('replayed_from' in wire for wire in wires)
        if (replayed != coupling['prepared']['prefix_count'] and cell.name in completed_names
                or any('replayed_from' not in wire for wire in wires[:replayed])
                or any('replayed_from' in wire for wire in wires[replayed:])):
            raise ValueError(f'{cell.name}: replay rows are not one exact declared prefix')
        logical = outcomes.get('response', 0); fresh = logical-replayed
        if fresh < 0:
            raise ValueError(f'{cell.name}: replay count exceeds logical replies')
        completed = cell.name in completed_names
        ledger.append({'name': cell.name, 'status': 'completed-endpoint' if completed else 'partial-null-loss-world',
            'loss': 'reported-in-endpoint-ledger' if completed else None,
            'response_count': logical, 'logical_response_count': logical,
            'fresh_physical_reply_count': fresh, 'replayed_response_count': replayed,
            'outcomes': outcomes, 'journal_sha256': before, 'binding_sha256': digest(binding),
            'row_identity_sha256': digest(rows)})
    completed = [row for row in ledger if row['status'] == 'completed-endpoint']
    partial = [row for row in ledger if row['status'] != 'completed-endpoint']
    return {'worlds': ledger,
        'completed_endpoint_replies': sum(r['logical_response_count'] for r in completed),
        'partial_null_loss_replies': sum(r['logical_response_count'] for r in partial),
        'completed_endpoint_fresh_physical_replies': sum(r['fresh_physical_reply_count'] for r in completed),
        'partial_null_loss_fresh_physical_replies': sum(r['fresh_physical_reply_count'] for r in partial),
        'all_logical_replies': sum(r['logical_response_count'] for r in ledger),
        'all_replayed_replies': sum(r['replayed_response_count'] for r in ledger),
        'all_fresh_physical_replies': sum(r['fresh_physical_reply_count'] for r in ledger)}


def _sequence(raw, require_complete):
    rows, steps, failures = raw.get('endpoints'), raw.get('steps'), raw.get('failures')
    if not isinstance(rows, list) or not isinstance(steps, list) or not isinstance(failures, list):
        raise ValueError('method path arrays absent')
    if require_complete:
        if raw.get('status') != 'complete' or failures or len(rows) != 6 or len(steps) != 6:
            raise ValueError('complete audit requires all six fresh attempts and no failures')
    elif raw.get('status') not in ('complete', 'stopped-with-preserved-failure'):
        raise ValueError('partial audit requires terminal preserved status')
    expected = SCHEDULE[:len(steps)]
    if [{k: step.get(k) for k in ('arm','step','name')} for step in steps] != expected:
        raise ValueError('frozen proposal schedule/order differs')
    if [{k: row.get(k) for k in ('arm','step','name')} for row in rows] != SCHEDULE[:len(rows)]:
        raise ValueError('physical endpoint schedule/order differs')
    if len(rows) > len(steps) or any(f.get('loss', 'not-null') is not None for f in failures):
        raise ValueError('endpoint/failure accounting differs or technical failure became loss')
    return rows, steps, failures


def _audit_steps(root, raw, shared, objective):
    rows, steps = raw['endpoints'], raw['steps']
    by_arm = {'gradient': [], 'blackbox': []}
    operator_receipts = []
    for position, frozen in enumerate(steps):
        item = SCHEDULE[position]
        path = root/'proposals'/f"{item['name']}.json"
        saved = read(path)
        if saved != frozen:
            raise ValueError('proposal file/evidence receipt differs')
        proposal = frozen.get('proposal', {})
        if proposal.get('sequence') != item['step'] or proposal.get('method') != (
                'represented-gradient' if item['arm'] == 'gradient' else 'blackbox'):
            raise ValueError('proposal method/sequence differs')
        if position < len(rows):
            row = rows[position]
            if (row.get('proposal_sha256') != proposal.get('content_sha256')
                    or row.get('theta') != proposal.get('candidate_theta')
                    or row.get('observation', {}).get('loss') != row.get('endpoint', {}).get('native_loss')):
                raise ValueError('proposal/physical observation join differs')
        operator_record = frozen.get('operator')
        if item['arm'] == 'gradient':
            eligible = shared['rows'] + by_arm['gradient']
            expected_shas = [r['endpoint']['checkpoint_sha256'] for r in eligible]
            operator_path = root/'operators'/f"{item['name']}.json"
            if (operator_record != {'path': str(operator_path),
                    'file_sha256': file_sha256(operator_path),
                    'representation_sha256': read(operator_path)['representation_sha256'],
                    'eligible_endpoint_sha256s': expected_shas}):
                raise ValueError('gradient operator eligible history/file receipt differs')
            operator = load_path_operator(operator_path, eligible, objective,
                GRADIENT_RULE['temperature_schedule'][item['step']], ROOT)
            backward = proposal.get('backward')
            expected_backward = {**operator.backward([proposal['current_theta']]),
                'temperature': GRADIENT_RULE['temperature_schedule'][item['step']]}
            if backward != expected_backward or operator._hash != operator_record['representation_sha256']:
                raise ValueError('scheduled represented backward does not reconstruct')
            operator_receipts.append({'name': item['name'], **operator_record,
                'backward': deepcopy(backward)})
        elif operator_record is not None or proposal.get('backward') is not None:
            raise ValueError('blackbox proposal consumed an operator/gradient')
        if position < len(rows):
            by_arm[item['arm']].append(rows[position])
    return operator_receipts


def _audit_policies(root, raw, shared, objective, world):
    result = {}
    for arm in ('gradient', 'blackbox'):
        state = validate_state(read(root/'policies'/f'{arm}.json'))
        completed = {row['name']: row for row in raw['endpoints'] if row['arm'] == arm}
        failures = {row['name']: row for row in raw['failures'] if row['arm'] == arm}
        expected_proposals = [step['proposal'] for step in raw['steps'] if step['arm'] == arm]
        if (len(state['events']) != len(expected_proposals) or state['pending'] is not None
                or state['historical'] != historical_observations(shared)
                or state['loss_spec_sha256'] != loss_spec_sha256(objective)
                or state['world_binding'] != world):
            raise ValueError('durable policy state does not match exact evidence history')
        for event, proposal in zip(state['events'], expected_proposals):
            name = f"{arm}-{proposal['sequence']}"
            observation = event['observation']
            if event['proposal'] != proposal:
                raise ValueError('policy proposal differs from frozen evidence')
            if name in completed:
                if observation != completed[name]['observation']:
                    raise ValueError('policy observation differs from completed endpoint')
            elif (name not in failures or observation.get('status') != 'technical-failure'
                    or observation.get('loss') is not None or observation.get('error') != failures[name]
                    or observation.get('theta') != proposal['candidate_theta']):
                raise ValueError('policy terminal failure differs from preserved null evidence')
        result[arm] = state
    return result


def _arm_summary(arm, rows, historical):
    observations = [{'origin': 'shared-historical', 'name': r['name'], 'theta': r['theta'],
        'loss': r['endpoint']['native_loss']} for r in historical]
    incumbent = min(observations, key=lambda row: row['loss'])
    incumbent_path, current_path = [], []
    for row in rows:
        point = {'origin': 'fresh', 'name': row['name'], 'theta': row['theta'],
            'loss': row['endpoint']['native_loss']}
        observations.append(point)
        if point['loss'] < incumbent['loss']:
            incumbent = point
        incumbent_path.append(deepcopy(incumbent))
        current_path.append({'name': row['name'], 'theta': row['theta'], 'loss': point['loss']})
    fresh_best = min(current_path, key=lambda row: row['loss']) if current_path else None
    center_loss = historical[1]['endpoint']['native_loss']
    historical_best = min(r['endpoint']['native_loss'] for r in historical)
    return {'arm': arm, 'historical_observations_charged': 3,
        'fresh_attempts': len(rows), 'observations': observations,
        'current_path': current_path, 'incumbent_path': incumbent_path,
        'fresh_best': fresh_best,
        'best_fresh_minus_initial_center': None if fresh_best is None else fresh_best['loss']-center_loss,
        'best_fresh_minus_best_historical': None if fresh_best is None else fresh_best['loss']-historical_best,
        'final_incumbent': deepcopy(incumbent)}


def analyze(run, *, expected_source, require_complete=True):
    root = Path(run).resolve()
    before = inventory(root)
    try:
        plan, raw = read(root/'plan.json'), read(root/'evidence.json')
        embedded_plan = {k: v for k, v in plan.items() if k != 'content_sha256'}
        if (raw.get('schema') != RAW_SCHEMA or raw.get('classification') != ACTUAL
                or raw.get('source_commit') != expected_source or raw.get('plan') != embedded_plan):
            raise ValueError('raw evidence source/schema/plan differs')
        claims = raw.get('claims', {})
        if claims != {'actual_fixed_weight_Qwen': True, 'exact_Qwen_Jacobian': False,
                'full_native_world_autograd': False, 'held_out_seeds': False,
                'optimizer_superiority': False, 'causal_scientific_benefit': False}:
            raise ValueError('claim boundary differs')
        sources = _source_proof(expected_source)
        objective, base, world, shared, coupling = _validate_plan(plan, expected_source)
        rows, steps, failures = _sequence(raw, require_complete)
        coupling_arg = {'mode': coupling['mode'], 'prepared': coupling['prepared']}
        proofs = [_audit_endpoint(root, row, base_system=base, declarations=DECLARATIONS,
            objective=objective, world=world, coupling=coupling_arg) for row in rows]
        physical = _physical_ledger(root, {r['name'] for r in rows}, world, coupling_arg)
        operators = _audit_steps(root, raw, shared, objective)
        policies = _audit_policies(root, raw, shared, objective, world)
        if require_complete and (raw.get('physical_native_worlds') != 6
                or raw.get('physical_reply_count') != physical['all_fresh_physical_replies']
                or raw.get('logical_response_count') != physical['all_logical_replies']
                or raw.get('replayed_response_count') != physical['all_replayed_replies']):
            raise ValueError('completed aggregate physical/logical counters differ')
        compact = [{k: proof[k] for k in ('name','theta','native_loss','hard_represented_loss',
            'checkpoint_sha256','system_fingerprint','response_count','fresh_physical_reply_count',
            'replayed_response_count','review_reply_count','objective_measurements','raw_projection_sha256',
            'journal_sha256','wire_sha256','completion_receipt_sha256','run_manifest_sha256')}
            | {'arm': row['arm'], 'step': row['step'], 'proposal_sha256': row['proposal_sha256'],
               'observation': deepcopy(row['observation']),
               'common_prefix_proof': deepcopy(proof['common_prefix_proof'])}
            for row, proof in zip(rows, proofs)]
        arms = {arm: _arm_summary(arm, [r for r in rows if r['arm'] == arm], shared['rows'])
                for arm in ('gradient', 'blackbox')}
        report = {'schema': SCHEMA, 'classification': ACTUAL,
            'status': 'complete' if len(rows) == 6 and not failures else 'valid-preserved-partial-failure',
            'source_commit': expected_source, 'raw_output_root': str(root),
            'objective': {'role': 'optimization-loss', 'loss_spec': objective,
                'hard_loss_replayed_for_every_completed_world': True},
            'technical_validity': {'completed_worlds': len(rows), 'planned_fresh_worlds': 6,
                'failures': deepcopy(failures), 'schedule_verified': True,
                'all_completed_checkpoints_remeasured': True,
                'all_policy_decisions_replayed': True},
            'shared_historical': {k: deepcopy(v) for k, v in shared.items() if k != 'rows'} |
                {'rows': [{'name': r['name'], 'theta': r['theta'],
                    'native_loss': r['endpoint']['native_loss'],
                    'checkpoint_sha256': r['endpoint']['checkpoint_sha256']} for r in shared['rows']]},
            'schedule': deepcopy(SCHEDULE), 'endpoints': compact,
            'operators': operators,
            'policy_state_sha256s': {arm: state['content_sha256'] for arm, state in policies.items()},
            'arms': arms,
            'comparison': {'scope': 'single common-prefix-coupled development path; descriptive only',
                'equal_fresh_native_attempt_budget': 3,
                'optimizer_superiority_claim': False, 'optimality_claim': False,
                'held_out_or_replication_claim': False},
            'physical_reply_count': physical['all_fresh_physical_replies'],
            'logical_response_count': physical['all_logical_replies'],
            'replayed_response_count': physical['all_replayed_replies'],
            'physical_response_ledger': physical['worlds'],
            'source_proof': {'current_method_and_scientific_sources_match_experiment_commit': True,
                'module_sha256s': sources},
            'raw_hashes': {'plan_file_sha256': file_sha256(root/'plan.json'),
                'evidence_file_sha256': file_sha256(root/'evidence.json'),
                'evidence_content_sha256': raw.get('content_sha256'),
                'inventory_sha256': digest(before), 'file_count': len(before), 'files': before},
            'held_out_metrics': {'status': 'not-measured'},
            'promotion_policy': {'status': 'not-defined-or-applied'},
            'claims': {'new_model_calls': 0, 'new_native_worlds': 0,
                'actual_fixed_weight_Qwen': True, 'exact_Qwen_Jacobian': False,
                'full_native_world_autograd': False, 'optimizer_superiority': False,
                'causal_scientific_benefit': False}}
        report['content_sha256'] = digest(report)
        return report
    finally:
        if inventory(root) != before:
            raise ValueError('raw evidence changed during read-only audit')


def markdown_summary(report):
    lines = ['# Native method paths v10 independent audit', '',
        f"- Status: `{report['status']}`", f"- Source: `{report['source_commit']}`",
        f"- Content SHA-256: `{report['content_sha256']}`",
        f"- Fresh/logical/replayed responses: {report['physical_reply_count']} / {report['logical_response_count']} / {report['replayed_response_count']}", '',
        '| arm | step | theta | native loss |', '|---|---:|---:|---:|']
    for row in report['endpoints']:
        lines.append(f"| {row['arm']} | {row['step']} | {row['theta']:.9g} | {row['native_loss']:.9g} |")
    lines += ['', 'Both methods are charged the same three shared historical observations and three fresh native attempts.',
        'This is one common-prefix-coupled development path, not held-out evidence, independent replication, optimizer superiority or optimality.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--expected-source', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--markdown', type=Path)
    parser.add_argument('--allow-incomplete', action='store_true')
    args = parser.parse_args()
    report = analyze(args.run, expected_source=args.expected_source,
        require_complete=not args.allow_incomplete)
    write_json_atomic(args.output, report, sort_keys=True, allow_nan=False)
    if args.markdown:
        args.markdown.write_text(markdown_summary(report))
    print(json.dumps({'status': report['status'], 'worlds': report['technical_validity']['completed_worlds'],
        'fresh_replies': report['physical_reply_count'], 'content_sha256': report['content_sha256']}, sort_keys=True))


if __name__ == '__main__':
    main()
