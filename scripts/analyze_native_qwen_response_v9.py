#!/usr/bin/env python3
"""Read-only audit of the bounded actual-Qwen response-gradient v9 pilot.

The auditor never starts a simulator, model, generated source, or container. It
remeasures completed checkpoints, reconstructs the calibration-only response
operator, and preserves an unsuccessful candidate or a stopped partial attempt.
Optimization loss, technical validity, held-out metrics, and promotion policy
are reported as separate concepts.
"""
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

from utopia.optimization.loss import load_loss_spec
from utopia.optimization.native_hybrid import native_endpoint, project_continuous
from utopia.optimization.native_qwen_response import control_proof, gradient_proposal, require_same_control
from utopia.optimization.native_relaxation import replay_tensor_trace, trace_objective
from utopia.optimization.native_response_fidelity import (
    NativeResponseOperator,
    boundary_layout,
    endpoint_decomposition,
    programs,
    raw_review_projection,
)
from utopia.system import SystemSpec
from utopia.system.design_patch import digest
from utopia.system.native_response_examples import DECLARATIONS, TERMS, response_gradient_system
from utopia.utils.data_utils import file_sha256, write_json_atomic

RAW_SCHEMA = 'scienceutopia.native-qwen-response-loop.v9'
SCHEMA = 'scienceutopia.native-qwen-response-audit.v9'
ACTUAL = 'actual-native-qwen-response-gradient-development-v9'
EXPERIMENT = {'protocol': 'native-qwen-response-gradient-v9', 'role': 'development-engineering',
    'review_task_identity_recording': True, 'public_payload_only_review_context': True}
CALIBRATION = [.2, .5, .8]
UNUSED = [.35, .65]
FIXED_NAMES = ('calibration-0', 'calibration-1', 'calibration-2',
               'unused-0', 'unused-1', 'gradient-candidate')
OBJECTIVE_PATH = ROOT / 'research/objectives/losses/native-joint-v5-net-reviewed-utility.json'
PROTOCOL_PATH = ROOT / 'research/protocols/campaigns/native-qwen-response-gradient-v9.md'
AMENDMENT_ID = 'native-qwen-response-gradient-v9-a2'
AMENDMENT_PATH = ROOT / 'research/protocols/campaigns/native-qwen-response-gradient-v9-a2.md'
SOURCE_PATHS = (
    'utopia/optimization/native_qwen_response.py',
    'utopia/optimization/native_response_fidelity.py',
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
    'research/protocols/campaigns/native-qwen-response-gradient-v9.md',
)


def _sha256(value):
    return (isinstance(value, str) and len(value) == 64
            and all(character in '0123456789abcdef' for character in value))


def read(path):
    value = json.loads(Path(path).read_text())
    if ('content_sha256' in value
            and value['content_sha256'] != digest({k: v for k, v in value.items()
                                                   if k != 'content_sha256'})):
        raise ValueError(f'content hash differs: {path}')
    return value


def inventory(root):
    root = Path(root)
    result = {}
    for path in sorted(root.rglob('*')):
        if path.is_symlink():
            raise ValueError('raw evidence cannot contain symlinks')
        if path.is_file():
            result[str(path.relative_to(root))] = {
                'sha256': file_sha256(path), 'bytes': path.stat().st_size}
    return result


def source_proof(expected_source, *, include_amendment=False):
    """Bind active scientific/comparator bytes to the experiment commit.

    The auditor itself is intentionally allowed to be a later addition. The
    modules that interpret raw evidence are not: current analysis code cannot
    silently reinterpret an old run under new scientific/comparator semantics.
    """
    paths = SOURCE_PATHS + ((str(AMENDMENT_PATH.relative_to(ROOT)),)
                            if include_amendment else ())
    result = {}
    for relative in paths:
        try:
            historical = subprocess.check_output(
                ['git', 'show', f'{expected_source}:{relative}'], cwd=ROOT)
        except subprocess.CalledProcessError as error:
            raise ValueError(f'expected source lacks required analysis module: {relative}') from error
        current_path = ROOT / relative
        if not current_path.is_file():
            raise ValueError(f'current analysis tree lacks required source: {relative}')
        current = current_path.read_bytes()
        if current != historical:
            raise ValueError(f'current analysis source differs from experiment pin: {relative}')
        result[relative] = hashlib.sha256(current).hexdigest()
    return result


