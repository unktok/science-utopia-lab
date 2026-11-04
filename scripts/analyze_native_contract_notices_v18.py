#!/usr/bin/env python3
"""Read archived JSON only. Not a native replay, model probe or code execution."""
import argparse
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scripts.analyze_native_staged_search_v15 import _inside, _inventory
from utopia.optimization.native_contract_notices import contract_notices
from utopia.optimization.native_jobs import pinned_revision
from utopia.system.design_patch import digest
from utopia.utils.data_utils import write_json_atomic


def analyze(run, audit_path, *, source_commit):
    run = Path(run).resolve()
    audit_path = Path(audit_path).resolve()
    audit = json.loads(audit_path.read_text())
    if audit.get('content_sha256') != digest({key: value for key, value in audit.items() if key != 'content_sha256'}):
        raise ValueError('archived audit content hash differs')
    before = _inventory(run)
    if before != audit['audit']['raw_input_sha256s']:
        raise ValueError('archived raw inventory differs from the source-matched audit')
    try:
        systems, authority = [], []
        for relative in sorted(before):
            if relative.endswith('/system.json'):
                document = json.loads(_inside(run, relative).read_text())
                systems.append({'path': relative, 'file_sha256': before[relative],
                    'system_document_sha256': digest(document), 'notices': contract_notices(document)})
            if '/authoring/generation-' in relative and Path(relative).name.startswith('step-') and relative.endswith('.completed.json'):
                completed = json.loads(_inside(run, relative).read_text())
                transport = completed['model_reply'].get('transport') or {}
                if 'request_payload' not in transport:
                    continue
                messages = transport['request_payload']['messages']
                system = messages[0] if messages else {}
                text = system.get('content', '')
                authority.append({'path': relative, 'file_sha256': before[relative],
                    'first_message_role': system.get('role'), 'system_message_sha256': digest(text),
                    'trusted_protocol_in_system': text.startswith('TRUSTED INSTITUTION-AUTHORING PROTOCOL\n'),
                    'trusted_ABI_in_system': 'TRUSTED EXECUTION ABI AND DISTRIBUTION CONTRACT\n' in text,
                    'objective_directive_in_system': 'Minimize the exact_loss_spec supplied in the session data.' in text})
        if len(authority) != audit['designer_costs']['recorded_POST_attempts']:
            raise ValueError('authority coverage does not account for all archived designer POSTs')
        if len(systems) != audit['physical_world_directory_count']:
            raise ValueError('contract notice coverage does not account for all archived world documents')
        from utopia.optimization import native_contract_notices
        from utopia.system import code_mechanisms
        result = {'schema': 'scienceutopia.native-contract-notices-offline.v18',
            'classification': 'offline-archive-diagnostics-not-an-actual-design-experiment',
            'analysis_source_commit': source_commit, 'original_actual_source_commit': audit['source_commit'],
            'original_audit_content_sha256': audit['content_sha256'],
            'original_audit_file_sha256': hashlib.sha256(audit_path.read_bytes()).hexdigest(),
            'analysis_script_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
            'notice_source_sha256': hashlib.sha256(Path(native_contract_notices.__file__).read_bytes()).hexdigest(),
            'code_ABI_source_sha256': hashlib.sha256(Path(code_mechanisms.__file__).read_bytes()).hexdigest(),
            'raw_inventory_sha256': digest(before), 'raw_files_verified_unchanged': len(before),
            'systems': systems, 'authority_coverage': authority,
            'all_archived_POSTs_have_trusted_authority_in_SYSTEM': all(row['first_message_role'] == 'system'
                and row['trusted_protocol_in_system'] and row['trusted_ABI_in_system']
                and row['objective_directive_in_system'] for row in authority) and bool(authority),
            'new_model_POSTs': 0, 'new_native_worlds': 0, 'source_executions': 0,
            'candidate_or_loss_changed': False, 'warnings_are_vetoes': False,
            'operational_goal_achieved': False,
            'scope': 'Counterfactual static notices on exact archived candidate documents plus actual original '
                'wire-role inspection. Does not show that an autonomous model follows the new notices.'}
        result['content_sha256'] = digest(result)
        return result
    finally:
        if _inventory(run) != before:
            raise ValueError('raw evidence changed during read-only diagnostics')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', required=True, type=Path)
    parser.add_argument('--audit', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    output, raw = args.output.resolve(), args.run.resolve()
    if output.is_relative_to(raw) or output.exists():
        raise ValueError('output must be fresh and outside immutable raw evidence')
    result = analyze(raw, args.audit, source_commit=pinned_revision(ROOT))
    write_json_atomic(output, result, sort_keys=True, allow_nan=False)
    print(json.dumps({'content_sha256': result['content_sha256'], 'archived_world_documents': len(result['systems']),
        'archived_POSTs_inspected': len(result['authority_coverage']),
        'notice_count': sum(len(row['notices']) for row in result['systems']), 'new_model_POSTs': 0}))


if __name__ == '__main__':
    main()
