#!/usr/bin/env python3
"""Prepare exact design transfer and independently audit fresh native REINFORCE.

Execution deliberately uses the existing run_native_discrete_policy.py. This
helper never imports archived losses as observations and makes no model calls.
"""
import argparse
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def prepare(source_campaign, selected, output):
    from utopia.system import SystemSpec, validate_system_spec
    from utopia.utils.data_utils import file_sha256, write_json_atomic
    source = json.loads(Path(source_campaign).read_text())
    baseline = source['records'][0]['suggestion']['candidate']
    winner = json.loads(Path(selected).read_text())
    if source['records'][-1]['suggestion']['candidate'] != winner:
        raise ValueError('selected design must be exact archived final proposal')
    designs = [baseline, winner]
    for design in designs:
        validate_system_spec(SystemSpec.from_dict(design)).require_valid()
    proof = {'schema': 'scienceutopia.live-native-policy-design-transfer.v5',
        'source_campaign_sha256': file_sha256(source_campaign),
        'selected_artifact_sha256': file_sha256(selected),
        'design_fingerprints': [SystemSpec.from_dict(d).fingerprint for d in designs],
        'scope': 'exact full design transfer only; no archived cost used for training',
        'design_origin': ['v3 baseline', 'v3 Qwen generated source winner'],
        'new_worlds_required': 2, 'new_world_years': 2, 'native_seed': 1301,
        'search_seed': 42, 'initial_logits': [0.0, 0.0],
        'sample_count': 2, 'batches': 1, 'fixed_baseline': 0.0,
        'learning_rate': 0.1,
        'no_redraw_rule': 'Preserve sampled actions, repeated actions and zero gradients; no retry for favorable results.'}
    output = Path(output)
    output.mkdir(parents=True, exist_ok=True)
    for name, value in [('designs.json', designs), ('transfer.json', proof)]:
        target = output / name
        if target.exists() and json.loads(target.read_text()) != value:
            raise ValueError('existing frozen transfer differs')
        write_json_atomic(target, value, sort_keys=True, allow_nan=False)
    return proof


def checkpoint_counts(state):
    papers = state['paper_tracker']['papers']
    rounds = [review for paper in papers for review in paper['review_history']]
    authors = [author for author in state['ecosystem_data']['agents'] if author['can_author']]
    events = state['native_system']['events']
    return {'native.accepted_decisions': sum(r['decision'] == 'accept' for r in rounds),
        'native.rejected_decisions': sum(r['decision'] == 'reject' for r in rounds),
        'native.review_records': sum(len(r['reviews']) for r in rounds),
        'native.final_active_authors': sum(a['is_active'] for a in authors),
        'native.final_author_resources': sum(a['resources'] for a in authors),
        'native.institutional_context_deliveries': sum(e['event_type'] == 'native.system.context_delivered' for e in events)}