def _validate_amendment(plan, expected_amendment):
    amendment = plan.get('amendment')
    if expected_amendment is None:
        if amendment is not None:
            raise ValueError('amended run requires an explicit expected amendment')
        return None
    if expected_amendment != AMENDMENT_ID or not AMENDMENT_PATH.is_file():
        raise ValueError('unknown or unavailable response-gradient amendment')
    expected = {'id': AMENDMENT_ID, 'sha256': file_sha256(AMENDMENT_PATH),
        'prior_maximum_worlds': 3, 'maximum_combined_physical_worlds': 9,
        'changes': ('exclude only server envelope metadata from cross-world '
                    'semantic response equality')}
    if amendment != expected:
        raise ValueError('prospective a2 amendment ID/hash/combined budget differs')
    return deepcopy(expected)


def _fixed_plan(plan, expected_source):
    objective = load_loss_spec(OBJECTIVE_PATH)
    world = plan.get('world', {})
    if (plan.get('schema') != RAW_SCHEMA or plan.get('classification') != ACTUAL
            or world.get('classification') != ACTUAL
            or world.get('source_commit') != expected_source
            or world.get('experiment') != EXPERIMENT
            or world.get('seed') != 42 or world.get('years') != 2
            or world.get('corpus_years') != 4
            or not _sha256(world.get('model_digest'))
            or not _sha256(world.get('corpus_sha256'))
            or not isinstance(world.get('runtime_seed_binding'), dict)
            or plan.get('population') != {'authors': 5, 'institutions': 5}
            or plan.get('loss_spec') != objective
            or plan.get('declarations') != DECLARATIONS or plan.get('terms') != TERMS
            or plan.get('calibration') != CALIBRATION or plan.get('unused') != UNUSED
            or plan.get('maximum_native_worlds') != 6
            or plan.get('temperatures') != [1., .2, .05, .01]
            or plan.get('candidate_rule') != ('center point .5, lr .02, displacement clamp '
                                               '+/-.10, support [.2,.8]')
            or plan.get('protocol_sha256') != file_sha256(PROTOCOL_PATH)):
        raise ValueError('frozen v9 source/objective/world/budget plan differs')
    expected_system = response_gradient_system(plan['image_id']).to_dict()
    if plan.get('system') != expected_system:
        raise ValueError('frozen v9 institutional system differs from pinned source')
    return objective, SystemSpec.from_dict(expected_system), world


def _endpoint_sequence(raw, *, require_complete):
    endpoints, failures = raw.get('endpoints'), raw.get('failures')
    if not isinstance(endpoints, list) or not isinstance(failures, list):
        raise ValueError('endpoint/failure ledgers are absent')
    names = [row.get('name') for row in endpoints]
    if names != list(FIXED_NAMES[:len(names)]) or len(names) > 6:
        raise ValueError('endpoint ledger is not the unique preregistered prefix')
    if any(not isinstance(row, dict) for row in endpoints):
        raise ValueError('endpoint ledger row is invalid')
    expected_thetas = CALIBRATION + UNUSED
    for index, row in enumerate(endpoints[:5]):
        if row.get('theta') != expected_thetas[index]:
            raise ValueError('fixed calibration/unused coordinate differs')
    if failures:
        if raw.get('status') != 'stopped-with-preserved-failure' or len(failures) != 1:
            raise ValueError('failure is not retained as one terminal stopped attempt')
        failure = failures[0]
        next_name = FIXED_NAMES[len(endpoints)] if len(endpoints) < 6 else None
        if (failure.get('loss', 'not-null') is not None
                or failure.get('name', next_name) != next_name):
            raise ValueError('failed world was converted to a loss or attached to another slot')
    elif raw.get('status') not in {'in-progress', 'complete'}:
        raise ValueError('raw status differs from endpoint/failure ledger')
    complete = raw.get('status') == 'complete'
    if complete != (len(endpoints) == 6 and not failures):
        raise ValueError('complete status does not mean exactly six successful worlds')
    if require_complete and not complete:
        raise ValueError('actual v9 pilot is not complete; use --allow-incomplete for a partial receipt')
    if not complete and not failures:
        raise ValueError('in-progress writer output is not a terminal auditable partial attempt')
    return endpoints, failures, complete


