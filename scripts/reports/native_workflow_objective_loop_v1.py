"""All structural slots, graph edits and separate incumbent/own loss paths."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path

from scripts.analyze_native_open_v7 import _inventory
from scripts.reports.native_objective_instrument_loop_v1 import render
from utopia.optimization.native_numeric_designer import checked, save
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import file_sha256

SCHEMA = 'scienceutopia.native-workflow-objective-report.v1'


def graph_change(before, after):
    """Literal phase and multiset edge changes, never an inferred policy effect."""
    fields = lambda spec: {k: v for k, v in spec.items() if k not in ('connections', 'schedules')}
    if fields(before) != fields(after):
        raise ValueError('audited structural-only policy changes source, parameters or other fields')
    phases = lambda spec: {s['mechanism_id']: s['phase'] for s in spec['schedules']}
    old, new = phases(before), phases(after)
    schedule_fields = lambda spec: {s['mechanism_id']: {k: v for k, v in s.items() if k != 'phase'}
        for s in spec['schedules']}
    if (set(old) != set(new) or len(old) != len(before['schedules'])
            or len(new) != len(after['schedules']) or schedule_fields(before) != schedule_fields(after)):
        raise ValueError('workflow node schedules/triggers differ')
    encode = lambda e: json.dumps(e, sort_keys=True, separators=(',', ':'), allow_nan=False)
    a, b = [Counter(encode(e) for e in spec['connections']) for spec in (before, after)]
    return {'phase_updates': {k: {'before': old[k], 'after': new[k]} for k in sorted(old) if old[k] != new[k]},
        'removed_connections': [json.loads(e) for e in sorted((a - b).elements())],
        'added_connections': [json.loads(e) for e in sorted((b - a).elements())],
        'source_parameters_nodes_unchanged': True}


def summarize(p, audit, records):
    if (p['schema'] != 'scienceutopia.native-workflow-objective-loop.v1.plan'
            or audit['schema'] != 'scienceutopia.native-workflow-objective-loop-audit.v1'
            or audit['source_commit'] != p['source_commit'] or audit['plan_sha256'] != p['content_sha256']
            or audit['closure']['terminal']['status'] != 'closed'
            or audit['source_proof']['status'] != 'verified-exact-source-closure'
            or audit['new_model_calls'] or audit['new_code_executions']):
        raise ValueError('normally closed matching original workflow audit required')
    worlds = {w['identity']: w for w in audit['worlds']}
    if len(worlds) != len(audit['worlds']): raise ValueError('duplicate audited world identity')
    used, references, slots = set(), [], []
    for label in p['reference_order']:
        identity = 'workflow-reference-' + label.lower(); w = worlds[identity]
        if (w['role'] != 'developer-reference' or w['status'] != 'complete'
                or w['system'] != p['reference_systems'][label]):
            raise ValueError('workflow reference identity/system differs')
        used.add(identity)
        references.append({'label': label, 'physical_job': identity, 'status': w['status'],
            'scores': clone(w['scores']), 'graph_from_anchor': graph_change(p['initial_system'], w['system'])})
    if set(records) != {(s['objective'], s['generation']) for s in p['schedule']}:
        raise ValueError('all six original structural slots required')
    for index, slot in enumerate(p['schedule']):
        objective, generation = slot['objective'], slot['generation']; r = records[objective, generation]
        if (r['request']['generation'] != generation or r['request']['loss_spec'] != p['losses'][objective]
                or r['request_sha256'] != digest(r['request']) or len(r['observations']) > 1
                or len(r['draws']) != len(r['observations'])):
            raise ValueError('literal workflow slot request/observation differs')
        parent = r['request']['parent_system']
        row = {**slot, 'slot_index': index, 'request_sha256': r['request_sha256'],
            'parent_system_sha256': digest(parent), 'generation_error': clone(r['generation_error']),
            'status': 'generation-null', 'physical_job': None, 'loss': None,
            'cross_scores': {o: None for o in p['objectives']},
            'graph_from_parent': None, 'graph_from_anchor': None}
        if r['observations'] and r['observations'][0] is not None:
            o = r['observations'][0]; identity = o['suggestion_id']; w = worlds[identity]
            suggestion = r['draws'][0]['suggestion']
            if (identity in used or w['role'] != 'workflow-own-proposal' or w['objective'] != objective
                    or w['status'] != o['status'] or w['system'] != o['candidate']
                    or suggestion is None or suggestion['candidate'] != o['candidate']
                    or o['loss'] != w['scores'][objective]):
                raise ValueError('workflow own world differs from original audited slot')
            used.add(identity)
            row.update(status=o['status'], physical_job=identity, loss=o['loss'], cross_scores=clone(w['scores']),
                graph_from_parent=graph_change(parent, w['system']),
                graph_from_anchor=graph_change(p['initial_system'], w['system']))
        elif r['generation_error'] is None and not any(d.get('technical_error') for d in r['draws']):
            raise ValueError('missing workflow observation without a retained technical null')
        slots.append(row)
    if used != set(worlds): raise ValueError('unaccounted original workflow world')
    paths = {}
    for objective in p['objectives']:
        rows = [r for r in slots if r['objective'] == objective]
        own, known = None, min(r['scores'][objective] for r in references)
        values = []
        for r in rows:
            if r['status'] == 'complete':
                own = r['loss'] if own is None else min(own, r['loss']); known = min(known, r['loss'])
            values.append({'generation': r['generation'], 'observed_loss': r['loss'],
                'status': r['status'], 'best_own_loss': own, 'best_known_loss': known})
        ties = [r['physical_job'] for r in rows if r['status'] == 'complete' and r['loss'] == own]
        selected = audit['selection']['selected'][objective]
        if (selected['loss'] != own or selected['all_tied_ids'] != ties
                or selected['selected_id'] != (ties[0] if ties else None)
                or selected['system'] != (worlds[ties[0]]['system'] if ties else None)):
            raise ValueError('workflow own-only selection changed or a reference was substituted')
        paths[objective] = values
    return {'schema': SCHEMA, 'source_commit': p['source_commit'], 'plan_sha256': p['content_sha256'],
        'audit_content_sha256': audit['content_sha256'], 'score_order': clone(p['objectives']),
        'references': references, 'slots': slots, 'loss_paths': paths, 'selection': clone(audit['selection']),
        'physical_worlds': len(worlds), 'consumed_own_slots': len(slots),
        'interpretation': {'held_out_evaluation': False, 'independent_optimizer_replications': False,
            'isolated_design_freedom_causal_effect_claimed': False, 'scientific_truth': False,
            'new_model_calls': 0, 'new_code_executions': 0, 'publication_ready': False}}


def export(args):
    root, output = Path(args.run).resolve(), Path(args.output).resolve()
    if output.exists() or output.is_relative_to(root): raise ValueError('fresh report outside original raw required')
    inputs = [root / 'plan.json', Path(args.audit_one).resolve(), Path(args.audit_two).resolve()]
    before = _inventory(root); hashes = {str(f): file_sha256(f) for f in inputs}
    p, a, b = [checked(json.loads(f.read_text())) for f in inputs]
    if (inputs[1].read_bytes() != inputs[2].read_bytes() or a != b
            or a['raw_inventory_sha256'] != digest(before) or a['raw_files'] != len(before)
            or a['closure']['terminal'] != checked(json.loads((root / 'terminal.json').read_text()))
            or a['selection'] != checked(json.loads((root / 'selection.json').read_text()))):
        raise ValueError('unchanged original workflow raw and two matching cold audits required')
    records = {}
    for objective in p['objectives']:
        state = json.loads((root / 'search' / objective / 'campaign/native-adaptive-state.json').read_text())
        if state['pending'] is not None or len(state['records']) != 3:
            raise ValueError('pending or incomplete original workflow history')
        records.update({(objective, g): r for g, r in enumerate(state['records'])})
    report = summarize(p, a, records)
    if before != _inventory(root) or hashes != {str(f): file_sha256(f) for f in inputs}:
        raise ValueError('workflow report input changed during reading')
    output.mkdir(parents=True); saved = save(output / 'report.json', report)
    render(saved, output)
    fields = ['slot_index', 'objective', 'generation', 'status', 'physical_job', 'loss', 'throughput',
        'content-utility', 'changed_phases', 'removed_edges', 'added_edges']
    with (output / 'slots.csv').open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields, lineterminator='\n'); writer.writeheader()
        for row in report['slots']:
            diff = row['graph_from_parent']
            writer.writerow({**{k: row[k] for k in fields if k in row}, **row['cross_scores'],
                **{k: None if diff is None else len(diff[v]) for k, v in (
                    ('changed_phases', 'phase_updates'), ('removed_edges', 'removed_connections'),
                    ('added_edges', 'added_connections'))}})
    save(output / 'manifest.json', {'schema': SCHEMA + '.export', 'inputs': hashes,
        'raw_inventory_sha256': digest(before), 'report_content_sha256': saved['content_sha256'],
        'files': {f.name: file_sha256(f) for f in sorted(output.iterdir()) if f.is_file()},
        'new_model_calls': 0, 'new_code_executions': 0})
    if _inventory(root) != before: raise ValueError('original workflow raw changed during rendering')
    return saved


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('run', 'audit-one', 'audit-two', 'output'): parser.add_argument('--' + key, type=Path, required=True)
    report = export(parser.parse_args())
    print(json.dumps({'consumed_slots': report['consumed_own_slots'], 'physical_worlds': report['physical_worlds']}))


if __name__ == '__main__': main()