def audit(directory, loss_path):
    from utopia.optimization.loss import evaluate_loss, load_loss_spec, loss_spec_sha256
    from utopia.optimization.native_discrete_policy import NativeDiscretePolicySearch
    from utopia.optimization.native_gradient import NativeGradientCampaign
    from utopia.runtime.checkpointing import read_portable_checkpoint
    from utopia.system import SystemSpec
    from utopia.system.code_mechanisms import sha as code_sha
    from utopia.system.native_kernel import NativeScienceKernel
    from utopia.utils.data_utils import file_sha256
    directory = Path(directory).resolve()
    before = {str(p.relative_to(directory)): file_sha256(p) for p in directory.rglob('*') if p.is_file()}
    path = directory / 'campaign' / 'native-gradient-state.json'
    state = json.loads(path.read_text())
    definition = state['binding']['search_definition']
    loss = load_loss_spec(loss_path)
    campaign = NativeGradientCampaign(directory / 'campaign',
        NativeDiscretePolicySearch.from_state(definition, loss_spec=loss),
        loss_spec=loss, seeds=state['binding']['seeds'], world_binding=state['binding']['world'])
    if len(campaign.state['reports']) != 1 or campaign.state['observations'] or campaign.state['search']['pending']:
        raise ValueError('exactly one terminal batch required')
    report = state['reports'][0]
    if len(report['draws']) != 2 or report['status'] != 'updated':
        raise ValueError('two successful fresh native draws required; failures remain null and unaudited as success')
    rows = []
    for draw, observation in zip(report['draws'], report['observations']):
        measured, proofs = [], []
        for run in observation['metadata']['runs']:
            checkpoint = Path(run['checkpoint_path'])
            payload = read_portable_checkpoint(checkpoint)
            design = SystemSpec.from_dict(observation['candidate'])
            kernel = NativeScienceKernel(design, checkpoint=payload['native_system'])
            if kernel.last_year != 2 or kernel.to_dict()['event_stream_hash'] != run['event_stream_hash']:
                raise ValueError('incomplete or changed native event stream')
            counts = checkpoint_counts(payload)
            measured.append({'run_id': run['run_id'], 'system_fingerprint': design.fingerprint,
                'measurement_schema': 'scienceutopia.native-domain-measurements.v1',
                'metrics': {key: {'status': 'measured', 'value': value} for key, value in counts.items()}})
            cell = directory / 'runs' / run['run_id']
            journal = cell / 'replies' / 'responses.sqlite'
            database = sqlite3.connect(journal.as_uri() + '?mode=ro', uri=True)
            try:
                journal_binding, = database.execute('SELECT binding FROM metadata').fetchone()
                replies = database.execute('SELECT outcome,data,data_sha FROM replies').fetchall()
            finally:
                database.close()
            if (json.loads(journal_binding) != payload['portable']['contract']['binding']
                    or len(replies) != payload['portable']['response_cache_count']
                    or any(kind != 'response' or hashlib.sha256(data.encode()).hexdigest() != digest for kind, data, digest in replies)):
                raise ValueError('native response journal/checkpoint integrity differs')
            receipts = []
            for node in design.mechanisms:
                if node.implementation == 'code.python.v1':
                    executed = [e for e in kernel.events if e.event_type == 'generated.code_executed' and e.provenance['mechanism_id'] == node.mechanism_id]
                    if len(executed) != 2 or any(e.payload['artifact_sha256'] != code_sha(node.parameters['code_artifact']) or e.payload['image_id'] != node.parameters['runtime_image_id'] for e in executed):
                        raise ValueError('exact frozen code/image was not executed in every year')
                    receipts.append({'mechanism_id': node.mechanism_id, 'artifact_sha256': code_sha(node.parameters['code_artifact']), 'image_id': node.parameters['runtime_image_id'], 'executions': len(executed)})
            proofs.append({'run_id': run['run_id'], 'checkpoint_sha256': file_sha256(checkpoint),
                'response_journal_sha256': file_sha256(journal), 'responses': len(replies),
                'counts': counts, 'executed_code': receipts, 'event_stream_hash': run['event_stream_hash']})
        independently_evaluated = evaluate_loss(loss, measured)
        if measured != observation['metadata']['measurements'] or independently_evaluated != observation['metadata']['loss_evaluation'] or independently_evaluated['loss'] != observation['loss']:
            raise ValueError('independent checkpoint loss re-extraction differs')
        rows.append({'action': draw['action'], 'suggestion_id': observation['suggestion_id'],
            'fingerprint': SystemSpec.from_dict(observation['candidate']).fingerprint,
            'loss': independently_evaluated['loss'], 'runs': proofs})
    # Independent analytical categorical score: d log p(action)/dz_j = 1[a=j]-p_j.
    logits = report['logits_before']
    weights = [math.exp(v - max(logits)) for v in logits]
    probabilities = [v / sum(weights) for v in weights]
    gradient = [sum((r['loss'] - report['baseline']) * (int(r['action'] == j) - probabilities[j]) for r in rows) / len(rows) for j in range(len(logits))]
    updated = [v - definition['learning_rate'] * g for v, g in zip(logits, gradient)]
    if any(abs(a - b) > 1e-14 for a, b in zip(gradient, report['gradient'])) or any(abs(a - b) > 1e-14 for a, b in zip(updated, report['logits_after'])):
        raise ValueError('policy autograd differs from independently analytical exact score update')
    after = {str(p.relative_to(directory)): file_sha256(p) for p in directory.rglob('*') if p.is_file()}
    if before != after:
        raise ValueError('read-only independent audit changed raw campaign artifacts')
    return {'schema': 'scienceutopia.fresh-native-policy-audit.v5',
        'binding': state['binding'], 'loss_spec_sha256': loss_spec_sha256(loss),
        'campaign_sha256': before['campaign/native-gradient-state.json'],
        'rows': rows, 'losses': [r['loss'] for r in rows], 'actions': [r['action'] for r in rows],
        'gradient': gradient, 'logits_before': logits, 'logits_after': updated,
        'probabilities_before': probabilities, 'new_native_executions': len(rows),
        'responses': sum(p['responses'] for r in rows for p in r['runs']),
        'raw_files_verified_unchanged': len(before), 'audit_new_model_calls': 0,
        'limits': ['one noisy batch, no convergence or held-out benefit claim',
            'preexisting full designs; not new code/topology invention',
            'exact policy score autograd, not pathwise native-world or LLM differentiation',
            'gameable acceptance-count engineering objective, not scientific quality']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest='command', required=True)
    preparation = commands.add_parser('prepare')
    preparation.add_argument('--source-campaign', type=Path, required=True)
    preparation.add_argument('--selected', type=Path, required=True)
    preparation.add_argument('--output', type=Path, required=True)
    auditing = commands.add_parser('audit')
    auditing.add_argument('--run', type=Path, required=True)
    auditing.add_argument('--loss', type=Path, required=True)
    args = parser.parse_args()
    result = prepare(args.source_campaign, args.selected, args.output) if args.command == 'prepare' else audit(args.run, args.loss)
    print(json.dumps(result, indent=2, sort_keys=True))


if __name__ == '__main__':
    main()
