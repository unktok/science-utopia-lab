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

from utopia.agents.base_agent import PaperReview
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
from utopia.runtime.checkpointing import canonical_json, read_portable_checkpoint
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
AMENDMENT_A2 = 'native-qwen-response-gradient-v9-a2'
AMENDMENT_A3 = 'native-qwen-response-gradient-v9-a3'
AMENDMENT_PATHS = {
    AMENDMENT_A2: ROOT / 'research/protocols/campaigns/native-qwen-response-gradient-v9-a2.md',
    AMENDMENT_A3: ROOT / 'research/protocols/campaigns/native-qwen-response-gradient-v9-a3.md',
}
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


def source_proof(expected_source, *, amendment_id=None):
    """Bind active scientific/comparator bytes to the experiment commit.

    The auditor itself is intentionally allowed to be a later addition. The
    modules that interpret raw evidence are not: current analysis code cannot
    silently reinterpret an old run under new scientific/comparator semantics.
    """
    extras = ()
    if amendment_id is not None:
        path = AMENDMENT_PATHS.get(amendment_id)
        if path is None:
            raise ValueError('unknown response-gradient amendment source')
        extras = (str(path.relative_to(ROOT)),)
        if amendment_id == AMENDMENT_A3:
            extras += ('utopia/optimization/native_response_prefix.py',)
    paths = SOURCE_PATHS + extras
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
    path = AMENDMENT_PATHS.get(expected_amendment)
    if path is None or not path.is_file():
        raise ValueError('unknown or unavailable response-gradient amendment')
    if expected_amendment == AMENDMENT_A2:
        expected = {'id': AMENDMENT_A2, 'sha256': file_sha256(path),
            'prior_maximum_worlds': 3, 'maximum_combined_physical_worlds': 9,
            'changes': ('exclude only server envelope metadata from cross-world '
                        'semantic response equality')}
    else:
        expected = {'id': AMENDMENT_A3, 'sha256': file_sha256(path),
            'prior_world_attempts': 4, 'prior_completed_worlds': 2,
            'prior_partial_worlds': 2, 'prior_physical_replies': 228,
            'maximum_combined_world_attempts': 10,
            'changes': ('replay an exact actual Qwen pre-intervention history; '
                        'generate affected and later replies freshly')}
    if amendment != expected:
        raise ValueError('prospective amendment ID/hash/prior/combined budget differs')
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


def _response_coupling(plan, amendment, raw_root):
    value = plan.get('response_coupling')
    if amendment is None or amendment['id'] != AMENDMENT_A3:
        if value is not None:
            raise ValueError('response coupling requires the explicit a3 amendment')
        return None
    if (not isinstance(value, dict) or set(value) != {'mode', 'unique_anchor_prefix_calls', 'prepared'}
            or value.get('mode') != 'actual-common-prefix-replay'
            or type(value.get('unique_anchor_prefix_calls')) is not int
            or value['unique_anchor_prefix_calls'] <= 0):
        raise ValueError('a3 plan lacks exact common-prefix coupling')
    prepared = value['prepared']
    from utopia.optimization.native_response_prefix import SCHEMA as prefix_schema, prepare_common_prefix
    if (not isinstance(prepared, dict) or prepared.get('schema') != prefix_schema
            or prepared.get('content_sha256') != digest({k: v for k, v in prepared.items()
                                                         if k != 'content_sha256'})
            or prepared.get('classification') !=
                'historical-oracle-prefix-coupling-not-independent-native-samples'
            or prepared.get('anchor_classification') != ACTUAL
            or prepared.get('prefix_count') != value['unique_anchor_prefix_calls']
            or len(prepared.get('calls', [])) != value['unique_anchor_prefix_calls']
            or prepared.get('module_sha256') != file_sha256(
                ROOT/'utopia/optimization/native_response_prefix.py')):
        raise ValueError('a3 prepared common-prefix manifest differs')
    anchor = Path(prepared['anchor_world_dir']).resolve()
    if anchor.is_relative_to(Path(raw_root).resolve()):
        raise ValueError('a3 historical anchor must be a separately preserved actual world')
    if prepare_common_prefix(anchor, prepared['anchor_endpoint']) != prepared:
        raise ValueError('a3 prepared prefix does not reconstruct from unchanged anchor raw')
    return {'mode': value['mode'], 'unique_anchor_prefix_calls': prepared['prefix_count'],
        'prepared': prepared}


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