def _safe_endpoint_paths(root, name, row):
    cell = (root / 'worlds' / name).resolve()
    checkpoint = cell / 'simulation/checkpoints/native-design/portable_checkpoint_year_2.json.gz'
    contexts = cell / 'code-contexts.jsonl'
    journal = cell / 'replies/responses.sqlite'
    wire = cell / 'wire-requests.jsonl'
    receipt = cell / 'completion-receipt.json'
    manifest = cell / 'simulation/docs/native-design/run_manifest.json'
    evidence = row.get('numeric_response_evidence', {})
    expected_evidence = {'journal': str(journal), 'wire': str(wire),
        'mechanism': 'addressed-selection', 'input_name': 'features',
        'completion_receipt': row.get('completion_receipt')}
    if evidence != expected_evidence:
        raise ValueError(f'{name}: response evidence escapes or differs from its physical cell')
    for path in (checkpoint, contexts, journal, wire, receipt, manifest):
        if not path.is_file() or not path.is_relative_to(cell):
            raise ValueError(f'{name}: required physical evidence is absent')
    return cell, checkpoint, contexts, journal, wire, receipt, manifest


def _audit_endpoint(root, row, *, base_system, declarations, objective, world):
    name, theta = row['name'], row['theta']
    candidate, projection = project_continuous(base_system, declarations, {'evidence-weight': theta})
    if row.get('projection') != projection:
        raise ValueError(f'{name}: exact institutional projection differs')
    cell, checkpoint, contexts, journal, wire, receipt_path, manifest = _safe_endpoint_paths(root, name, row)
    endpoint = native_endpoint(checkpoint, candidate, declarations, objective,
        world=world, code_contexts=contexts)
    if endpoint != row.get('endpoint'):
        raise ValueError(f'{name}: stored endpoint differs from independent checkpoint measurement')
    hard = float(trace_objective(replay_tensor_trace(endpoint['trace'], programs(endpoint),
        hard=True, verify_recorded=True), TERMS))
    if (not math.isclose(hard, endpoint['native_loss'], rel_tol=0., abs_tol=1e-10)
            or not math.isclose(hard, row.get('hard_represented_loss', math.nan),
                                rel_tol=0., abs_tol=1e-10)):
        raise ValueError(f'{name}: fixed hard objective does not replay')
    proof = control_proof(endpoint, cell)
    if proof != row.get('control_proof'):
        raise ValueError(f'{name}: control proof differs')
    receipt = read(receipt_path)
    if (receipt != row.get('completion_receipt')
            or receipt.get('run_manifest_sha256') != file_sha256(manifest)
            or receipt.get('timing_authenticated') is not False):
        raise ValueError(f'{name}: completion receipt differs or overstates timing')
    layout, numeric, _ = boundary_layout(endpoint)
    _, response = raw_review_projection(endpoint, layout, numeric,
        journal=journal, wire=wire, mechanism='addressed-selection', input_name='features',
        completion_receipt=receipt)
    if (endpoint['response_cache_count'] != row.get('fresh_physical_replies')
            or response['checkpoint_response_count'] != row.get('fresh_physical_replies')):
        raise ValueError(f'{name}: full physical reply count differs')
    metrics = endpoint['measurement']['metrics']
    objective_metrics = {}
    for key in ('native.accepted_decisions', 'native.accepted_peer_score_sum',
                'native.review_records'):
        value = metrics.get(key)
        if (not isinstance(value, dict) or value.get('status') != 'measured'
                or type(value.get('value')) not in (int, float)
                or not math.isfinite(value['value'])):
            raise ValueError(f'{name}: fixed objective constituent {key} is unavailable')
        objective_metrics[key] = value['value']
    return {'name': name, 'theta': theta, 'native_loss': endpoint['native_loss'],
        'hard_represented_loss': hard, 'checkpoint_sha256': endpoint['checkpoint_sha256'],
        'initial_checkpoint_sha256': endpoint['initial_checkpoint_sha256'],
        'system_fingerprint': endpoint['system_fingerprint'],
        'physical_initial_identity': endpoint['physical_initial_identity'],
        'noncoordinate_system_sha256': endpoint['noncoordinate_system_sha256'],
        'response_count': endpoint['response_cache_count'],
        'objective_measurements': objective_metrics,
        'review_reply_count': sum(item['actual_replies'] for item in response['cohorts']),
        'review_cohorts': response['cohorts'],
        'raw_projection_sha256': digest(response),
        'journal_sha256': response['journal_sha256'], 'wire_sha256': response['wire_sha256'],
        'code_contexts_sha256': endpoint['code_contexts_sha256'],
        'completion_receipt_sha256': receipt['content_sha256'],
        'run_manifest_sha256': receipt['run_manifest_sha256'],
        'control_proof': proof, 'endpoint': endpoint}


