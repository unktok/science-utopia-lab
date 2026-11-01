#!/usr/bin/env python3
"""Read-only feedback/source, full-run gradient and actual UI-job evidence audit."""
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from utopia.optimization.loss import evaluate_loss
from utopia.system import SystemSpec
from utopia.system.design_patch import digest
from utopia.runtime.checkpointing import canonical_json, read_portable_checkpoint
from utopia.utils.data_utils import file_sha256


def wire_summary(cell, *, needle, required):
    cell = Path(cell).resolve()
    wire = cell / 'wire-requests.jsonl'
    if not wire.exists():
        if required: raise ValueError('actual request journal required')
        return {'recorded': False}
    db = sqlite3.connect((cell / 'replies/responses.sqlite').as_uri() + '?mode=ro', uri=True)
    try:
        responses = db.execute('SELECT payload_sha,outcome,data,data_sha FROM replies').fetchall()
    finally:
        db.close()
    if any(outcome != 'response' or hashlib.sha256(data.encode()).hexdigest() != sha for _, outcome, data, sha in responses):
        raise ValueError('response journal integrity mismatch')
    requests = [json.loads(line) for line in wire.read_text().splitlines()]
    if any(hashlib.sha256(canonical_json(r['payload']).encode()).hexdigest() != r['payload_sha256'] for r in requests):
        raise ValueError('actual request payload hash mismatch')
    if {r['payload_sha256'] for r in requests} != {r[0] for r in responses}:
        raise ValueError('HTTP payloads and completed response-cache inputs differ')
    contexts = [r for r in requests if needle in json.dumps(r['payload'])]
    return {'recorded': True, 'wire_sha256': file_sha256(wire), 'actual_requests': len(requests),
            'contexts_by_year': dict(Counter(str(r['year']) for r in contexts)),
            'context_request_hashes': sorted(r['payload_sha256'] for r in contexts)}


def source_audit(run, loss, *, require_wire):
    from scripts.audit_native_design_loop import audit
    from utopia.optimization.native_feedback import feedback_from_native_history
    saved = json.loads((run / 'campaign/native-design-state.json').read_text())
    result = audit(run, loss, saved['binding']['world']['years'])
    feedback = feedback_from_native_history(saved['records'])
    proposals = []
    for index, record in enumerate(saved['records'][1:], 1):
        receipts = [json.loads(p.read_text()) for p in (run / 'design-proposals').glob(f'source-revision-{index}-*.json')]
        accepted = [r for r in receipts if r['status'] == 'isolated-probe-passed-not-native-evaluated' and r['patch'] == record['patch']]
        if len(accepted) != 1: raise ValueError('executed revision does not match one actual generated proposal')
        receipt = accepted[0]
        if receipt['binding']['history_sha256'] != digest(saved['records'][:index]):
            raise ValueError('source proposal does not depend on the exact prior native observations')
        source = record['patch']['operations'][0]['value']['source']
        if source != receipt['draft']['source'] or digest(source) != receipt['source_sha256']:
            raise ValueError('model source was not preserved exactly')
        plan_hash = receipt.get('plan_sha256')
        if plan_hash:
            plans = [json.loads(p.read_text()) for p in (run / 'design-proposals').glob(f'source-plan-{index}-*.json')]
            matching = [p for p in plans if digest(p['plan']) == plan_hash and p['binding'] == receipt['binding'] and p['prompt_sha256'] == receipt['prompt_sha256']]
            if len(matching) != 1:
                raise ValueError('recorded model plan and executed source lineage differ')
        proposals.append({'index': index, 'source_sha256': digest(source), 'history_sha256': receipt['binding']['history_sha256'],
            'probe_messages': receipt['probe_message_count'], 'plan_sha256': plan_hash, 'technical_repairs': sum(r['status'] == 'invalid' for r in receipts)})
    for row in result['rows']:
        for item in row['runs']:
            item['wire'] = wire_summary(run / 'runs' / item['run_id'], needle='peer-observer', required=require_wire)
    result.update(proposals=proposals, feedback_activity=[{
        'observation_id': r['observation_id'], 'loss': r['loss'],
        'delivered_messages': sum(len(e['delivered_messages']) for e in r['executions'])} for r in feedback['observations']],
        raw_output_root=str(run), source_verification='exact model source, prior-observation binding, native executed source/image receipts and independent domain/loss audit')
    return result