def _wire_rows(path):
    return [json.loads(line) for line in Path(path).read_text().splitlines()]


def _year1_review_records(checkpoint):
    """Independently reconstruct semantic Year-1 reviews and clock hashes."""
    state = read_portable_checkpoint(checkpoint)
    records, reviews = [], {}
    for conference in state.get('conference_system', {}).get('conferences', []):
        conference_id = conference.get('conference_id')
        for paper_id, values in conference.get('reviews', {}).items():
            for review in values:
                if review.get('year') != 1:
                    continue
                identity = {'year': 1, 'conference_id': conference_id,
                    'paper_id': paper_id, 'reviewer_id': review.get('reviewer_id')}
                key = canonical_json(identity)
                clock = review.get('review_time')
                if (key in reviews or review.get('conference_id') != conference_id
                        or review.get('arxiv_id') != paper_id
                        or not isinstance(identity['reviewer_id'], str)
                        or not identity['reviewer_id'] or type(clock) not in (int, float)
                        or not math.isfinite(clock)):
                    raise ValueError('year1 review checkpoint has an invalid semantic identity or clock')
                nonclock = {k: v for k, v in review.items() if k != 'review_time'}
                records.append({**identity, 'review_time': clock,
                    'anchor_review_sha256': digest(review),
                    'nonclock_review_sha256': digest(nonclock)})
                reviews[key] = deepcopy(review)
    records.sort(key=lambda row: canonical_json({k: row[k] for k in
        ('year', 'conference_id', 'paper_id', 'reviewer_id')}))
    return records, reviews


def _audit_review_clock_coupling(cell, prepared, receipt):
    """Verify clock replay against real anchor/target checkpoints and receipts."""
    declaration = prepared.get('review_clock_coupling', {})
    anchor_file = prepared.get('anchor_files', {}).get('year1_checkpoint', {})
    source_sha = declaration.get('source_checkpoint_sha256')
    anchor_path = Path(anchor_file.get('path', '')).resolve()
    target_path = cell/'simulation/checkpoints/native-design/portable_checkpoint_year_1.json.gz'
    if (not anchor_path.is_file() or not target_path.is_file()
            or anchor_file.get('sha256') != source_sha
            or file_sha256(anchor_path) != source_sha):
        raise ValueError('review-clock source checkpoint binding differs')
    anchor_records, _ = _year1_review_records(anchor_path)
    target_records, target_reviews = _year1_review_records(target_path)
    expected = declaration.get('records')
    if (declaration.get('field') != 'review_time' or declaration.get('period') != 1
            or anchor_records != expected or target_records != expected):
        raise ValueError('review-clock anchor/target checkpoint semantics differ')
    clock = receipt.get('review_clock_coupling', {})
    if (clock.get('source_checkpoint_sha256') != source_sha
            or clock.get('field') != 'review_time' or clock.get('period') != 1
            or clock.get('expected_records') != len(expected)
            or clock.get('completed_checkpoint_verification') !=
                'exact-semantic-year1-checkpoint-clocks-verified'
            or clock.get('prior_session_before_timestamps_reconstructed') is not False
            or clock.get('global_and_transport_clock_modified') is not False
            or clock.get('year2_review_clock_modified') is not False):
        raise ValueError('review-clock completion receipt contract differs')
    changes = clock.get('current_session_before_after_records')
    if not isinstance(changes, list) or len(changes) != len(expected):
        raise ValueError('review-clock before/after receipt coverage differs')
    expected_by_id = {canonical_json({k: row[k] for k in
        ('year', 'conference_id', 'paper_id', 'reviewer_id')}): row for row in expected}
    seen = set()
    for change in changes:
        identity = {k: change.get(k) for k in
            ('year', 'conference_id', 'paper_id', 'reviewer_id')}
        key = canonical_json(identity)
        anchor = expected_by_id.get(key)
        target = target_reviews.get(key)
        before = change.get('before_review_time')
        if (anchor is None or target is None or key in seen
                or change.get('field') != 'review_time'
                or change.get('source_checkpoint_sha256') != source_sha
                or type(before) not in (int, float) or not math.isfinite(before)
                or change.get('after_review_time') != anchor['review_time']
                or change.get('after_review_sha256') != anchor['anchor_review_sha256']
                or change.get('nonclock_review_sha256') != anchor['nonclock_review_sha256']):
            raise ValueError('review-clock before/after row differs')
        reconstructed_before = deepcopy(target)
        reconstructed_before['review_time'] = before
        if (digest(reconstructed_before) != change.get('before_review_sha256')
                or digest(target) != change.get('after_review_sha256')
                or digest({k: v for k, v in target.items() if k != 'review_time'}) !=
                    change.get('nonclock_review_sha256')):
            raise ValueError('review-clock before/after hashes do not reconstruct')
        seen.add(key)
    if seen != set(expected_by_id):
        raise ValueError('review-clock semantic identities are incomplete')
    return {'source_checkpoint_sha256': source_sha,
        'target_checkpoint_sha256': file_sha256(target_path),
        'record_count': len(expected), 'all_semantic_records_verified': True,
        'before_hashes_reconstructed_from_target_nonclock_state': True,
        'historical_before_timestamps_independently_authenticated': False,
        'year2_review_clocks_declared_live': True}


