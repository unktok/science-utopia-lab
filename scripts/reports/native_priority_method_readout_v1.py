"""Complete compound-identity readout of the finite native mixed-method study.

Only closed original records are read. No candidate, observation, selection,
model request, generated program or scientific world is created or repaired.
"""
import argparse
from collections import Counter
import csv
import json
import os
from pathlib import Path
import subprocess
import sys

from scripts.analyze_native_open_v7 import _inventory
from utopia.optimization.loss import evaluate_loss, loss_spec_sha256
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'scienceutopia.native-priority-method-readout.v1'
STUDY = 'scienceutopia.native-priority-method-comparison.v1'
METHODS = ('uniform-priority', 'adaptive-priority', 'free-code-graph')
OBJECTIVES = ('content-utility', 'resource-aware-content')
METRICS = ('native.accepted_decisions', 'native.common_content_utility_sum',
           'native.collected_activity_resource_cost', 'native.uncollected_activity_resource_cost')


def literal(value):
    return {k: v for k, v in value.items() if k != 'content_sha256'}


def read(path):
    return checked(json.loads(Path(path).read_text()))


def history_key(slot):
    return slot['method'], slot['replication'], slot['objective']


def cell_id(slot):
    return '/'.join((slot['method'], 'history-' + str(slot['replication']), slot['objective'],
                     'generation-' + str(slot['generation'])))


def world_key(world):
    if world['role'] == 'developer-reference':
        return ('reference', world['identity'])
    if (world['role'] not in ('numeric-own-proposal', 'workflow-own-proposal')
            or world['method'] not in METHODS or type(world['optimizer_history']) is not int
            or world['optimizer_history'] not in range(2) or world['objective'] not in OBJECTIVES
            or (world['role'] == 'workflow-own-proposal') != (world['method'] == METHODS[2])):
        raise ValueError('declared compound native world identity required')
    return world['method'], world['optimizer_history'], world['objective'], world['identity']


def graph_delta(parent, candidate):
    a = {n['mechanism_id']: n for n in parent['mechanisms']}
    b = {n['mechanism_id']: n for n in candidate['mechanisms']}
    source = lambda n: n.get('parameters', {}).get('code_artifact', {}).get('source')
    edges = lambda v: {digest(e) for e in v['connections']}
    return {'nodes_added': sorted(b.keys() - a.keys()), 'nodes_removed': sorted(a.keys() - b.keys()),
        'source_changed_nodes': sorted(k for k in a.keys() & b.keys() if source(a[k]) != source(b[k])),
        'parameter_changed_nodes': sorted(k for k in a.keys() & b.keys() if a[k].get('parameters') != b[k].get('parameters')),
        'wires_added': len(edges(candidate) - edges(parent)), 'wires_removed': len(edges(parent) - edges(candidate)),
        'schedules_changed': parent['schedules'] != candidate['schedules'],
        'scope': 'Literal edits relative to actual parent, not proof of native effect or benefit'}