def gradient_audit(run, loss):
    run = Path(run).resolve()
    from utopia.optimization.native_gradient import NativeScoreFunctionSearch, NativeGradientCampaign
    from utopia.system.native_kernel import NativeScienceKernel
    saved_path = run / 'campaign/native-gradient-state.json'
    before = file_sha256(saved_path)
    saved = json.loads(saved_path.read_text())
    definition = saved['binding']['search_definition']
    if definition['schema'] == 'scienceutopia.native-discrete-policy.v1':
        from utopia.optimization.native_discrete_policy import NativeDiscretePolicySearch
        search = NativeDiscretePolicySearch.from_state(definition, loss_spec=loss)
    else:
        search = NativeScoreFunctionSearch.from_state(definition, loss_spec=loss)
    campaign = NativeGradientCampaign(run / 'campaign', search, loss_spec=loss, seeds=saved['binding']['seeds'], world_binding=saved['binding']['world'])
    rows = []
    for report in campaign.state['reports']:
        for draw, observation in zip(report['draws'], report['observations']):
            measured, wires = [], []
            spec = SystemSpec.from_dict(draw['suggestion']['candidate'])
            for evidence in observation['metadata']['runs']:
                checkpoint = Path(evidence['checkpoint_path'])
                if file_sha256(checkpoint) != evidence['checkpoint_sha256']: raise ValueError('gradient native checkpoint hash changed')
                state = read_portable_checkpoint(checkpoint)
                kernel = NativeScienceKernel(spec, checkpoint=state['native_system'])
                binding, world = state['portable']['contract']['binding'], saved['binding']['world']
                if (binding['cell'] != spec.fingerprint or binding['model_revision'] != world['model_digest']
                    or binding['corpus_sha256'] != world['corpus_sha256'] or binding['science_config']['source_commit'] != world['source_commit']):
                    raise ValueError('gradient world/model/source binding mismatch')
                rounds = [r for p in state['paper_tracker']['papers'] for r in p['review_history']]
                authors = [a for a in state['ecosystem_data']['agents'] if a['can_author']]
                counts = {'native.accepted_decisions': sum(r['decision'] == 'accept' for r in rounds),
                    'native.rejected_decisions': sum(r['decision'] == 'reject' for r in rounds),
                    'native.review_records': sum(len(r['reviews']) for r in rounds),
                    'native.final_active_authors': sum(a['is_active'] for a in authors),
                    'native.final_author_resources': sum(a['resources'] for a in authors),
                    'native.institutional_context_deliveries': sum(e.event_type == 'native.system.context_delivered' for e in kernel.events)}
                measured.append({'run_id': evidence['run_id'], 'system_fingerprint': spec.fingerprint,
                    'measurement_schema': 'scienceutopia.native-domain-measurements.v1',
                    'metrics': {k: {'status': 'measured', 'value': v} for k, v in counts.items()}})
                wires.append(wire_summary(run / 'runs' / evidence['run_id'], needle='advisory-feedback', required=True))
            if measured != observation['metadata']['measurements'] or evaluate_loss(loss, measured) != observation['metadata']['loss_evaluation']:
                raise ValueError('gradient measured native losses changed')
            rows.append({'candidate_fingerprint': spec.fingerprint, 'loss': observation['loss'], 'measurements': measured, 'wire': wires})
    if file_sha256(saved_path) != before: raise ValueError('read-only gradient audit changed state')
    return {'schema': 'scienceutopia.native-feedback-gradient-audit.v2', 'binding': saved['binding'], 'rows': rows,
        'reports': [{k: r.get(k) for k in ('method', 'status', 'gradient', 'mean_before', 'mean_after',
                    'logits_before', 'logits_after', 'distribution', 'feedback_scope')} for r in saved['reports']],
        'state_sha256': before, 'raw_output_root': str(run), 'full_native_world_autograd': False,
        'verification': 'deterministic estimator replay, independent checkpoint-derived losses, pinned fixed model, actual request hashes and unchanged campaign state'}


def ui_audit(queue_path, job_id, loss=None):
    from utopia.optimization.native_jobs import NativeJobQueue
    from scripts.audit_native_design_loop import audit
    queue = NativeJobQueue(queue_path)
    job = queue.get(job_id)
    _, request = queue._row(job_id)
    if loss is not None and digest(loss) != digest(request['loss_spec']):
        raise ValueError('supplied loss differs from the exact UI-submitted LossSpec; omit --loss to audit its frozen request')
    loss = request['loss_spec']
    if job['status'] != 'complete': raise ValueError('completed actual UI job required')
    envelope = queue.evidence(job_id)
    result = audit(queue.directory / job_id, loss, job['years'], require_completion=False)
    if result['rows'][0]['loss'] != job['result']['native_loss']: raise ValueError('UI job score differs from native audit')
    return {'schema': 'scienceutopia.native-ui-roundtrip-audit.v2', 'job': job, 'native_audit': result,
            'viewer_sha256': digest(envelope), 'scope': 'explicit browser-edited branch; not automatic optimizer or same-society migration'}


if __name__ == '__main__':
    import argparse
    from utopia.optimization.loss import load_loss_spec
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode', choices=['source', 'gradient', 'ui'])
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--loss', type=Path)
    parser.add_argument('--job-id')
    parser.add_argument('--require-wire', action='store_true')
    args = parser.parse_args()
    if args.mode != 'ui' and args.loss is None:
        parser.error('--loss required for source and gradient audits')
    loss = load_loss_spec(args.loss) if args.loss is not None else None
    if args.mode == 'source': result = source_audit(args.run.resolve(), loss, require_wire=args.require_wire)
    elif args.mode == 'gradient': result = gradient_audit(args.run.resolve(), loss)
    else: result = ui_audit(args.run.resolve(), args.job_id, loss)
    print(json.dumps(result, ensure_ascii=False, indent=2, allow_nan=False))