def _physical_response_ledger(root, completed_names, world):
    """Count every durable actual response, including null-loss partial worlds."""
    worlds = root / 'worlds'
    directories = sorted(path for path in worlds.iterdir() if path.is_dir()) if worlds.exists() else []
    if any(path.name not in FIXED_NAMES for path in directories):
        raise ValueError('undeclared physical response world directory exists')
    ledger = []
    for cell in directories:
        journal = cell / 'replies/responses.sqlite'
        if not journal.exists():
            ledger.append({'name': cell.name, 'status': 'partial-before-response-journal',
                'loss': None, 'response_count': 0, 'outcomes': {}, 'journal_sha256': None})
            continue
        before = file_sha256(journal)
        with sqlite3.connect(journal.resolve().as_uri()+'?mode=ro', uri=True) as db:
            metadata = db.execute('SELECT binding FROM metadata').fetchall()
            outcomes = dict(db.execute(
                'SELECT outcome,COUNT(*) FROM replies GROUP BY outcome').fetchall())
            rows = db.execute('SELECT payload_sha,outcome,data_sha FROM replies ORDER BY rowid').fetchall()
        if len(metadata) != 1 or file_sha256(journal) != before:
            raise ValueError(f'{cell.name}: physical response journal changed or lacks one binding')
        binding = json.loads(metadata[0][0])
        if (binding.get('seed') != world['seed']
                or binding.get('model_revision') != world['model_digest']
                or binding.get('corpus_sha256') != world['corpus_sha256']
                or binding.get('science_config', {}).get('source_commit') != world['source_commit']
                or len(rows) != sum(outcomes.values())
                or any(not _sha256(row[0]) or not _sha256(row[2]) for row in rows)
                or any(row[1] not in {'response', 'error'} for row in rows)):
            raise ValueError(f'{cell.name}: partial/full physical response binding or rows differ')
        completed = cell.name in completed_names
        ledger.append({'name': cell.name,
            'status': 'completed-endpoint' if completed else 'partial-null-loss-world',
            'loss': 'reported-in-endpoint-ledger' if completed else None,
            'response_count': outcomes.get('response', 0), 'outcomes': outcomes,
            'journal_sha256': before, 'binding_sha256': digest(binding),
            'row_identity_sha256': digest(rows)})
    completed = sum(row['response_count'] for row in ledger if row['status'] == 'completed-endpoint')
    partial = sum(row['response_count'] for row in ledger if row['status'] != 'completed-endpoint')
    return {'worlds': ledger, 'completed_endpoint_replies': completed,
        'partial_null_loss_replies': partial, 'all_fresh_physical_replies': completed+partial}