def _audit_common_prefix(cell, row, endpoint, proof, coupling):
    """Reconstruct one target's normal cache and exact anchor-origin prefix."""
    prepared = coupling['prepared']
    receipt_path = cell/'common-prefix-receipt.json'
    if not receipt_path.is_file():
        raise ValueError(f"{row['name']}: completed a3 endpoint lacks prefix receipt")
    receipt = read(receipt_path)
    if row.get('common_prefix_receipt') != receipt:
        raise ValueError(f"{row['name']}: row and durable prefix receipt differ")
    prefix = prepared['prefix_count']
    journal, wire = cell/'replies/responses.sqlite', cell/'wire-requests.jsonl'
    with sqlite3.connect(journal.resolve().as_uri()+'?mode=ro', uri=True) as db:
        metadata = db.execute('SELECT binding FROM metadata').fetchall()
        sql = db.execute(
            'SELECT rowid,identity,payload_sha,outcome,data,data_sha FROM replies ORDER BY rowid').fetchall()
    wires = _wire_rows(wire)
    if len(metadata) != 1 or len(sql) != len(wires) or len(sql) != endpoint['response_cache_count']:
        raise ValueError(f"{row['name']}: logical target cache/wire count differs")
    binding = json.loads(metadata[0][0])
    if receipt != {**{k: receipt[k] for k in receipt if k != 'content_sha256'},
                    'content_sha256': digest({k: receipt[k] for k in receipt if k != 'content_sha256'})}:
        raise ValueError(f"{row['name']}: prefix receipt content differs")
    expected_receipt = {
        'schema': prepared['schema']+'.execution',
        'manifest_sha256': prepared['content_sha256'],
        'anchor_checkpoint_sha256': prepared['anchor_endpoint']['checkpoint_sha256'],
        'used_prefix_count': prefix, 'expected_prefix_count': prefix,
        'replayed_response_count': prefix,
        'fresh_physical_calls': len(sql)-prefix,
        'fresh_physical_reply_count': len(sql)-prefix,
        'fresh_review_boundary_reached': True,
        'logical_response_count': len(sql), 'prefix_complete': True,
        'independent_prefix_replication': False,
        'target_binding_sha256': digest(binding),
    }
    for key, value in expected_receipt.items():
        if receipt.get(key) != value:
            raise ValueError(f"{row['name']}: prefix receipt field differs: {key}")
    if (type(receipt.get('initially_committed_prefix_count')) is not int
            or type(receipt.get('replayed_in_this_session')) is not int
            or receipt['initially_committed_prefix_count'] + receipt['replayed_in_this_session'] != prefix
            or type(receipt.get('fresh_physical_calls_this_session')) is not int
            or not 0 <= receipt['fresh_physical_calls_this_session'] <= len(sql)-prefix):
        raise ValueError(f"{row['name']}: prefix resume/session counters differ")
    if (row.get('logical_response_count') != len(sql)
            or row.get('replayed_response_count') != prefix
            or row.get('fresh_physical_replies') != len(sql)-prefix):
        raise ValueError(f"{row['name']}: runner logical/replayed/fresh counters differ")
    for index, (saved, request, call) in enumerate(zip(sql[:prefix], wires[:prefix], prepared['calls'])):
        origin = {'schema': prepared['schema']+'.replayed-from',
            'manifest_sha256': prepared['content_sha256'],
            'anchor_checkpoint_sha256': prepared['anchor_endpoint']['checkpoint_sha256'],
            'anchor_journal_sha256': prepared['anchor_files']['journal']['sha256'], **call}
        _, identity, payload_sha, outcome, data, data_sha = saved
        if (request.get('replayed_from') != origin or request.get('year') != call['year']
                or request.get('payload_sha256') != call['payload_sha256']
                or payload_sha != call['payload_sha256'] or data_sha != call['response_sha256']
                or outcome != 'response' or hashlib.sha256(data.encode()).hexdigest() != data_sha
                or identity == call['anchor_cache_identity']
                or hashlib.sha256(canonical_json(request['payload']).encode()).hexdigest() != payload_sha):
            raise ValueError(f"{row['name']}: logical replay row {index} differs from exact anchor origin")
    if any('replayed_from' in request for request in wires[prefix:]):
        raise ValueError(f"{row['name']}: undeclared replay exists after the prefix")
    first = wires[prefix]
    payload = first['payload']
    schema = (payload.get('extra_body', {}).get('structured_outputs', {}).get('json')
        or payload.get('response_format', {}).get('json_schema', {}).get('schema'))
    seed = payload.get('seed', payload.get('extra_body', {}).get('seed'))
    boundary = prepared['boundary']
    if (first.get('year') != boundary['year'] or seed != boundary['seed']
            or digest(schema) != boundary['task_schema_sha256']
            or schema != PaperReview.model_json_schema()):
        raise ValueError(f"{row['name']}: first fresh call is not the declared Year2 review boundary")
    anchor_proof = control_proof(prepared['anchor_endpoint'], Path(prepared['anchor_world_dir']))
    anchor_control = require_same_control([anchor_proof, proof])
    clock_proof = _audit_review_clock_coupling(cell, prepared, receipt)
    return {'mode': coupling['mode'], 'manifest_sha256': prepared['content_sha256'],
        'receipt_content_sha256': receipt['content_sha256'],
        'anchor_checkpoint_sha256': prepared['anchor_endpoint']['checkpoint_sha256'],
        'anchor_journal_sha256': prepared['anchor_files']['journal']['sha256'],
        'unique_anchor_prefix_calls': prefix, 'response_count': len(sql),
        'replayed_response_count': prefix, 'fresh_physical_reply_count': len(sql)-prefix,
        'target_binding_sha256': digest(binding),
        'anchor_control_check': anchor_control,
        'review_clock_coupling': clock_proof,
        'first_fresh_review_boundary_verified': True,
        'no_replay_after_prefix_verified': True,
        'target_cache_identities_distinct_from_anchor': True}


