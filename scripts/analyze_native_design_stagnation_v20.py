#!/usr/bin/env python3
"""Read-only archived wire/operand diagnosis. No generation or code execution."""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.analyze_native_staged_search_v15 import _inside, _inventory
from utopia.optimization.native_authoring_ir import _read, resolve_address
from utopia.optimization.native_jobs import pinned_revision
from utopia.system.design_patch import digest
from utopia.utils.data_utils import write_json_atomic

FORBIDDEN = 'Explicit retention is legal; do not invent a candidate or a measured outcome.'
PERMITTED = 'You may invent arbitrary literal Python'


def analyze(run, audit_path, *, source_commit):
    run, audit_path = Path(run).resolve(), Path(audit_path).resolve()
    audit = json.loads(audit_path.read_text())
    if audit['content_sha256'] != digest({k: v for k, v in audit.items() if k != 'content_sha256'}):
        raise ValueError('archived audit content hash differs')
    before = _inventory(run)
    if before != audit['audit']['raw_input_sha256s']:
        raise ValueError('archived raw inventory changed')
    try:
        rows, errors, edits = [], Counter(), []
        for relative in sorted(before):
            path = Path(relative)
            if '/authoring/generation-' not in relative or not path.name.startswith('step-') or not relative.endswith('.completed.json'):
                continue
            completed = json.loads(_inside(run, relative).read_text())
            transport = completed['model_reply']['transport']
            wire = transport['request_wire_utf8']
            if hashlib.sha256(wire.encode()).hexdigest() != transport['request_wire_sha256']:
                raise ValueError('archived wire bytes/hash differ')
            payload = json.loads(wire)
            if payload != transport['request_payload']:
                raise ValueError('archived parsed wire differs from payload')
            messages = payload['messages']
            rows.append({'path': relative, 'completed_file_sha256': before[relative],
                'request_wire_sha256': transport['request_wire_sha256'],
                'SYSTEM_permits_candidate_invention': any(m['role'] == 'system' and PERMITTED in m['content'] for m in messages),
                'USER_narration_forbids_candidate_invention': any(m['role'] == 'user' and FORBIDDEN in m['content'] for m in messages)})
            transition = completed['transition'] or {}
            for error in transition.get('errors', []):
                errors[error['message']] += 1
            action = completed['model_reply']['output']
            if not isinstance(action, dict) or action.get('tool') != 'edit':
                continue
            binding = json.loads(_inside(run, str(path.parent / 'request.json')).read_text())
            parent = binding['request']['parent_system']
            if transition['document_before_sha256'] != digest(parent):
                raise ValueError('operand comparison requires the actual unchanged parent')
            for index, operation in enumerate(action['operations']):
                if operation['op'] != 'replace':
                    raise ValueError('this archive diagnosis requires literal replace operands')
                target = resolve_address(parent, operation, stage='read-only-v20-operand-diagnosis')
                operand = operation['value']
                existing = _read(parent, target, stage='read-only-v20-operand-diagnosis')
                edits.append({'step_path': relative, 'operation_index': index,
                    'resolved_path': target, 'literal_operand_sha256': digest(operand),
                    'parent_value_sha256': digest(existing), 'literal_operand_equals_parent': digest(operand) == digest(existing),
                    'actually_applied': transition['ok']})
        if len(rows) != audit['designer_costs']['recorded_POST_attempts']:
            raise ValueError('wire inspection does not cover all actual POSTs')
        result = {'schema': 'scienceutopia.native-design-stagnation-diagnosis.v20',
            'classification': 'read-only-archive-diagnosis-not-new-design-performance',
            'analysis_source_commit': source_commit, 'original_actual_source_commit': audit['source_commit'],
            'original_audit_content_sha256': audit['content_sha256'],
            'analysis_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'raw_inventory_sha256': digest(before), 'raw_files_verified_unchanged': len(before),
            'contradictory_literal_narration': FORBIDDEN, 'permissive_SYSTEM_literal': PERMITTED,
            'actual_POSTs': len(rows), 'wire_coverage': rows, 'attempted_edit_operands': edits,
            'tool_error_counts': dict(sorted(errors.items())),
            'all_POSTs_contain_conflicting_invention_instructions': bool(rows) and all(
                row['SYSTEM_permits_candidate_invention'] and row['USER_narration_forbids_candidate_invention'] for row in rows),
            'all_edit_operands_equal_parent': bool(edits) and all(e['literal_operand_equals_parent'] for e in edits),
            'new_model_POSTs': 0, 'new_native_worlds': 0, 'source_executions': 0,
            'causal_sufficiency_established': False,
            'interpretation': 'The source-owned turn task contradicts the permitted candidate invention. '
                'Its presence on actual wires is established, not its causal sufficiency for retention. '
                'All literal edit operands equal the parent, including rejected edits: accepting extra '
                'metadata alone would not recover a changed institutional source in this archive.'}
        result['content_sha256'] = digest(result)
        return result
    finally:
        if _inventory(run) != before:
            raise ValueError('raw evidence changed during diagnostics')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists() or args.output.resolve().is_relative_to(args.run.resolve()):
        raise ValueError('diagnostic output must be fresh and outside immutable raw evidence')
    result = analyze(args.run, args.audit, source_commit=pinned_revision(ROOT))
    write_json_atomic(args.output, result, sort_keys=True, allow_nan=False)
    print(json.dumps({key: result[key] for key in ('content_sha256', 'actual_POSTs',
        'all_POSTs_contain_conflicting_invention_instructions', 'all_edit_operands_equal_parent', 'new_model_POSTs')}))


if __name__ == '__main__':
    main()