def _operator_reconstruction(root, rows, proofs, raw, objective):
    calibration_rows, calibration_proofs = rows[:3], proofs[:3]
    endpoints = [p['endpoint'] for p in calibration_proofs]
    fit_evidence = {p['checkpoint_sha256']: r['numeric_response_evidence']
                    for r, p in zip(calibration_rows, calibration_proofs)}
    if set(fit_evidence) != {p['checkpoint_sha256'] for p in calibration_proofs}:
        raise ValueError('operator fit evidence is not exactly three calibration checkpoints')
    operator_path = root / 'response-operator.json'
    operator = NativeResponseOperator.fit(endpoints, DECLARATIONS, objective, TERMS,
        temperatures=[1., .2, .05, .01], numeric_response_evidence=fit_evidence)
    saved = NativeResponseOperator.load(operator_path)
    if operator.state != saved.state or operator._hash != saved._hash:
        raise ValueError('saved operator differs from exact calibration-only refit')
    if (operator.state['calibration'] != endpoints
            or operator.state['numeric_response_evidence'] != fit_evidence
            or operator.state['temperature_selection']['unused_endpoints_seen'] != 0
            or operator.state['temperature_selection']['calibration_checkpoint_sha256s']
                != [p['checkpoint_sha256'] for p in calibration_proofs]):
        raise ValueError('operator contains undeclared non-calibration outcomes')
    backward = operator.backward([.5])
    proposal = gradient_proposal(backward)
    frozen = read(root / 'frozen-proposal.json')
    expected = {'schema': RAW_SCHEMA+'.frozen-proposal', 'backward': backward,
        'proposal': proposal, 'operator_file_sha256': file_sha256(operator_path),
        'temperature_selection': operator.state['temperature_selection'],
        'calibration_checkpoint_sha256s': [p['checkpoint_sha256'] for p in calibration_proofs],
        'unused_outcomes_seen': 0}
    if frozen != {**expected, 'content_sha256': digest(expected)}:
        raise ValueError('frozen proposal does not reconstruct before unused outcomes')
    if raw.get('frozen_proposal') != frozen:
        raise ValueError('evidence does not bind the exact frozen proposal')
    return operator, backward, proposal, frozen


def _complete_reconstruction(root, rows, proofs, raw, objective):
    operator, backward, proposal, frozen = _operator_reconstruction(root, rows, proofs, raw, objective)
    if rows[5]['theta'] != proposal['candidate'] or rows[5]['theta'] in UNUSED:
        raise ValueError('physical candidate differs from the frozen gradient proposal')
    controls = require_same_control([p['control_proof'] for p in proofs])
    calibration_controls = require_same_control([p['control_proof'] for p in proofs[:3]])
    unused_endpoints = [p['endpoint'] for p in proofs[3:5]]
    checks = [operator.validate_unused(p) for p in unused_endpoints]
    finite = operator.integrated_check(*unused_endpoints, quadrature=128)
    decomposition = endpoint_decomposition(*unused_endpoints, DECLARATIONS, TERMS,
        temperature=operator.state['temperature'])
    candidate_check = operator.validate_unused(proofs[5]['endpoint'])
    delta = proofs[5]['native_loss'] - proofs[1]['native_loss']
    expected = {'calibration_control_check': calibration_controls,
        'all_control_check': controls, 'physical_native_worlds': 6,
        'physical_reply_count': sum(p['response_count'] for p in proofs),
        'unused_checks': checks, 'unused_finite_path': finite,
        'unused_decomposition': decomposition, 'candidate_check': candidate_check,
        'native_candidate_minus_center': delta,
        'operator_sha256': file_sha256(root/'response-operator.json'),
        'operator_representation_sha256': operator._hash,
        'raw_fit_rmse': operator.state['raw_fit_rmse']}
    for key, value in expected.items():
        if raw.get(key) != value:
            raise ValueError(f'completed derived evidence differs: {key}')
    return {'operator_file_sha256': expected['operator_sha256'],
        'operator_representation_sha256': operator._hash,
        'operator_content_sha256': read(root/'response-operator.json')['content_sha256'],
        'temperature_selection': operator.state['temperature_selection'],
        'raw_fit_rmse': operator.state['raw_fit_rmse'], 'center_backward': backward,
        'frozen_proposal': frozen, 'unused_checks': checks,
        'unused_finite_path': finite, 'unused_decomposition': decomposition,
        'candidate_check': candidate_check,
        'candidate_minus_center_native_loss': delta,
        'candidate_improvement_status': ('improved' if delta < 0 else 'worse' if delta > 0 else 'tied'),
        'all_control_check': controls,
        'freeze_order_proof': {'calibration_only_operator_reconstructed': True,
            'unused_outcomes_seen': 0,
            'frozen_file_content_matches_current_bytes': True,
            'historical_creation_time_authenticated': False,
            'scope': ('Content and declared order are verified; filesystem timestamps and owner assertions '
                      'do not independently authenticate when the proposal was created.')}}