def analyze(plan, audit, slots, references):
    """Pure all-slot projection. Synthetically supplied audits are not provenance."""
    checked(plan); checked(audit)
    if (plan['schema'] != STUDY + '.plan' or audit['schema'] != STUDY + '.audit'
            or plan['methods'] != list(METHODS) or plan['objectives'] != list(OBJECTIVES)
            or len(plan['replication_seeds']) != 2 or plan['generations'] != 2
            or audit['source_commit'] != plan['source_commit'] or audit['plan_sha256'] != plan['content_sha256']
            or audit['source_proof']['status'] != 'verified-exact-source-closure'
            or audit['closure']['terminal']['status'] != 'closed'
            or audit['closure']['terminal']['consumed_slots'] != 24
            or audit['new_model_calls'] != 0 or audit['new_code_executions'] != 0
            or audit['held_out_evaluation'] or audit['selection']['baseline_fallback']
            or audit['selection']['held_out_evaluation']):
        raise ValueError('exact normally closed original-source mixed-method audit required')
    expected = {(m, r, o, g) for m in METHODS for r in range(2) for o in OBJECTIVES for g in range(2)}
    actual = [(s['method'], s['replication'], s['objective'], s['generation']) for s in plan['schedule']]
    if (len(actual) != 24 or set(actual) != expected or len(slots) != 24
            or [s['slot'] for s in slots] != plan['schedule']
            or any(type(s['replication']) is not int or type(s['generation']) is not int for s in plan['schedule'])
            or list(references) != plan['reference_order']):
        raise ValueError('all exact ordered slots/references required, including technical nulls')
    worlds = {}
    for w in audit['worlds']:
        key = world_key(w)
        if key in worlds: raise ValueError('duplicate compound native world identity')
        worlds[key] = w
    used = set()

    def outcome(observation, key, objective):
        o = literal(observation); m = o['metadata']; w = worlds.get(key)
        scores = {k: evaluate_loss(v, m['measurements']) for k, v in plan['losses'].items()}
        if (w is None or key in used or o['suggestion_id'] != w['identity'] or o['candidate'] != w['system']
                or o['status'] != w['status'] or o['loss'] != scores[objective]['loss']
                or (o['status'] == 'complete') != (scores[objective]['status'] == 'complete')
                or m['loss_evaluation'] != scores[objective] or m['loss_spec_sha256'] != loss_spec_sha256(plan['losses'][objective])
                or w['scores'] != {k: v['loss'] for k, v in scores.items()}
                or len(m['measurements']) > 1):
            raise ValueError('literal audited program, observation and cross-scores required')
        used.add(key); measured = m['measurements'][0]['metrics'] if m['measurements'] else {}
        return {'status': o['status'], 'suggestion_id': o['suggestion_id'], 'loss': o['loss'],
            'literal_system_sha256': digest(o['candidate']), 'cross_scores': {k: v['loss'] for k, v in scores.items()},
            'metrics': {k: clone(measured.get(k, {'status': 'measurement-not-recorded', 'value': None})) for k in METRICS},
            'technical_failures': clone(m.get('technical_failures', []))}

    refs = []
    for label in plan['reference_order']:
        o = references[label]; key = ('reference', 'workflow-reference-' + label)
        row = outcome(o, key, 'throughput')
        if row['status'] != 'complete': raise ValueError('normally closed reference must be measured')
        refs.append({'label': label, 'visible_parent': label in plan['optimizer_reference_labels'], **row})
    visible = [r for r in refs if r['visible_parent']]
    if [r['label'] for r in visible] != plan['optimizer_reference_labels'] or not visible:
        raise ValueError('literal common visible reference pool required')
    parents = {o: min(visible, key=lambda r: r['cross_scores'][o]) for o in OBJECTIVES}
    rows = []; candidates = {}
    for i, entry in enumerate(slots):
        slot, o, s = entry['slot'], entry['observation'], entry['suggestion']
        row = {'slot_index': i, 'cell_id': cell_id(slot), **clone(slot), 'generation_error': clone(entry['generation_error'])}
        if o is None:
            if s is not None or slot['method'] != METHODS[2] or not entry['generation_error']:
                raise ValueError('explicit original generation failure, not fabricated missing observation, required')
            row.update(status='generation-null', suggestion_id=None, loss=None, literal_system_sha256=None,
                cross_scores={k: None for k in plan['losses']},
                metrics={k: {'status': 'measurement-not-recorded', 'value': None} for k in METRICS},
                technical_failures=[], graph_delta=None)
        else:
            if s is None or s['candidate'] != o['candidate'] or s['suggestion_id'] != o['suggestion_id']:
                raise ValueError('original suggestion/observation identity required')
            key = (*history_key(slot), o['suggestion_id'])
            row.update(outcome(o, key, slot['objective']))
            row['graph_delta'] = graph_delta(entry['parent_system'], o['candidate'])
            candidates[row['cell_id']] = o['candidate']
        rows.append(row)
    if used != set(worlds) or audit['closure']['terminal']['observations'] != len(worlds):
        raise ValueError('every physical audited world must be accounted for exactly once')
    paths, selected = {}, []
    for method in METHODS:
        for rep in range(2):
            for objective in OBJECTIVES:
                history = [r for r in rows if history_key(r) == (method, rep, objective)]
                history.sort(key=lambda r: r['generation'])
                reference = parents[objective]['cross_scores'][objective]; best = None; path = []
                for row in history:
                    if row['status'] == 'complete': best = row['loss'] if best is None else min(best, row['loss'])
                    path.append({'cell_id': row['cell_id'], 'generation': row['generation'], 'status': row['status'],
                        'observed_loss': row['loss'], 'best_own_loss': best, 'reference_loss': reference,
                        'best_known_including_visible_parent': reference if best is None else min(reference, best)})
                paths['/'.join((method, str(rep), objective))] = path
                pool = [r for r in history if r['status'] == 'complete']
                best = min((r['loss'] for r in pool), default=None); ties = [r for r in pool if r['loss'] == best]
                chosen = ties[0] if ties else None
                expected_selection = {'loss': best, 'completed_submissions': len(pool),
                    'all_tied_ids': [r['suggestion_id'] for r in ties],
                    'selected_id': chosen['suggestion_id'] if chosen else None,
                    'system': candidates[chosen['cell_id']] if chosen else None, 'reference_loss': reference}
                if audit['selection']['selected'][method][str(rep)][objective] != expected_selection:
                    raise ValueError('frozen own-only selection differs; no reselection or reference fallback')
                selected.append({'method': method, 'replication': rep, 'objective': objective, 'loss': best,
                    'completed_submissions': len(pool), 'all_tied_ids': expected_selection['all_tied_ids'],
                    'cell_id': chosen['cell_id'] if chosen else None, 'suggestion_id': expected_selection['selected_id'],
                    'literal_system_sha256': chosen['literal_system_sha256'] if chosen else None,
                    'cross_scores': chosen['cross_scores'] if chosen else {k: None for k in plan['losses']},
                    'reference_loss': reference, 'own_minus_reference': None if best is None else best - reference})
    duplicates = Counter(w['identity'] for w in audit['worlds'])
    return {'schema': SCHEMA, 'scientific_source_commit': plan['source_commit'], 'plan_content_sha256': plan['content_sha256'],
        'input_audit_content_sha256': audit['content_sha256'], 'frozen_selection_content_sha256': audit['selection']['content_sha256'],
        'references': refs, 'slots': rows, 'paths': paths, 'selected': selected,
        'coverage': {'declared_own_slots': 24, 'complete_own_slots': sum(r['status'] == 'complete' for r in rows),
            'generation_nulls': sum(r['status'] == 'generation-null' for r in rows),
            'execution_or_measurement_nulls': sum(r['status'] not in ('complete', 'generation-null') for r in rows),
            'physical_worlds': len(worlds)},
        'nonunique_suggestion_ids_across_compound_cells': {k: n for k, n in sorted(duplicates.items()) if n > 1},
        'interpretation': 'One reused researcher-world condition. U is fixed abstract opinion, K is collected native cost. '
            'Different objectives need not select different systems. Literal edits are not effects; exact input classes '
            'are not semantic equivalence. Two seeded histories are not independent populations or sufficient method evidence.',
        'new_model_calls': 0, 'new_code_executions': 0, 'selection_changed': False,
        'held_out_evaluation': False, 'method_superiority_claimed': False, 'publication_ready': False}


