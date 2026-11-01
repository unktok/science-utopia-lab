#!/usr/bin/env python3
"""Read-only checkpoint reconstruction and cross-objective native-loop audit.

Does not import the simulator's measurement adapter, run models, change records,
or treat logical reuse as an independently executed replicate.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def checkpoint_measurements(path, run_id, fingerprint):
    """Recompute all eight native metrics from a completed domain checkpoint.

    ``fingerprint`` is the exact expected executed SystemSpec fingerprint.
    Callers must separately verify an archived external checkpoint_sha256 when
    adopting evidence; the portable reader validates its serialization envelope,
    NOT a cryptographic file hash. Kernel event provenance is checked on restore.
    """
    from utopia.runtime.checkpointing import read_portable_checkpoint
    from utopia.system import SystemSpec
    from utopia.system.native_kernel import NativeScienceKernel

    state = read_portable_checkpoint(Path(path).resolve())
    spec = SystemSpec.from_dict(state['native_system']['spec'])
    if spec.fingerprint != fingerprint:
        raise ValueError('checkpoint system fingerprint differs from expected executed design')
    kernel = NativeScienceKernel(spec, checkpoint=state['native_system'])
    years = state['portable']['contract']['binding']['science_config']['years']
    if kernel.last_year != years or state['year'] != years or state['phase'] != 5:
        raise ValueError('measurement requires a completed native checkpoint')
    decisions = [d for paper in state['paper_tracker']['papers'] for d in paper['review_history']]
    accepted = [d for d in decisions if d.get('decision') == 'accept']
    authors = [a for a in state['ecosystem_data']['agents'] if a['can_author']]
    values = {
        'native.accepted_decisions': len(accepted),
        'native.rejected_decisions': sum(d.get('decision') == 'reject' for d in decisions),
        'native.review_records': sum(len(d.get('reviews', [])) for d in decisions),
        'native.final_active_authors': sum(a['is_active'] for a in authors),
        'native.final_author_resources': sum(a['resources'] for a in authors),
        'native.institutional_context_deliveries': sum(e.event_type == 'native.system.context_delivered' for e in kernel.events),
        'native.accepted_unreviewed_decisions': sum(not d.get('reviews', []) for d in accepted),
    }
    # Independent implementation: construct per-accepted-observation means from
    # peer replies, not persisted final_score / review-history score.
    means = []
    invalid = False
    for decision in accepted:
        replies = decision.get('reviews', [])
        scores = [reply.get('overall_score') for reply in replies]
        if any(type(score) not in (int, float) or not math.isfinite(score) for score in scores):
            invalid = True
            break
        means.append(math.fsum(scores) / len(scores) if scores else 0.0)
    metrics = {key: {'status': 'measured', 'value': value} for key, value in values.items()}
    metrics['native.accepted_peer_score_sum'] = (
        {'status': 'unavailable', 'value': None,
         'reason': 'accepted decision has a missing or nonfinite raw reviewer score'} if invalid else
        {'status': 'measured', 'value': sum(means)})
    return {'run_id': run_id, 'system_fingerprint': fingerprint,
            'measurement_schema': 'scienceutopia.native-domain-measurements.v1', 'metrics': metrics}


def audit_campaign(run, loss, comparison_losses=None, *, require_completion=True):
    from utopia.optimization.loss import evaluate_loss
    from utopia.optimization.native_design import NativeDesignCampaign
    from utopia.optimization.native_feedback import checked_native_state
    from utopia.optimization.native_transition_data import physical_initial_identity
    from utopia.system import SystemSpec
    from utopia.system.code_mechanisms import sha
    from utopia.utils.data_utils import file_sha256
    from utopia.runtime.checkpointing import read_portable_checkpoint

    run = Path(run).resolve()
    state_path = run / 'campaign/native-design-state.json'
    original_sha = file_sha256(state_path)
    saved = json.loads(state_path.read_text())
    if not saved['records'] or saved['pending'] is not None:
        raise ValueError('audit requires a terminal nonempty campaign')
    # Reopening checks exact patches, candidate lineage, suggestion IDs,
    # incumbent parenting and loss arithmetic, without writing existing state.
    controller = NativeDesignCampaign(run / 'campaign',
        initial_system=SystemSpec.from_dict(saved['records'][0]['parent_system']),
        loss_spec=loss, seeds=saved['binding']['seeds'], world_binding=saved['binding']['world'])
    objectives = {loss['id']: loss, **(comparison_losses or {})}
    rows = []
    for record in controller.state['records']:
        obs = record['observation']
        spec = SystemSpec.from_dict(record['suggestion']['candidate'])
        measurements, evidence_rows = [], []
        for evidence in obs['metadata']['runs']:
            checkpoint = Path(evidence['checkpoint_path']).resolve()
            state, kernel = checked_native_state(record, evidence)
            world = saved['binding']['world']
            binding = state['portable']['contract']['binding']
            if (binding['cell'] != spec.fingerprint or binding['seed'] != evidence['seed']
                    or binding['model_revision'] != world['model_digest']
                    or binding['corpus_sha256'] != world['corpus_sha256']
                    or binding['science_config']['source_commit'] != world['source_commit']):
                raise ValueError('checkpoint executed design/model/corpus/source/seed mismatch')
            measured = checkpoint_measurements(checkpoint, evidence['run_id'], spec.fingerprint)
            measurements.append(measured)
            code = []
            for node in spec.mechanisms:
                if node.implementation != 'code.python.v1':
                    continue
                executions = [e for e in kernel.events if e.event_type == 'generated.code_executed'
                              and e.provenance.get('mechanism_id') == node.mechanism_id]
                if not executions or any(e.payload['artifact_sha256'] != sha(node.parameters['code_artifact'])
                        or e.payload['image_id'] != node.parameters['runtime_image_id'] for e in executions):
                    raise ValueError('executed institution source/image differs from suggested design')
                code.append({'mechanism_id': node.mechanism_id,
                    'source_sha256': sha(node.parameters['code_artifact']['source']),
                    'artifact_sha256': sha(node.parameters['code_artifact']),
                    'image_id': node.parameters['runtime_image_id'], 'executions': len(executions)})
            cell = checkpoint.parent.parent.parent.parent
            journal = cell / 'replies/responses.sqlite'
            db = sqlite3.connect(journal.as_uri() + '?mode=ro', uri=True)
            try:
                if json.loads(db.execute('SELECT binding FROM metadata').fetchone()[0]) != binding:
                    raise ValueError('response journal binding differs from checkpoint')
                replies = db.execute('SELECT outcome,data,data_sha FROM replies').fetchall()
                if len(replies) != state['portable']['response_cache_count'] or any(
                        outcome != 'response' or hashlib.sha256(data.encode()).hexdigest() != digest
                        for outcome, data, digest in replies):
                    raise ValueError('response journal count or content hash differs')
            finally:
                db.close()
            initial_path = checkpoint.parent / 'portable_checkpoint_year_0.json.gz'
            evidence_rows.append({'run_id': evidence['run_id'], 'seed': evidence['seed'],
                'checkpoint': str(checkpoint), 'checkpoint_sha256': file_sha256(checkpoint),
                'initial_physical_state_sha256': physical_initial_identity(read_portable_checkpoint(initial_path)),
                'response_count': len(replies), 'response_journal_sha256': file_sha256(journal),
                'native_event_stream_hash': evidence['event_stream_hash'], 'executed_code': code})
        recorded = obs['metadata']['measurements']
        if measurements != recorded:
            raise ValueError('checkpoint-reconstructed measurements differ from recorded observation')
        derived = evaluate_loss(loss, measurements)
        if derived != obs['metadata']['loss_evaluation'] or obs['loss'] != derived['loss']:
            raise ValueError('checkpoint-recomputed objective differs from recorded observation')
        rows.append({'suggestion_id': record['suggestion']['suggestion_id'],
            'based_on_observation_id': record['suggestion']['based_on_observation_id'],
            'system_fingerprint': spec.fingerprint, 'status': obs['status'], 'loss': obs['loss'],
            'difference': record['difference'], 'measurements': measurements, 'runs': evidence_rows,
            'cross_objective': {name: evaluate_loss(objective, measurements) for name, objective in objectives.items()},
            'technical_failures': obs['metadata']['technical_failures']})
    completion_path = run / 'completion.json'
    if require_completion and not completion_path.exists():
        raise ValueError('completed campaign receipt required')
    if completion_path.exists() and json.loads(completion_path.read_text())['budget'] != len(rows):
        raise ValueError('completed record count differs from declared budget')
    if file_sha256(state_path) != original_sha:
        raise ValueError('read-only audit changed campaign state')
    return {'schema': 'scienceutopia.native-objective-audit.v5', 'binding': saved['binding'],
        'campaign_sha256': original_sha, 'rows': rows,
        'loss_path': [r['loss'] for r in rows],
        'incumbent_suggestion_id': (controller.incumbent() or {}).get('suggestion', {}).get('suggestion_id'),
        'limits': ['engineering preferences, not scientific quality',
                   'cross-objective values reuse the same physical worlds, not independent replicates',
                   'development seeds; no held-out or full-world pathwise-gradient claim']}


def main():
    from utopia.optimization.loss import load_loss_spec
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--loss', type=Path, required=True)
    parser.add_argument('--compare-loss', type=Path, action='append', default=[])
    args = parser.parse_args()
    losses = [load_loss_spec(path) for path in args.compare_loss]
    print(json.dumps(audit_campaign(args.run, load_loss_spec(args.loss), {s['id']: s for s in losses}),
                     ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))


if __name__ == '__main__':
    main()