def _prefix_control_status(proofs, failures):
    """Verify a prefix or reproduce its preserved strict control failure.

    This does not reinterpret a failed control proof as scientific evidence.
    It only allows a terminal partial audit to bind the exact failure emitted
    by the pinned implementation after every individual proof was restored.
    """
    if not proofs:
        return {'status': 'no-completed-world-control-comparison'}
    try:
        proof = require_same_control([item['control_proof'] for item in proofs])
    except Exception as error:
        failure = failures[0] if len(failures) == 1 else {}
        recorded_cause = (failure.get('stage') == 'fit-control-or-report'
            and failure.get('error_type') == type(error).__name__
            and failure.get('error') == str(error)[:4000]
            and failure.get('loss', 'not-null') is None)
        return {'status': ('reproduced-preserved-strict-control-failure' if recorded_cause
                           else 'observed-uncontrolled-prefix-separate-from-terminal-failure'),
            'error_type': type(error).__name__, 'error': str(error),
            'matches_recorded_terminal_failure_cause': recorded_cause,
            'recorded_terminal_failure': deepcopy(failure),
            'scope': ('Actual independent-Qwen pre-intervention/prompt drift prevents a controlled '
                      'response fit for this prefix. It is a separate technical diagnostic, not '
                      'a negative fidelity, optimization, or scientific outcome, and is not '
                      'asserted to have caused a separately recorded PortableStop.')}
    return proof