def collect(root, plan):
    refs = {label: read(root / 'references' / label / 'observation.json') for label in plan['reference_order']}
    slots = []; states = {}
    for slot in plan['schedule']:
        method, rep, objective = history_key(slot); g = slot['generation']
        directory = root / 'search' / method / ('history-' + str(rep)) / objective
        if method != METHODS[2]:
            target = directory / ('generation-' + str(g)); started = read(target / 'started.json')
            parent_id = started['suggestion']['based_on_observation_id']
            before = read(directory / ('initial-state.json' if g == 0 else 'generation-0/optimizer-after-tell.json'))
            own_parents = before['optimizer']['observations']
            parent = next((r['candidate'] for r in own_parents if r['observation_id'] == parent_id), None)
            if parent_id is not None and parent is None:
                raise ValueError('declared numeric parent missing from original optimizer state')
            # A uniform sample has no parent; the frozen family anchor is its
            # declared reference, not a fabricated based_on observation.
            parent = before['space_binding']['anchor'] if parent is None else parent
            slots.append({'slot': clone(slot), 'suggestion': started['suggestion'],
                'observation': read(target / 'observation.json'), 'parent_system': parent, 'generation_error': None})
        else:
            key = history_key(slot)
            if key not in states:
                state = json.loads((directory / 'campaign/native-adaptive-state.json').read_text())
                if state['pending'] is not None or len(state['records']) != plan['generations']:
                    raise ValueError('original free history must have all terminal records')
                states[key] = state
            record = states[key]['records'][g]; draws, observations = record['draws'], record['observations']
            if (len(draws) != len(observations) or len(draws) > 1 or not record['compiled']
                    or not record['generated'] or record['request']['generation'] != g):
                raise ValueError('exact one-draw free record or original generation failure required')
            if not draws:
                if not record['generation_error']: raise ValueError('missing draw without original generation error')
                s = o = None; error = record['generation_error']
            else:
                s, o = draws[0]['suggestion'], observations[0]
                error = record['generation_error'] or draws[0].get('error')
            slots.append({'slot': clone(slot), 'suggestion': s, 'observation': o,
                'parent_system': record['request']['parent_system'], 'generation_error': error})
    return slots, refs


