#!/usr/bin/env python3
"""Read-only native campaign/checkpoint/journal audit; no model calls or reruns."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sqlite3
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def audit(run, loss, years):
    from utopia.optimization.loss import evaluate_loss
    from utopia.optimization.native_design import NativeDesignCampaign
    from utopia.replay.converter import ArtifactBundle, convert_artifacts
    from utopia.replay.events import canonical_event_stream_hash
    from utopia.replay.native_design import native_design_replay
    from utopia.replay.projector import replay
    from utopia.runtime.checkpointing import read_portable_checkpoint
    from utopia.system import SystemSpec
    from utopia.system.native_kernel import NativeScienceKernel
    from utopia.utils.data_utils import file_sha256

    state_path = run / 'campaign' / 'native-design-state.json'
    before = file_sha256(state_path)
    saved = json.loads(state_path.read_text())
    if not saved['records'] or saved['pending'] is not None:
        raise ValueError('audit requires a terminal nonempty campaign')
    initial = SystemSpec.from_dict(saved['records'][0]['parent_system'])
    campaign = NativeDesignCampaign(run / 'campaign', initial_system=initial,
        loss_spec=loss, seeds=saved['binding']['seeds'], world_binding=saved['binding']['world'])
    rows = []
    for record in campaign.state['records']:
        obs = record['observation']
        measured = []
        runs = []
        for evidence in obs['metadata']['runs']:
            cell = run / 'runs' / evidence['run_id']
            checkpoint = cell / 'simulation' / 'checkpoints' / 'native-design' / f'portable_checkpoint_year_{years}.json.gz'
            state = read_portable_checkpoint(checkpoint)
            spec = SystemSpec.from_dict(record['suggestion']['candidate'])
            kernel = NativeScienceKernel(spec, checkpoint=state['native_system'])
            if kernel.last_year != years or kernel.to_dict()['event_stream_hash'] != evidence['event_stream_hash']:
                raise ValueError('native checkpoint year or event hash mismatch')
            binding = state['portable']['contract']['binding']
            world = saved['binding']['world']
            if (binding['cell'] != spec.fingerprint or binding['seed'] != evidence['seed']
                    or binding['model_revision'] != world['model_digest']
                    or binding['corpus_sha256'] != world['corpus_sha256']
                    or binding['science_config']['source_commit'] != world['source_commit']):
                raise ValueError('checkpoint design/world binding mismatch')
            papers = state['paper_tracker']['papers']
            rounds = [r for p in papers for r in p['review_history']]
            authors = [a for a in state['ecosystem_data']['agents'] if a['can_author']]
            counts = {'native.accepted_decisions': sum(r['decision'] == 'accept' for r in rounds),
                'native.rejected_decisions': sum(r['decision'] == 'reject' for r in rounds),
                'native.review_records': sum(len(r['reviews']) for r in rounds),
                'native.final_active_authors': sum(a['is_active'] for a in authors),
                'native.final_author_resources': sum(a['resources'] for a in authors),
                'native.institutional_context_deliveries': sum(e.event_type == 'native.system.context_delivered' for e in kernel.events)}
            measurement = {'run_id': evidence['run_id'], 'system_fingerprint': spec.fingerprint,
                'measurement_schema': 'scienceutopia.native-domain-measurements.v1',
                'metrics': {k: {'status': 'measured', 'value': v} for k, v in counts.items()}}
            measured.append(measurement)
            events = convert_artifacts(ArtifactBundle.discover(checkpoint))
            view = native_design_replay(checkpoint, expected_system_fingerprint=spec.fingerprint,
                                       label='Native engineering pilot, not scientific improvement')
            projected = replay(events)
            if projected.completed_years != list(range(1, years + 1)):
                raise ValueError('canonical replay years differ')
            db_path = cell / 'replies' / 'responses.sqlite'
            db = sqlite3.connect(db_path.as_uri() + '?mode=ro', uri=True)
            try:
                cache_binding, = db.execute('SELECT binding FROM metadata').fetchone()
                if json.loads(cache_binding) != binding:
                    raise ValueError('response journal and checkpoint bindings differ')
                replies = db.execute('SELECT outcome,data,data_sha FROM replies').fetchall()
                if any(outcome != 'response' or hashlib.sha256(data.encode()).hexdigest() != sha for outcome, data, sha in replies):
                    raise ValueError('response journal integrity failure')
                if len(replies) != state['portable']['response_cache_count']:
                    raise ValueError('response journal and completed checkpoint counts differ')
            finally:
                db.close()
            runs.append({'run_id': evidence['run_id'], 'checkpoint': str(checkpoint),
                'checkpoint_sha256': file_sha256(checkpoint), 'response_cache_sha256': file_sha256(db_path),
                'responses': len(replies), 'llm_call_stats': state['portable']['llm_call_stats'],
                'papers': len(papers), 'counts': counts, 'native_event_counts': dict(Counter(e.event_type for e in kernel.events)),
                'native_event_stream_hash': evidence['event_stream_hash'],
                'canonical_event_count': len(events), 'canonical_event_stream_hash': canonical_event_stream_hash(events),
                'web_stream_hash': view['web_stream_hash'], 'replayed_years': projected.completed_years})
        if measured != obs['metadata']['measurements'] or evaluate_loss(loss, measured) != obs['metadata']['loss_evaluation']:
            raise ValueError('independently rederived checkpoint measurements/loss differ')
        rows.append({'suggestion_id': record['suggestion']['suggestion_id'],
            'based_on_observation_id': record['suggestion']['based_on_observation_id'],
            'status': obs['status'], 'loss': obs['loss'], 'difference': record['difference'],
            'technical_failures': obs['metadata']['technical_failures'], 'runs': runs})
    if file_sha256(state_path) != before:
        raise ValueError('read-only audit changed campaign state')
    completion = json.loads((run / 'completion.json').read_text())
    if len(rows) != completion['budget']:
        raise ValueError('terminal record count and declared budget differ')
    return {'schema': 'scienceutopia.native-design-loop-audit.v1', 'binding': saved['binding'],
        'campaign_sha256': before, 'completion': {k: v for k, v in completion.items() if k != 'incumbent'},
        'rows': rows, 'verification': 'checkpoint-derived measurements/loss, lineage, kernel restore, canonical replay, response journal hashes and read-only reopen passed',
        'limits': ['development engineering objective, not scientific quality',
                   'developer-authored example, not LLM invention', 'no full native autograd or live game intervention',
                   'response journal integrity, not an independent full HTTP wire audit']}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--loss', type=Path, required=True)
    parser.add_argument('--years', type=int, default=4)
    args = parser.parse_args()
    from utopia.optimization.loss import load_loss_spec
    print(json.dumps(audit(args.run.resolve(), load_loss_spec(args.loss), args.years), ensure_ascii=False, indent=2))


if __name__ == '__main__':
    main()