def analyze(run, *, expected_source, require_complete=True, expected_amendment=None):
    root = Path(run).resolve()
    before = inventory(root)
    try:
        plan, raw = read(root/'plan.json'), read(root/'evidence.json')
        if (len(expected_source) != 40 or raw.get('schema') != RAW_SCHEMA
                or raw.get('classification') != ACTUAL
                or raw.get('source_commit') != expected_source
                or raw.get('plan') != plan):
            raise ValueError('raw evidence source/schema/immutable plan differs')
        claims = raw.get('claims', {})
        if (claims.get('actual_fixed_weight_Qwen') is not True
                or claims.get('scripted_researcher_HTTP') is not False
                or claims.get('exact_Qwen_Jacobian') is not False
                or claims.get('full_native_world_autograd') is not False
                or claims.get('held_out_seeds') is not False
                or claims.get('causal_scientific_benefit') is not False):
            raise ValueError('raw evidence omits or overstates the preregistered claim boundary')
        amendment = _validate_amendment(plan, expected_amendment)
        sources = source_proof(expected_source, include_amendment=amendment is not None)
        objective, base_system, world = _fixed_plan(plan, expected_source)
        rows, failures, complete = _endpoint_sequence(raw, require_complete=require_complete)
        proofs = [_audit_endpoint(root, row, base_system=base_system, declarations=DECLARATIONS,
                                  objective=objective, world=world) for row in rows]
        physical = _physical_response_ledger(root, {row['name'] for row in rows}, world)
        prefix_control = _prefix_control_status(proofs, failures)
        analysis = None
        if complete:
            analysis = _complete_reconstruction(root, rows, proofs, raw, objective)
        elif len(proofs) >= 3 and (root/'response-operator.json').exists() and (root/'frozen-proposal.json').exists():
            operator, backward, proposal, frozen = _operator_reconstruction(
                root, rows, proofs, raw, objective)
            analysis = {'partial_calibration_only_operator': True,
                'operator_representation_sha256': operator._hash,
                'center_backward': backward, 'frozen_proposal': frozen,
                'candidate': proposal['candidate'],
                'unused_or_candidate_outcome_inference': 'not-derived-from-incomplete-attempt'}
        completed_response_total = sum(p['response_count'] for p in proofs)
        if physical['completed_endpoint_replies'] != completed_response_total:
            raise ValueError('completed endpoint reply total differs from physical SQL ledgers')
        if complete and (physical['partial_null_loss_replies'] != 0
                or physical['all_fresh_physical_replies'] != raw.get('physical_reply_count')):
            raise ValueError('physical reply total differs from all restored checkpoints')
        compact_proofs = [{k: v for k, v in proof.items() if k != 'endpoint'} for proof in proofs]
        result = {'schema': SCHEMA, 'classification': ACTUAL,
            'status': 'complete' if complete else 'valid-preserved-partial-failure',
            'source_commit': expected_source, 'raw_output_root': str(root),
            'source_proof': {'current_scientific_and_comparator_modules_match_experiment_commit': True,
                'module_sha256s': sources},
            'prospective_amendment': amendment,
            'world_binding': {'source_commit': world['source_commit'],
                'model_digest': world['model_digest'], 'corpus_sha256': world['corpus_sha256'],
                'seed': world['seed'], 'years': world['years'],
                'corpus_years': world['corpus_years'],
                'runtime_seed_binding': world['runtime_seed_binding'],
                'experiment': world['experiment']},
            'objective': {'role': 'optimization-loss', 'loss_spec': objective,
                'hard_loss_replayed_for_every_completed_world': True},
            'technical_validity': {'completed_worlds': len(proofs),
                'planned_world_budget': 6, 'failures': deepcopy(failures),
                'all_completed_checkpoints_remeasured': True,
                'all_completed_raw_response_projections_rejoined': True,
                'prefix_control_comparison': prefix_control},
            'world_order': [{'name': p['name'], 'theta': p['theta']} for p in proofs],
            'endpoints': compact_proofs,
            'physical_reply_count': physical['all_fresh_physical_replies'],
            'completed_endpoint_reply_count': physical['completed_endpoint_replies'],
            'partial_null_loss_reply_count': physical['partial_null_loss_replies'],
            'physical_response_ledger': physical['worlds'],
            'response_operator_analysis': analysis,
            'raw_hashes': {'plan_file_sha256': file_sha256(root/'plan.json'),
                'evidence_file_sha256': file_sha256(root/'evidence.json'),
                'evidence_content_sha256': raw.get('content_sha256'),
                'inventory_sha256': digest(before), 'file_count': len(before),
                'files': before},
            'held_out_metrics': {'status': 'not-measured',
                'reason': 'unused coordinates are development fidelity checks, not held-out seeds'},
            'promotion_policy': {'status': 'not-defined-or-applied'},
            'claims': {'new_model_calls': 0, 'new_native_worlds': 0,
                'new_container_or_generated_source_executions': 0,
                'actual_fixed_weight_Qwen': True, 'exact_Qwen_Jacobian': False,
                'full_native_world_autograd': False, 'held_out_generalization': False,
                'causal_scientific_benefit': False,
                'counterfactual_confidence_from_partial_attempt': False}}
        result['content_sha256'] = digest(result)
        return result
    finally:
        if inventory(root) != before:
            raise ValueError('raw evidence changed during read-only audit; no stable result')


