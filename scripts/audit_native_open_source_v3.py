#!/usr/bin/env python3
"""Independent exact-context/native-loss audit for free-source design attempts."""
from pathlib import Path
import json
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))


def audit_free_source(run, loss):
    from scripts.audit_native_design_loop import audit
    from scripts.audit_native_feedback_v2 import wire_summary
    from utopia.optimization.native_code_trace import parent_context_provider
    from utopia.system import SystemSpec
    from utopia.system.code_mechanisms import sha
    saved = json.loads((run / 'campaign/native-design-state.json').read_text())
    world = saved['binding']['world']
    completed = (run / 'completion.json').exists()
    result = audit(run, loss, world['years'], require_completion=completed)
    provider = parent_context_provider(run / 'runs', source_commit=world['source_commit'])
    proposals = []
    for path in sorted((run / 'design-proposals').glob('free-source-*.json')):
        if not re.fullmatch(r'free-source-\d+-\d+\.json', path.name):
            continue
        receipt = json.loads(path.read_text())
        if receipt['receipt_sha256'] != sha({k: v for k, v in receipt.items() if k != 'receipt_sha256'}):
            raise ValueError('free-source receipt digest mismatch')
        binding = receipt['binding']
        index = binding['index']
        history = saved['records'][:index]
        if not history or binding['history_sha256'] != sha(history):
            raise ValueError('source proposal is not bound to exact earlier native observations')
        incumbent = min((r for r in history if r['observation']['status'] == 'complete'), key=lambda r: r['observation']['loss'])
        parent = SystemSpec.from_dict(incumbent['suggestion']['candidate'])
        if parent.fingerprint != binding['parent_fingerprint'] or binding['loss_spec_sha256'] != sha(loss):
            raise ValueError('free-source parent/objective binding mismatch')
        rows = provider(binding['node_id'], parent, history)
        if [r['bundle_sha256'] for r in rows] != binding['context_bundle_sha256s']:
            raise ValueError('source proposal is not grounded in the exact completed native contexts')
        row_lookup = {r['bundle_sha256']: r for r in rows}
        executed = False
        if receipt['status'] == 'isolated-probes-passed-not-native-evaluated':
            artifact = receipt['patch']['operations'][0]['value']
            if artifact['source'] != receipt['draft']['source'] or sha(artifact['source']) != receipt['source_sha256']:
                raise ValueError('executed artifact differs from exact model-generated source')
            if 'generated' in receipt and receipt['generated']['python_code'] != artifact['source']:
                raise ValueError('normalized Python source differs from actual structured model output')
            for probe in receipt['probe_results']:
                native = row_lookup[probe['native_bundle_sha256']]
                if any(probe['receipt'].get(key + '_sha256') != sha(value) for key, value in (
                    ('artifact', artifact), ('context', native['context']), ('result', probe['result']))):
                    raise ValueError('source isolated-probe evidence mismatch')
            if index < len(saved['records']):
                record = saved['records'][index]
                if record['patch'] != receipt['patch']:
                    raise ValueError('native execution is not the actual source proposal')
                executed = record['observation']['status'] == 'complete'
        proposals.append({'receipt': path.name, 'receipt_sha256': receipt['receipt_sha256'],
            'index': index, 'status': receipt['status'], 'error': receipt.get('error'),
            'source_sha256': sha(receipt['draft'].get('source')) if isinstance(receipt.get('draft'), dict) else None,
            'source_same_as_parent': receipt.get('source_same_as_parent'),
            'actual_native_evaluated': executed,
            'probe_results_changed': [p['result_changed'] for p in receipt['probe_results']],
            'prompt_utf8_bytes': receipt.get('prompt_utf8_bytes'), 'prompt_view_limits': receipt.get('prompt_view_limits')})
    for row in result['rows']:
        for native in row['runs']:
            native['wire'] = wire_summary(run / 'runs' / native['run_id'], needle='not-a-context-probe', required=True)
    result.update(schema='scienceutopia.native-open-source-audit.v3', proposals=proposals,
        raw_output_root=str(run), campaign_budget_completed=completed,
        interpretation='actual arbitrary-node source design, not full topology invention or scientific-quality optimization')
    if not completed:
        result['completion'] = 'campaign-not-budget-complete'
    return result


if __name__ == '__main__':
    import argparse
    from utopia.optimization.loss import load_loss_spec
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--loss', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(audit_free_source(args.run.resolve(), load_loss_spec(args.loss)), ensure_ascii=False, indent=2, allow_nan=False))
