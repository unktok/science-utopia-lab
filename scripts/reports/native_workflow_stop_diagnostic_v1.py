"""Read an actually stopped workflow prefix; never fabricate a closed audit.

Compare full literal requests and committed reply choices with the original
closed R7. A prior reply never fills the new unknown response or supplies loss.
"""
import argparse
import fcntl
import hashlib
import json
from pathlib import Path
import sqlite3

from scripts.analyze_native_open_v7 import _inventory
from scripts.reports.native_observed_request_classes_v1 import sequence
from scripts.run_native_planning_fixed_evaluation_v1 import origin_evidence
from scripts.run_pre_scale_completion_chain_v1 import process_identity
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]


def cell_records(cell):
    wires = [json.loads(v) for v in (cell / 'wire-requests.jsonl').read_text().splitlines()]
    with sqlite3.connect((cell / 'replies/responses.sqlite').resolve().as_uri() + '?mode=ro', uri=True) as db:
        replies = db.execute('SELECT payload_sha,outcome,data,data_sha FROM replies ORDER BY rowid').fetchall()
    return wires, replies


def prefix(left_wires, left_replies, right_wires, right_replies):
    left = sequence(left_wires, left_replies); right = sequence(right_wires, right_replies)
    request_equal = 0
    for a, b in zip(left_wires, right_wires):
        if a['payload'] != b['payload']:
            break
        request_equal += 1
    reply_equal = 0
    for a, b in zip(left_replies, right_replies):
        if a[0] != b[0] or json.loads(a[2])['choices'] != json.loads(b[2])['choices']:
            break
        reply_equal += 1
    if not left_wires:
        raise ValueError('actual stopped HTTP prefix required')
    last = left_wires[-1]['payload_sha256']
    previous = [{'response_ordinal': i, 'body_sha256': row[3],
        'usage': json.loads(row[2]).get('usage')} for i, row in enumerate(right_replies) if row[0] == last]
    return {'stopped_requests': left, 'prior_complete_requests': right,
        'equal_full_request_prefix_count': request_equal,
        'equal_committed_literal_choice_prefix_count': reply_equal,
        'last_request_sha256': last,
        'prior_matching_request_ordinals': [i for i, row in enumerate(right_wires) if row['payload_sha256'] == last],
        'prior_matching_committed_responses': previous,
        'new_missing_response_recovered_or_filled': False,
        'whole_world_equivalence_claimed': False, 'timeout_cause_identified': False}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--frozen-source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    root, frozen, out = args.run.resolve(), args.frozen_source.resolve(), args.output.resolve()
    if out.exists() or out.is_relative_to(root) or out.is_relative_to(frozen):
        raise ValueError('fresh output outside stopped science required')
    analysis_source = pinned_revision(ROOT)
    read = lambda path: checked(json.loads(path.read_text()))
    with (root / 'writer.lock').open('r') as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        before = _inventory(root)
        plan, start, end = [read(root / name) for name in ('plan.json', 'started.json', 'terminal.json')]
        if (plan['schema'] != 'scienceutopia.native-workflow-objective-loop.v1.plan'
                or plan['source_commit'] != pinned_revision(frozen)
                or start['plan_sha256'] != plan['content_sha256'] or process_identity(start['pid']) is not None
                or end['status'] != 'stopped' or end['stage'] != 'references'
                or end['error_type'] != 'PortableStop' or 'APITimeoutError' not in end['error']
                or end['consumed_slots'] != 0 or end['observations'] != 0
                or (root / 'selection.json').exists()):
            raise ValueError('original stopped pre-selection workflow transport boundary required')
        original, audit = origin_evidence(plan['origin'])
        prior_root = Path(plan['origin']['run'])
        prior_before = _inventory(prior_root)
        first = plan['reference_order'][0]
        if first != 'R7-original':
            raise ValueError('exact original first R7 reference required')
        starts = [read(v) for v in (root / 'references').glob('*/started.json')]
        if len(starts) != 1 or starts[0]['seed'] != 61001:
            raise ValueError('single actual first reference prefix required')
        current = root / 'references/R7-original/worlds/workflow-reference-r7-original-s61001'
        previous = prior_root / 'references/assignment-reserve21-no-review-all/worlds/reference-assignment-reserve21-no-review-all-s61001'
        reference = next(w for w in audit['worlds'] if w['identity'] == previous.name.removesuffix('-s61001'))
        if reference['status'] != 'complete' or reference['seed'] != 61001:
            raise ValueError('exact normally audited previous R7 required')
        wires, replies = cell_records(current); old_wires, old_replies = cell_records(previous)
        comparison = prefix(wires, replies, old_wires, old_replies)
        certificates = list((root / 'initial-readiness/author').glob('*/certificate.json'))
        if len(certificates) != 1 or read(certificates[0])['passed'] is not True:
            raise ValueError('original successful initial workflow calibration required')
        payload = wires[-1]['payload']
        result = {'schema': 'scienceutopia.native-workflow-stop-prefix-diagnostic.v1',
            'analysis_source_commit': analysis_source, 'scientific_source_commit': plan['source_commit'],
            'plan_content_sha256': plan['content_sha256'], 'original_start': start, 'original_terminal': end,
            'current_raw_inventory_sha256': digest(before), 'current_raw_files': len(before),
            'prior_audit_content_sha256': audit['content_sha256'],
            'prior_raw_inventory_sha256': digest(prior_before),
            'initial_certificate_file_sha256': file_sha256(certificates[0]),
            'comparison': comparison,
            'last_request_summary': {'year': wires[-1]['year'], 'model': payload['model'],
                'max_tokens': payload['max_tokens'], 'reasoning_effort': payload.get('reasoning_effort'),
                'schema_name': payload['response_format']['json_schema']['name'],
                'message_roles_and_character_counts': [[m['role'], len(m['content'])] for m in payload['messages']]},
            'checkpoints': {str(p.relative_to(current)): file_sha256(p)
                for p in sorted(current.rglob('portable_checkpoint_year_*.json.gz'))},
            'scope': {'normal_full_audit': False, 'completed_new_reference_worlds': 0,
                'own_slots_consumed': 0, 'new_model_calls': 0, 'new_code_executions': 0,
                'new_native_worlds': 0, 'scientific_loss_imputed': False,
                'unknown_response_resolved': False, 'timeout_cause_proved': False,
                'publication_ready': False}}
        if (before != _inventory(root) or prior_before != _inventory(prior_root)
                or pinned_revision(frozen) != plan['source_commit'] or pinned_revision(ROOT) != analysis_source):
            raise ValueError('original evidence or readout source changed')
        save(out, result)
        print(json.dumps({'input_prefix': comparison['equal_full_request_prefix_count'],
            'reply_choice_prefix': comparison['equal_committed_literal_choice_prefix_count'],
            'missing_replies': comparison['stopped_requests']['wire_inputs_without_committed_reply'],
            'new_model_calls': 0, 'normal_full_audit': False}))


if __name__ == '__main__':
    main()