def _audit_endpoint(root, row, *, base_system, declarations, objective, world, coupling=None):
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
    if response['checkpoint_response_count'] != endpoint['response_cache_count']:
        raise ValueError(f'{name}: full logical reply count differs')
    prefix_proof = (_audit_common_prefix(cell, row, endpoint, proof, coupling)
                    if coupling is not None else None)
    if coupling is None:
        if (endpoint['response_cache_count'] != row.get('fresh_physical_replies')
                or any(key in row for key in ('logical_response_count', 'replayed_response_count',
                                               'common_prefix_receipt'))):
            raise ValueError(f'{name}: independent-world physical reply count differs')
        fresh, replayed = endpoint['response_cache_count'], 0
    else:
        fresh = prefix_proof['fresh_physical_reply_count']
        replayed = prefix_proof['replayed_response_count']
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
        'fresh_physical_reply_count': fresh, 'replayed_response_count': replayed,
        'common_prefix_proof': prefix_proof,
        'objective_measurements': objective_metrics,
        'review_reply_count': sum(item['actual_replies'] for item in response['cohorts']),
        'review_cohorts': response['cohorts'],
        'raw_projection_sha256': digest(response),
        'journal_sha256': response['journal_sha256'], 'wire_sha256': response['wire_sha256'],
        'code_contexts_sha256': endpoint['code_contexts_sha256'],
        'completion_receipt_sha256': receipt['content_sha256'],
        'run_manifest_sha256': receipt['run_manifest_sha256'],
        'control_proof': proof, 'endpoint': endpoint}


