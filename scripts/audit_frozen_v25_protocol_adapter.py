#!/usr/bin/env python3
"""Explicit read-only reporting adapter for the frozen V25 protocol allowlist defect.

Loads the original auditor/runtime from a clean pinned tree. The only substituted
function extends its protocol-path allowlist; every original source byte and the
actual protocol byte is still checked. Never rewrites frozen source/raw evidence.
This is an adapted audit, not a claim that the original unmodified command passed.
"""
import argparse
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import subprocess
import sys


PROTOCOLS = {'research/protocols/campaigns/native-tool-calling-exploration-v25-a'
    + str(index) + '.md' for index in (1, 2, 3)}


def protocol_proof(original, root, source, classification, *, protocol_path):
    if protocol_path not in PROTOCOLS:
        raise ValueError('adapter only extends the three declared V25 protocol paths')
    # The original verifier still checks every runtime/helper source blob,
    # including its own original auditor and the older default protocol.
    proof = original(source, classification)
    expected = hashlib.sha256(subprocess.check_output(
        ['git', 'show', source + ':' + protocol_path], cwd=root)).hexdigest()
    actual = hashlib.sha256((root / protocol_path).read_bytes()).hexdigest()
    if actual != expected:
        raise ValueError('actual V25 protocol differs from frozen source')
    proof['files'][protocol_path] = {'actual_source_sha256': expected, 'analysis_source_sha256': actual}
    proof['protocol_allowlist_extension'] = {
        'actual_protocol': protocol_path,
        'original_source_verifier_preserved': True,
        'only_bypassed_defect': 'original explicit path allowlist omitted driver-selected V25 protocol',
        'original_unmodified_audit_claimed': False}
    return proof


def load_frozen_auditor(root, source):
    if not re.fullmatch('[0-9a-f]{40}', source):
        raise ValueError('exact 40-character source commit required')
    actual = subprocess.check_output(['git', 'rev-parse', 'HEAD'], cwd=root, text=True).strip()
    dirty = subprocess.check_output(['git', 'status', '--porcelain'], cwd=root, text=True)
    if actual != source or dirty:
        raise ValueError('original auditor requires its clean pinned experiment tree')
    path = root / 'scripts/analyze_native_staged_search_v15.py'
    expected = subprocess.check_output(['git', 'show', source + ':scripts/analyze_native_staged_search_v15.py'], cwd=root)
    if path.read_bytes() != expected:
        raise ValueError('original auditor source bytes differ')
    if any(name == 'utopia' or name.startswith('utopia.') or name.startswith('scripts.') for name in sys.modules):
        raise ValueError('adapter process must not have imported another runtime')
    sys.path.insert(0, str(root))
    spec = importlib.util.spec_from_file_location('frozen_v25_auditor', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    original = module.source_proofs
    module.source_proofs = lambda source, classification, *, protocol_path: protocol_proof(
        original, root, source, classification, protocol_path=protocol_path)
    return module


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--frozen-tree', type=Path, required=True)
    parser.add_argument('--expected-source', required=True)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--compact', action='store_true')
    args = parser.parse_args()
    root, raw, output = args.frozen_tree.resolve(), args.run.resolve(), args.output.resolve()
    if output.exists() or output.is_relative_to(raw) or output.is_relative_to(root):
        raise ValueError('fresh audit output must be outside frozen source and raw evidence')
    module = load_frozen_auditor(root, args.expected_source)
    result = module.analyze(raw, expected_source=args.expected_source, require_complete=True)
    result['audit']['external_protocol_allowlist_adapter'] = {
        'schema': 'scienceutopia.frozen-v25-report-adapter.v26',
        'adapter_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'original_auditor_source_sha256': hashlib.sha256(
            (root / 'scripts/analyze_native_staged_search_v15.py').read_bytes()).hexdigest(),
        'original_runtime_source_commit': args.expected_source,
        'frozen_source_or_raw_modified': False,
        'original_unmodified_audit_claimed': False}
    result.pop('content_sha256')
    result['content_sha256'] = module.digest(result)
    if args.compact:
        result = module.compact_summary(result)
    module.write_json_atomic(output, result, sort_keys=True, allow_nan=False)
    print(json.dumps({key: result[key] for key in ('status', 'physical_native_worlds',
        'physical_researcher_responses', 'content_sha256')}, sort_keys=True))


if __name__ == '__main__':
    main()
