#!/usr/bin/env python3
"""Read-only remeasurement of SCRIPTED v8 response-fidelity QA, no forward calls."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3
import subprocess

from utopia.constants import IMPORTANT_NOTES
from utopia.optimization.native_response_fidelity import (NativeResponseOperator,
    boundary_layout, endpoint_decomposition, raw_review_projection, verify_endpoint)
from utopia.runtime.checkpointing import canonical_json, read_portable_checkpoint
from utopia.system.design_patch import digest
from utopia.system.native_kernel import _hash
from utopia.utils.data_utils import file_sha256, write_json_atomic

CLASSIFICATION = 'scripted-fixture-not-native-results'


def inventory(root):
    paths = sorted(p for p in root.rglob('*') if p.is_file())
    if any(p.is_symlink() for p in root.rglob('*')):
        raise ValueError('QA raw inventory must not contain symlinks')
    return {str(p.relative_to(root)): file_sha256(p) for p in paths}


def transport_proof(root, events):
    """Join every recorded request/reply and actual review prompt-use receipt."""
    with sqlite3.connect((root/'cache/responses.sqlite').resolve().as_uri()+'?mode=ro', uri=True) as db:
        binding, = db.execute('SELECT binding FROM metadata').fetchone()
        binding = json.loads(binding)
        replies = db.execute('SELECT rowid,payload_sha,outcome,data,data_sha FROM replies ORDER BY rowid').fetchall()
    wire = [json.loads(line) for line in (root/'wire.jsonl').read_text().splitlines()]
    wire_shas = [w['payload_sha256'] for w in wire]
    reply_shas = [r[1] for r in replies]
    if (len(set(wire_shas)) != len(wire) or len(set(reply_shas)) != len(replies)
            or set(wire_shas) != set(reply_shas)):
        raise ValueError('scripted QA transport is not one-to-one fresh physical requests')
    wire_by_sha = {row['payload_sha256']: (index+1, row) for index, row in enumerate(wire)}
    actual_prompts, transport_rows = Counter(), []
    for sql_rowid, sha, outcome, data, data_sha in replies:
        wire_line, row = wire_by_sha[sha]
        if (sha != row['payload_sha256'] or sha != hashlib.sha256(canonical_json(row['payload']).encode()).hexdigest()
                or outcome != 'response' or data_sha != hashlib.sha256(data.encode()).hexdigest()
                or json.loads(data)['model'] != binding['model'] or row['payload']['model'] != binding['model']):
            raise ValueError('actual response/request content hash or model differs')
        transport_rows.append({'sql_rowid': sql_rowid, 'wire_line': wire_line, 'payload_sha256': sha})
        for message in row['payload']['messages']:
            text = message.get('content')
            prefix = IMPORTANT_NOTES+'\n\n'
            if message['role'] == 'user' and isinstance(text, str) and text.startswith(prefix):
                actual_prompts[(row['year'], _hash(text[len(prefix):]))] += 1
    deliveries, uses = {}, Counter()
    review_years = []
    for event in events:
        if event['event_type'] == 'native.system.context_delivered':
            message = event['payload']['message']
            for actor in event['actor_ids']:
                key = actor, message['message_id']
                if key in deliveries:
                    raise ValueError('duplicate physical native context delivery')
                deliveries[key] = message
        if event['event_type'] == 'native.system.review_context_used':
            review_years.append(event['year'])
            if not event['provenance']['input_event_ids']:
                raise ValueError('review receipt has no actual causal inputs')
            for use in event['payload']['uses']:
                if not use['message_ids'] or len(set(use['message_ids'])) != len(use['message_ids']):
                    raise ValueError('review receipt has missing/duplicate message identity')
                for identity in use['message_ids']:
                    message = deliveries.get((use['actor_id'], identity))
                    if message is None or message['received_year'] > event['year']:
                        raise ValueError('review used undelivered or future institutional information')
                uses[(event['year'], use['prompt_sha256'])] += 1
    if review_years != list(range(1, 7)) or not uses or uses-actual_prompts:
        raise ValueError('actual native review prompt-use receipts do not match recorded HTTP inputs')
    return {'fresh_physical_responses': len(replies), 'review_prompt_uses_verified': sum(uses.values()),
        'transport_join': {'kind': 'unique-payload-sha256-bijection-in-sql-completion-order',
            'sql_rowids': [r[0] for r in replies],
            'wire_lines_in_sql_order': [r['wire_line'] for r in transport_rows],
            'row_binding_sha256': digest(transport_rows)},
        'actual_actor_message_deliveries': len(deliveries), 'binding_sha256': digest(binding),
        'journal_sha256': file_sha256(root/'cache/responses.sqlite'), 'wire_sha256': file_sha256(root/'wire.jsonl')}


def analyze(run, *, expected_source, refit_amendment=False, representation_output=None):
    run = Path(run).resolve()
    before = inventory(run)
    report = json.loads((run/'compact-response-fidelity-v8.json').read_text())
    endpoints = json.loads((run/'completed-native-endpoints.json').read_text())
    if (report['classification'] != CLASSIFICATION or report['source_commit'] != expected_source
            or report['content_sha256'] != digest({k: v for k, v in report.items() if k != 'content_sha256'})
            or report['new_live_Qwen_calls'] != 0 or report['full_native_world_autograd']
            or report['native_LLM_Jacobian_verified'] or len(endpoints) != 7):
        raise ValueError('not the exact completed scripted native QA/source')
    saved_path = run/'response-operator.json'
    saved_operator = json.loads(saved_path.read_text())
    if (saved_operator['content_sha256'] != digest({k: v for k, v in saved_operator.items() if k != 'content_sha256'})
            or saved_operator['representation_sha256'] != digest(saved_operator['model'])):
        raise ValueError('original saved operator content/representation changed')
    original_proof = {'file_sha256': file_sha256(saved_path), 'content_sha256': saved_operator['content_sha256'],
        'module_sha256': saved_operator['module_sha256'], 'representation_sha256': saved_operator['representation_sha256']}
    if refit_amendment:
        if representation_output is None or Path(representation_output).resolve().is_relative_to(run):
            raise ValueError('amended representation must be saved outside original raw')
        original_module = subprocess.check_output(['git', 'show', expected_source+':utopia/optimization/native_response_fidelity.py'])
        if hashlib.sha256(original_module).hexdigest() != saved_operator['module_sha256']:
            raise ValueError('original representation module does not match exact historical source pin')
        state = saved_operator['model']
        if state['calibration'] != endpoints[:3]:
            raise ValueError('original calibration is not the three preregistered native endpoints')
        for proof in state['raw_response_proofs']:
            if file_sha256(Path(proof['journal'])) != proof['journal_sha256'] or file_sha256(Path(proof['wire'])) != proof['wire_sha256']:
                raise ValueError('historically recorded calibration response bytes changed')
        operator = NativeResponseOperator.fit(state['calibration'], state['declarations'], state['loss_spec'], state['terms'],
            temperatures=[c['temperature'] for c in state['temperature_selection']['candidates']],
            numeric_response_evidence=state['numeric_response_evidence'])
        if operator.state['temperature_selection'] != state['temperature_selection']:
            raise ValueError('receipt hardening unexpectedly changes historical calibration temperature selection')
        report['analysis_amendment'] = {'kind': 'explicit-stricter-receipt-refit-same-frozen-native-endpoints',
            'original_saved_operator': original_proof, 'original_native_source_commit': expected_source,
            'current_representation_module_sha256': file_sha256(Path(__file__).resolve().parents[1]/'utopia/optimization/native_response_fidelity.py'),
            'new_native_forward_worlds': 0, 'new_live_model_calls': 0,
            'reason': 'Full checkpoint SQL binding/count/path and original review task proof; exact calibration-only evidence; complete projection contract; explicit endpoint and delta fidelity.'}
    else:
        operator = NativeResponseOperator.load(saved_path)
    proofs = []
    for index, (endpoint, compact) in enumerate(zip(endpoints, report['endpoints'])):
        if endpoint['world']['source_commit'] != expected_source or endpoint['world']['classification'] != CLASSIFICATION:
            raise ValueError('native endpoint source/classification differs')
        verify_endpoint(endpoint, operator.state['declarations'], operator.state['loss_spec'])
        if compact != {k: endpoint[k] for k in compact}:
            raise ValueError('compact native measurements differ from restored evidence')
        root = Path(endpoint['checkpoint']).parent.parent
        if not root.is_relative_to(run):
            raise ValueError('native endpoint escapes this raw QA directory')
        saved = read_portable_checkpoint(endpoint['checkpoint'])
        proof = transport_proof(root, saved['native_system']['events'])
        layout, z, _ = boundary_layout(endpoint)
        _, projection = raw_review_projection(endpoint, layout, z, journal=root/'cache/responses.sqlite',
            wire=root/'wire.jsonl', mechanism='addressed-selection', input_name='features')
        if sum(c['actual_replies'] for c in projection['cohorts']) != proof['review_prompt_uses_verified']:
            raise ValueError('raw review replies and exact authorized prompt-use counts differ')
        proofs.append({'checkpoint_sha256': endpoint['checkpoint_sha256'], **proof,
            'native_integer_review_cohorts': projection['cohorts'],
            'completion_sql_seal_status': 'absent-in-original-native-run',
            'historical_raw_anchor': ({'kind': 'recorded-calibration-projection-in-original-saved-operator',
                'operator_file_sha256': original_proof['file_sha256'],
                'original_projection_journal_sha256': saved_operator['model']['raw_response_proofs'][index]['journal_sha256'],
                'original_projection_wire_sha256': saved_operator['model']['raw_response_proofs'][index]['wire_sha256']}
                if index < 3 else {'kind': 'no-historical-sql-file-hash-anchor',
                    'status': 'posthoc-current-file-checksum-only-not-run-sealed'}),
            'native_loss_anchor': 'exact-completed-native-checkpoint-hash',
            'raw_numeric_precision_scope': 'calibration-operator-anchored-not-completion-sealed' if index < 3
                else 'checkpoint-binding-count-original-task-and-posthoc-raw-checksum-not-historical-run-seal'})
    point = operator.backward([0.])
    finite = operator.integrated_check(endpoints[3], endpoints[4], quadrature=128)
    if refit_amendment:
        for key in ('gradient', 'frozen_boundary_gradient', 'learned_response_contribution', 'represented_loss'):
            if point[key] != report['point_backward'][key]:
                raise ValueError('receipt hardening changed historical conditional calculus')
        for key in ('status', 'predicted_finite_delta', 'actual_native_delta', 'response_aware_native_error', 'frozen_boundary_native_error'):
            if finite[key] != report['native_finite_path'][key]:
                raise ValueError('receipt hardening changed historical native finite-path measurements')
        report.update(point_backward=point, native_finite_path=finite,
            unused_endpoint_checks=[operator.validate_unused(p) for p in endpoints[3:5]],
            raw_response_proofs=operator.state['raw_response_proofs'])
    elif point != report['point_backward'] or finite != report['native_finite_path']:
        raise ValueError('backward/unused finite-path evidence does not reconstruct')
    if endpoint_decomposition(endpoints[3], endpoints[4], operator.state['declarations'],
            operator.state['terms'], temperature=operator.state['temperature']) != report['endpoint_decomposition']:
        raise ValueError('native response decomposition does not reconstruct')
    after = inventory(run)
    if after != before:
        raise ValueError('raw QA changed during read-only audit')
    report.pop('content_sha256')
    if refit_amendment:
        operator.save(representation_output, verification_endpoints=endpoints[3:])
        # Durable semantic reconstruction uses only the same frozen endpoints.
        restored = NativeResponseOperator.load(representation_output)
        if restored.state != operator.state:
            raise ValueError('amended representation durable reload differs')
        amended = json.loads(Path(representation_output).read_text())
        report['analysis_amendment']['saved_operator'] = {'path': str(Path(representation_output).resolve()),
            'file_sha256': file_sha256(Path(representation_output)), 'content_sha256': amended['content_sha256'],
            'module_sha256': amended['module_sha256'], 'representation_sha256': amended['representation_sha256']}
    if inventory(run) != before:
        raise ValueError('raw QA changed during durable representation reload')
    report['audit'] = {'schema': 'scienceutopia.native-response-fidelity-qa-audit.v8',
        'source_module_sha256': file_sha256(Path(__file__)), 'new_model_calls': 0,
        'analysis_source_commit': subprocess.check_output(['git', 'rev-parse', 'HEAD'], text=True).strip(),
        'analysis_worktree_clean_at_audit': not bool(subprocess.check_output(['git', 'status', '--porcelain'], text=True).strip()),
        'new_code_container_executions': 0, 'raw_directory': str(run),
        'raw_files_verified_unchanged': len(before), 'raw_inventory_sha256': digest(before),
        'native_endpoint_measurements_independently_reextracted': 7, 'transport': proofs,
        'scope': 'Scripted developer QA only; all native costs retained, no actual-Qwen fidelity claim.'}
    report['content_sha256'] = digest(report)
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--expected-source', required=True)
    parser.add_argument('--output', required=True, type=Path)
    parser.add_argument('--refit-receipt-amendment', action='store_true')
    parser.add_argument('--representation-output', type=Path)
    args = parser.parse_args()
    if args.output.resolve().is_relative_to(args.run.resolve()):
        parser.error('audit output must be outside immutable raw directory')
    report = analyze(args.run, expected_source=args.expected_source,
        refit_amendment=args.refit_receipt_amendment, representation_output=args.representation_output)
    write_json_atomic(args.output, report, sort_keys=True, allow_nan=False)
    print(json.dumps({'output': str(args.output), 'classification': report['classification'],
        'native_worlds': report['native_worlds'], 'raw_files_unchanged': report['audit']['raw_files_verified_unchanged']}))


if __name__ == '__main__':
    main()