def export(args):
    root, frozen, out = args.run.resolve(), args.frozen_source.resolve(), args.output.resolve()
    reader_source, scientific = pinned_revision(ROOT), pinned_revision(frozen)
    if out.exists() or any(out.is_relative_to(p) for p in (root, frozen, ROOT)):
        raise ValueError('fresh report outside reader/scientific source and raw required')
    audits = [args.audit_one.resolve(), args.audit_two.resolve()]; costs = [args.cost_one.resolve(), args.cost_two.resolve()]
    if (audits[0] == audits[1] or costs[0] == costs[1] or audits[0].read_bytes() != audits[1].read_bytes()
            or costs[0].read_bytes() != costs[1].read_bytes()):
        raise ValueError('distinct matching paired original audits and cost projections required')
    inputs = [root / n for n in ('plan.json', 'terminal.json', 'selection.json')] + audits + costs
    hashes = {str(p): file_sha256(p) for p in inputs}; before = _inventory(root)
    plan, audit, cost = read(inputs[0]), read(audits[0]), read(costs[0])
    if (plan['source_commit'] != scientific or digest(before) != audit['raw_inventory_sha256']
            or audit['closure']['terminal'] != read(root / 'terminal.json')
            or audit['selection'] != read(root / 'selection.json')
            or cost['source_commit'] != scientific or cost['plan_sha256'] != plan['content_sha256']
            or cost['input_audit_content_sha256'] != audit['content_sha256'] or cost['raw_inventory_sha256'] != digest(before)
            or cost['new_model_calls'] != 0 or cost['new_code_executions'] != 0):
        raise ValueError('unchanged original normal closure, selection, inventory and costs required')
    slots, refs = collect(root, plan); result = analyze(plan, audit, slots, refs)
    result.update(analysis_source_commit=reader_source, cost_content_sha256=cost['content_sha256'])
    if before != _inventory(root) or hashes != {str(p): file_sha256(p) for p in inputs}:
        raise ValueError('original evidence changed during projection')
    out.mkdir(parents=True); save(out / 'report.json', result)
    fields = ['slot_index', 'cell_id', 'method', 'replication', 'objective', 'generation', 'status', 'suggestion_id', 'loss',
              'throughput', *OBJECTIVES, *METRICS]
    with (out / 'slots.csv').open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        writer.writerows({**{k: r[k] for k in fields if k in r}, **r['cross_scores'],
            **{k: r['metrics'][k]['value'] for k in METRICS}} for r in result['slots'])
    save(out / 'manifest.json', {'schema': SCHEMA + '.export', 'inputs': hashes,
        'analysis_source_commit': reader_source, 'scientific_source_commit': scientific,
        'adapter_file_sha256': file_sha256(Path(__file__)),
        'files': {p.name: file_sha256(p) for p in sorted(out.iterdir())}, 'new_model_calls': 0, 'new_code_executions': 0})
    if (before != _inventory(root) or hashes != {str(p): file_sha256(p) for p in inputs}
            or pinned_revision(ROOT) != reader_source or pinned_revision(frozen) != scientific):
        raise ValueError('reader/scientific source or original records changed during export')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    keys = ('run', 'frozen-source', 'audit-one', 'audit-two', 'cost-one', 'cost-two', 'output')
    for key in keys: parser.add_argument('--' + key, type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get('SCIENCE_UTOPIA_PRIORITY_READOUT_WORKER') == '1': export(args); return
    result = subprocess.run([sys.executable, '-B', '-c',
        'import runpy,sys;sys.path.insert(0,sys.argv.pop(1));runpy.run_path(sys.argv.pop(1),run_name="__main__")',
        str(args.frozen_source.resolve()), str(Path(__file__).resolve()),
        *[v for key in keys for v in ('--' + key, str(getattr(args, key.replace('-', '_')).resolve()))]],
        cwd=args.frozen_source, env={**os.environ, 'PYTHONHASHSEED': '42', 'SCIENCE_UTOPIA_PRIORITY_READOUT_WORKER': '1'},
        timeout=1800, check=False)
    if result.returncode: raise SystemExit(result.returncode)


if __name__ == '__main__': main()