def markdown_summary(report):
    if report.get('content_sha256') != digest({k: v for k, v in report.items()
                                               if k != 'content_sha256'}):
        raise ValueError('report content hash differs')
    lines = ['# Native Qwen response-gradient v9 audit', '',
        f"- Status: `{report['status']}`",
        f"- Source: `{report['source_commit']}`",
        f"- Audit content SHA-256: `{report['content_sha256']}`",
        f"- Completed physical worlds: {report['technical_validity']['completed_worlds']} / 6",
        f"- Fresh physical replies: {report['physical_reply_count']}",
        f"- Replies in completed endpoints: {report.get('completed_endpoint_reply_count', report['physical_reply_count'])}",
        f"- Replies in partial null-loss worlds: {report.get('partial_null_loss_reply_count', 0)}", '',
        '## Observed development losses', '',
        '| world | weight | fixed native loss | A | Q | R | replies |',
        '|---|---:|---:|---:|---:|---:|---:|']
    for row in report['endpoints']:
        measurements = row.get('objective_measurements', {})
        a = measurements.get('native.accepted_decisions', 'n/a')
        q = measurements.get('native.accepted_peer_score_sum', 'n/a')
        r = measurements.get('native.review_records', 'n/a')
        lines.append(f"| {row['name']} | {row['theta']:.6g} | {row['native_loss']:.9g} | {a} | {q} | {r} | {row['response_count']} |")
    lines += ['', '## Interpretation boundary', '',
        'The table contains fixed-objective development measurements, including an unfavorable or tied candidate if observed.',
        'The gradient is autograd through a calibration-fitted numeric response representation, not an exact Qwen or native-world Jacobian.',
        'Unused coordinates are fidelity checks, not held-out seeds. No promotion policy or causal scientific-benefit claim is applied.', '']
    control = report['technical_validity'].get('prefix_control_comparison', {})
    if control.get('status') == 'observed-uncontrolled-prefix-separate-from-terminal-failure':
        lines += ['## Independent-Qwen prefix diagnostic', '',
            f"- Status: `{control['status']}`",
            f"- Comparator detail: `{control['error']}`", '',
            'The completed independent worlds changed before the declared rubric intervention, so this prefix cannot identify a controlled response fit.',
            'This stochastic prefix drift is separate from the recorded terminal stop and is not a negative response-fidelity, optimization, or scientific result.', '']
    failures = report['technical_validity']['failures']
    if failures:
        lines += ['## Preserved terminal failure', '',
            'The attempt stopped after the completed prefix. The failed slot has null loss; no missing world or confidence statement was fabricated.',
            '', '```json', json.dumps(failures, ensure_ascii=False, indent=2, sort_keys=True), '```', '']
    analysis = report.get('response_operator_analysis')
    if report['status'] == 'complete' and analysis is not None:
        lines += ['## Frozen update outcome', '',
            f"- Candidate weight: `{analysis['frozen_proposal']['proposal']['candidate']}`",
            f"- Candidate minus center native loss: `{analysis['candidate_minus_center_native_loss']}`",
            f"- Observed status: `{analysis['candidate_improvement_status']}`",
            '- Proposal ordering: content-bound and calibration-only; historical creation time is not independently authenticated.', '']
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--expected-source', required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--markdown', type=Path)
    parser.add_argument('--allow-incomplete', action='store_true')
    parser.add_argument('--expected-amendment', choices=(AMENDMENT_ID,))
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(args.run.resolve()):
        parser.error('audit output must be outside immutable raw directory')
    if args.markdown and args.markdown.resolve().is_relative_to(args.run.resolve()):
        parser.error('markdown output must be outside immutable raw directory')
    report = analyze(args.run, expected_source=args.expected_source,
                     require_complete=not args.allow_incomplete,
                     expected_amendment=args.expected_amendment)
    write_json_atomic(args.output, report, sort_keys=True, allow_nan=False)
    if args.markdown:
        args.markdown.write_text(markdown_summary(report))
    print(json.dumps({'output': str(args.output.resolve()), 'status': report['status'],
        'worlds': report['technical_validity']['completed_worlds'],
        'replies': report['physical_reply_count'],
        'content_sha256': report['content_sha256']}, sort_keys=True))


if __name__ == '__main__':
    main()
