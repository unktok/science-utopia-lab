"""All catalog-control outcomes and actual project/input traces after closure."""
import argparse
import csv
import json
from pathlib import Path

from scripts.analyze_native_open_v7 import _inventory
from scripts.reports.native_institution_effect_trace_v1 import checkpoint
from scripts.reports.native_instruction_timing_v1 import completed_pairs, direction_input, native_history
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'scienceutopia.native-catalog-actuation-report.v1'


def export(args):
    root, out, frozen = args.run.resolve(), args.output.resolve(), args.frozen_source.resolve()
    source = pinned_revision(ROOT)
    if out.exists() or out.is_relative_to(root) or out.is_relative_to(frozen):
        raise ValueError('fresh export outside scientific source/raw required')
    paths = [root / 'plan.json', args.audit_one, args.audit_two]
    hashes = {str(p): file_sha256(p) for p in paths}
    if paths[1].read_bytes() != paths[2].read_bytes(): raise ValueError('matching original double audits required')
    p, audit = [checked(json.loads(path.read_text())) for path in paths[:2]]
    before = _inventory(root)
    if (p['schema'] != 'scienceutopia.native-catalog-actuation.v1.plan'
            or audit['schema'] != 'scienceutopia.native-catalog-actuation-audit.v1'
            or audit['source_commit'] != p['source_commit'] or audit['plan_sha256'] != p['content_sha256']
            or pinned_revision(frozen) != p['source_commit']
            or audit['closure']['terminal']['status'] != 'closed'
            or audit['source_proof']['status'] != 'verified-exact-source-closure'
            or audit['raw_inventory_sha256'] != digest(before) or audit['new_model_calls']
            or audit['new_code_executions'] or len(audit['worlds']) != 3
            or [w['identity'] for w in audit['worlds']] != [j['identity'] for j in p['jobs']]):
        raise ValueError('normally closed literal original catalog-control audit required')
    catalog = {d['topic']: d['years'] for d in p['catalog']['directions']}
    marker = 'native-developer-catalog-agenda-v1'
    worlds = []
    for w, job in zip(audit['worlds'], p['jobs']):
        if any(w[k] != job[k] for k in job): raise ValueError('literal job differs')
        cell = Path(w['loaded']['context']).resolve().parent
        if not cell.is_relative_to(root): raise ValueError('world outside audited raw')
        states = [checkpoint(cell, item, w['system']) for item in w['physical_proof'].get('annual_checkpoints', [])]
        annual, memories = [], []
        if states:
            annual, memories, _ = native_history(states, marker, catalog)
        wires, replies = completed_pairs(cell) if (cell / 'wire-requests.jsonl').is_file() else ([], {})
        directions = []
        for i, wire in enumerate(wires):
            result = direction_input(wire, replies.get(i), memories, marker, catalog)
            if result is not None: directions.append({'wire_index': i, **result})
        if w['status'] == 'complete' and [s['year'] for s in states] != [1, 2, 3, 4]:
            raise ValueError('complete control lacks four annual states')
        worlds.append({'identity': w['identity'], 'condition': w['condition'], 'seed': w['seed'],
            'status': w['status'], 'scores': w['scores'], 'annual': annual, 'direction_memories': memories,
            'direction_requests': directions, 'annual_agendas': w['annual_agendas'],
            'catalog_project_effects': w['physical_proof'].get('native_counts', {}).get('project_assignments_verified', []),
            'physical_wire_requests': len(wires), 'committed_responses': len(replies),
            'wire_without_committed_reply': len(wires) - len(replies)})
    result = {'schema': SCHEMA, 'analysis_source_commit': source, 'scientific_source_commit': p['source_commit'],
        'plan_sha256': p['content_sha256'], 'audit_content_sha256': audit['content_sha256'],
        'raw_inventory_sha256': digest(before), 'catalog': p['catalog'], 'worlds': worlds,
        'scope': 'Developer controls at one reused seed. Native assignments, advice in direction inputs, '
            'scientist choices and completed outcomes remain distinct. Direct assignment replaces the '
            'original planning choice; its absence is not advice obedience. Partial boundaries remain '
            'diagnostics, never completed losses. No automatic invention, optimizer superiority, pure '
            'mediation, independent replication or general scientific benefit is inferred.',
        'new_model_calls': 0, 'new_code_executions': 0, 'loss_or_selection_changed': False, 'publication_ready': False}
    if (before != _inventory(root) or hashes != {str(path): file_sha256(path) for path in paths}
            or pinned_revision(ROOT) != source or pinned_revision(frozen) != p['source_commit']):
        raise ValueError('original raw or reader binding changed')
    out.mkdir(parents=True); save(out / 'report.json', result)
    fields = ['condition', 'status', 'seed', 'throughput', 'founder-activity', 'physical_wire_requests',
        'committed_responses', 'direction_requests', 'advisory_direction_inputs', 'catalog_project_effects']
    with (out / 'controls.csv').open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        for w in worlds:
            writer.writerow({**{k: w[k] for k in ('condition', 'status', 'seed', 'physical_wire_requests', 'committed_responses')},
                **w['scores'], 'direction_requests': len(w['direction_requests']),
                'advisory_direction_inputs': sum(r['literal_instruction_present'] for r in w['direction_requests']),
                'catalog_project_effects': len(w['catalog_project_effects'])})
    save(out / 'manifest.json', {'schema': SCHEMA + '.export', 'inputs': hashes,
        'report_file_sha256': file_sha256(out / 'report.json'), 'controls_file_sha256': file_sha256(out / 'controls.csv'),
        'analysis_source_commit': source, 'new_model_calls': 0, 'new_code_executions': 0})
    print(json.dumps({'worlds': len(worlds), 'complete': sum(w['status'] == 'complete' for w in worlds)}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('run', 'frozen-source', 'audit-one', 'audit-two', 'output'):
        parser.add_argument('--' + name, type=Path, required=True)
    export(parser.parse_args())


if __name__ == '__main__': main()