def _physical_response_ledger(root, completed_names, world, coupling=None):
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
                'loss': None, 'response_count': 0, 'logical_response_count': 0,
                'fresh_physical_reply_count': 0, 'replayed_response_count': 0,
                'outcomes': {}, 'journal_sha256': None})
            continue
        wire_path = cell/'wire-requests.jsonl'
        if not wire_path.is_file():
            raise ValueError(f'{cell.name}: response journal lacks exact wire provenance')
        before = file_sha256(journal)
        with sqlite3.connect(journal.resolve().as_uri()+'?mode=ro', uri=True) as db:
            metadata = db.execute('SELECT binding FROM metadata').fetchall()
            outcomes = dict(db.execute(
                'SELECT outcome,COUNT(*) FROM replies GROUP BY outcome').fetchall())
            rows = db.execute(
                'SELECT rowid,identity,payload_sha,outcome,data,data_sha FROM replies ORDER BY rowid').fetchall()
        wires = _wire_rows(wire_path)
        if len(metadata) != 1 or file_sha256(journal) != before:
            raise ValueError(f'{cell.name}: physical response journal changed or lacks one binding')
        binding = json.loads(metadata[0][0])
        if (binding.get('seed') != world['seed']
                or binding.get('model_revision') != world['model_digest']
                or binding.get('corpus_sha256') != world['corpus_sha256']
                or binding.get('science_config', {}).get('source_commit') != world['source_commit']
                or len(rows) != sum(outcomes.values())
                or len(rows) != len(wires)
                or any(not _sha256(row[1]) or not _sha256(row[2]) or not _sha256(row[5])
                       or hashlib.sha256(row[4].encode()).hexdigest() != row[5] for row in rows)
                or any(row[3] not in {'response', 'error'} for row in rows)
                or [row[2] for row in rows] != [wire.get('payload_sha256') for wire in wires]):
            raise ValueError(f'{cell.name}: partial/full physical response binding or rows differ')
        replayed = sum('replayed_from' in wire for wire in wires)
        if ((coupling is None and replayed)
                or (coupling is not None and any('replayed_from' not in wire for wire in wires[:replayed]))
                or any('replayed_from' in wire for wire in wires[replayed:])):
            raise ValueError(f'{cell.name}: logical replay rows are not one exact initial prefix')
        logical = outcomes.get('response', 0)
        fresh = logical-replayed
        if fresh < 0:
            raise ValueError(f'{cell.name}: replayed count exceeds logical replies')
        completed = cell.name in completed_names
        ledger.append({'name': cell.name,
            'status': 'completed-endpoint' if completed else 'partial-null-loss-world',
            'loss': 'reported-in-endpoint-ledger' if completed else None,
            'response_count': logical, 'logical_response_count': logical,
            'fresh_physical_reply_count': fresh, 'replayed_response_count': replayed,
            'outcomes': outcomes,
            'journal_sha256': before, 'binding_sha256': digest(binding),
            'row_identity_sha256': digest(rows)})
    completed_logical = sum(row['logical_response_count'] for row in ledger
                            if row['status'] == 'completed-endpoint')
    partial_logical = sum(row['logical_response_count'] for row in ledger
                          if row['status'] != 'completed-endpoint')
    completed_fresh = sum(row['fresh_physical_reply_count'] for row in ledger
                          if row['status'] == 'completed-endpoint')
    partial_fresh = sum(row['fresh_physical_reply_count'] for row in ledger
                        if row['status'] != 'completed-endpoint')
    replayed = sum(row['replayed_response_count'] for row in ledger)
    return {'worlds': ledger, 'completed_endpoint_replies': completed_logical,
        'partial_null_loss_replies': partial_logical,
        'completed_endpoint_fresh_physical_replies': completed_fresh,
        'partial_null_loss_fresh_physical_replies': partial_fresh,
        'all_logical_replies': completed_logical+partial_logical,
        'all_replayed_replies': replayed,
        'all_fresh_physical_replies': completed_fresh+partial_fresh}


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


def _represented_landscape(operator):
    """Posthoc rendering data from the already frozen fitted representation."""
    coordinates = []
    for index in range(61):
        theta = .2 + index * .01
        represented = operator.backward([theta])
        coordinates.append({'theta': theta,
            'predicted_loss': represented['represented_loss'],
            'gradient': represented['gradient'][0],
            'frozen_boundary_gradient': represented['frozen_boundary_gradient'][0]})
    return {'scope': 'posthoc frozen representation visualization; not native samples or candidate selection',
        'coordinates': coordinates, 'representation_sha256': operator._hash,
        'new_native_forward_calls': 0, 'new_model_calls': 0}


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
        'physical_reply_count': sum(p['fresh_physical_reply_count'] for p in proofs),
        'unused_checks': checks, 'unused_finite_path': finite,
        'unused_decomposition': decomposition, 'candidate_check': candidate_check,
        'native_candidate_minus_center': delta,
        'operator_sha256': file_sha256(root/'response-operator.json'),
        'operator_representation_sha256': operator._hash,
        'raw_fit_rmse': operator.state['raw_fit_rmse']}
    for key, value in expected.items():
        if raw.get(key) != value:
            raise ValueError(f'completed derived evidence differs: {key}')
    landscape = _represented_landscape(operator)
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
        'represented_landscape': landscape,
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
        sources = source_proof(expected_source,
            amendment_id=amendment['id'] if amendment is not None else None)
        coupling = _response_coupling(plan, amendment, root)
        objective, base_system, world = _fixed_plan(plan, expected_source)
        rows, failures, complete = _endpoint_sequence(raw, require_complete=require_complete)
        proofs = [_audit_endpoint(root, row, base_system=base_system, declarations=DECLARATIONS,
                                  objective=objective, world=world, coupling=coupling) for row in rows]
        physical = _physical_response_ledger(root, {row['name'] for row in rows}, world,
                                             coupling=coupling)
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
        completed_fresh_total = sum(p['fresh_physical_reply_count'] for p in proofs)
        if physical['completed_endpoint_fresh_physical_replies'] != completed_fresh_total:
            raise ValueError('completed endpoint fresh reply total differs from physical wire provenance')
        if complete and (physical['partial_null_loss_replies'] != 0
                or physical['all_fresh_physical_replies'] != raw.get('physical_reply_count')):
            raise ValueError('physical reply total differs from all restored checkpoints')
        response_coupling = None
        if coupling is not None:
            prepared = coupling['prepared']
            response_coupling = {'mode': coupling['mode'],
                'classification': 'common-prefix-coupled-development-not-independent-worlds',
                'unique_anchor_prefix_calls': coupling['unique_anchor_prefix_calls'],
                'prior_v9_actual_physical_replies': amendment['prior_physical_replies'],
                'prepared_manifest_sha256': prepared['content_sha256'],
                'anchor_checkpoint_sha256': prepared['anchor_endpoint']['checkpoint_sha256'],
                'anchor_journal_sha256': prepared['anchor_files']['journal']['sha256'],
                'anchor_wire_sha256': prepared['anchor_files']['wire']['sha256'],
                'anchor_code_contexts_sha256': prepared['anchor_files']['code_contexts']['sha256'],
                'anchor_source_commit': prepared['anchor_endpoint']['world']['source_commit'],
                'scope': ('One actual Qwen prefix is replayed across logical development worlds; '
                          'anchor-origin calls are counted once and are not new a3 calls.')}
            if complete:
                expected_counts = {
                    'response_coupling': plan['response_coupling'],
                    'logical_response_count': physical['all_logical_replies'],
                    'fresh_physical_reply_count': physical['all_fresh_physical_replies'],
                    'unique_actual_calls_supporting_this_campaign':
                        coupling['unique_anchor_prefix_calls']+physical['all_fresh_physical_replies'],
                    'all_v9_actual_physical_replies': 228+physical['all_fresh_physical_replies']}
                for key, value in expected_counts.items():
                    if raw.get(key) != value:
                        raise ValueError(f'a3 coupled response accounting differs: {key}')
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
            'fresh_physical_reply_count': physical['all_fresh_physical_replies'],
            'logical_response_count': physical['all_logical_replies'],
            'replayed_response_count': physical['all_replayed_replies'],
            'unique_actual_calls_supporting_this_campaign': (
                coupling['unique_anchor_prefix_calls']+physical['all_fresh_physical_replies']
                if coupling is not None else physical['all_fresh_physical_replies']),
            'all_v9_actual_physical_reply_count': (
                amendment['prior_physical_replies']+physical['all_fresh_physical_replies']
                if coupling is not None else None),
            'completed_endpoint_reply_count': physical['completed_endpoint_replies'],
            'partial_null_loss_reply_count': physical['partial_null_loss_replies'],
            'physical_response_ledger': physical['worlds'],
            'response_coupling': response_coupling,
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
                'common_prefix_coupled_development': coupling is not None,
                'independent_native_world_replication': False if coupling is not None else None,
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
    coupled = report.get('response_coupling') is not None
    lines = ['# Native Qwen response-gradient v9 audit', '',
        f"- Status: `{report['status']}`",
        f"- Source: `{report['source_commit']}`",
        f"- Audit content SHA-256: `{report['content_sha256']}`",
        f"- Completed {'common-prefix-coupled logical' if coupled else 'physical'} worlds: {report['technical_validity']['completed_worlds']} / 6",
        f"- Fresh physical replies: {report['physical_reply_count']}",
        f"- Logical responses: {report.get('logical_response_count', report['physical_reply_count'])}",
        f"- Replayed prefix responses: {report.get('replayed_response_count', 0)}",
        f"- Replies in completed endpoints: {report.get('completed_endpoint_reply_count', report['physical_reply_count'])}",
        f"- Replies in partial null-loss worlds: {report.get('partial_null_loss_reply_count', 0)}", '',
        '## Observed development losses', '',
        '| world | weight | fixed native loss | A | Q | R | logical | fresh | replayed |',
        '|---|---:|---:|---:|---:|---:|---:|---:|---:|']
    for row in report['endpoints']:
        measurements = row.get('objective_measurements', {})
        a = measurements.get('native.accepted_decisions', 'n/a')
        q = measurements.get('native.accepted_peer_score_sum', 'n/a')
        r = measurements.get('native.review_records', 'n/a')
        lines.append(f"| {row['name']} | {row['theta']:.6g} | {row['native_loss']:.9g} | {a} | {q} | {r} | {row['response_count']} | {row.get('fresh_physical_reply_count', row['response_count'])} | {row.get('replayed_response_count', 0)} |")
    lines += ['', '## Interpretation boundary', '',
        'The table contains fixed-objective development measurements, including an unfavorable or tied candidate if observed.',
        'The gradient is autograd through a calibration-fitted numeric response representation, not an exact Qwen or native-world Jacobian.',
        'Unused coordinates are fidelity checks, not held-out seeds. No promotion policy or causal scientific-benefit claim is applied.', '']
    if coupled:
        coupling = report['response_coupling']
        lines += ['## Actual common-prefix coupling', '',
            f"- Unique anchor-origin calls: `{coupling['unique_anchor_prefix_calls']}`",
            f"- Prepared manifest: `{coupling['prepared_manifest_sha256']}`", '',
            'The six development worlds execute the full native forward process but share one exact actual-Qwen prefix.',
            'Replayed prefix responses are logical cache entries, not new model calls or independent world replications. Anchor-origin calls are counted once outside the a3 fresh-call total.', '']
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
    parser.add_argument('--expected-amendment', choices=(AMENDMENT_A2, AMENDMENT_A3))
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
