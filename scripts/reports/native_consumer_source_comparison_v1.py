"""Read all matched source-evidence slots after original paired closure.

No model calls, generated-code execution, world replay or winner substitution.
Scientific decoding is imported from the declared frozen scientific source.
"""
import argparse
import csv
import fcntl
import json
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

from scripts.analyze_native_open_v7 import _inventory
from scripts.reports.native_topic_free_readout_v1 import construction, literal_metrics
from scripts.reports.native_institution_effect_trace_v1 import trace_world
from scripts.reports.native_observed_request_classes_v1 import sequence, groups
from scripts.reports.native_workflow_objective_loop_v1 import graph_change
from utopia.optimization.blackbox import Observation
from utopia.optimization.loss import evaluate_loss, loss_spec_sha256
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.optimization.native_resource_cost import METRIC, UNCOLLECTED_METRIC
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]
STUDY = 'scienceutopia.native-consumer-source-comparison.v1'
SCHEMA = STUDY + '.readout'
ARMS = ['interface-only', 'literal-consumers']
OBJECTIVES = ['content-utility', 'resource-aware-content']
SCORES = ['throughput', *OBJECTIVES]
REFERENCES = ['core-only', 'core-plus-related', 'terminal-consolidation']


def analyze(plan, audit, records, observations):
    """Literal finite pilot projection; nulls remain null and ties stay fixed."""
    if (plan['schema'] != STUDY + '.plan' or audit['schema'] != STUDY + '.audit'
            or plan['arms'] != ARMS or plan['objectives'] != OBJECTIVES
            or plan['generations'] != 2 or plan['reference_order'] != REFERENCES
            or plan['optimizer_reference_labels'] != REFERENCES[:2]
            or plan['design_space']['world_law_scope'] != 'fixed-native-effects-institution-workflow-v6'
            or audit['source_commit'] != plan['source_commit']
            or audit['plan_sha256'] != plan['content_sha256']
            or audit['closure']['terminal']['status'] != 'closed'
            or audit['source_proof']['status'] != 'verified-exact-source-closure'
            or audit['new_model_calls'] or audit['new_code_executions'] or audit['held_out_evaluation']
            or audit['selection']['baseline_fallback']
            or audit['selection'].get('held_out_evaluation', False)):
        raise ValueError('exact normally closed matched original audit required')
    expected = [(s['arm'], s['objective'], s['generation']) for s in plan['schedule']]
    if (len(expected) != 8 or len(set(expected)) != 8 or set(records) != set(expected)
            or set(expected) != {(a, o, g) for a in ARMS for o in OBJECTIVES for g in range(2)}):
        raise ValueError('all eight original slots required, including nulls')
    worlds = {w['identity']: w for w in audit['worlds']}
    if len(worlds) != len(audit['worlds']) or set(worlds) != set(observations):
        raise ValueError('all and only actual audited world observations required')

    def outcome(identity, objective):
        w = worlds[identity]
        o = Observation.from_dict(observations[identity]).to_dict()
        m = o['metadata']; measured = m['measurements']
        scores = {key: evaluate_loss(value, measured) for key, value in plan['losses'].items()}
        if (o['suggestion_id'] != identity or o['candidate'] != w['system'] or o['status'] != w['status']
                or o['loss'] != scores[objective]['loss'] or scores[objective] != m['loss_evaluation']
                or m['loss_spec_sha256'] != loss_spec_sha256(plan['losses'][objective])
                or m['system_fingerprint'] != SystemSpec.from_dict(w['system']).fingerprint
                or w['scores'] != {key: value['loss'] for key, value in scores.items()}
                or (o['status'] == 'complete') != (scores[objective]['status'] == 'complete')):
            raise ValueError('literal original outcome/assigned loss/metric identity differs')
        metrics = literal_metrics(measured)
        collected, unpaid = [metrics[key]['value'] for key in (METRIC, UNCOLLECTED_METRIC)]
        return {'physical_job': identity, 'status': o['status'], 'cross_scores': clone(w['scores']),
            'metrics': metrics, 'requested_activity_cost': None if collected is None or unpaid is None else collected + unpaid,
            'measurement_sha256s': [digest(v) for v in measured],
            'measurements': clone(measured), 'technical_failures': clone(m['technical_failures']),
            'institutional_work_events': None if not measured else
                measured[0]['native_workflow_interval']['institutional_work_events']}

    used = set(); references = []
    for label in REFERENCES:
        identity = 'workflow-reference-' + label
        w = worlds[identity]
        if (w['role'] != 'developer-reference' or w['status'] != 'complete'
                or w['system'] != plan['reference_systems'][label]):
            raise ValueError('complete literal same-authority reference required')
        used.add(identity)
        references.append({'label': label, 'optimizer_visible': label in REFERENCES[:2],
                           **outcome(identity, 'throughput')})
    slots = []
    for index, key in enumerate(expected):
        arm, objective, generation = key; record = records[key]; request = record['request']
        if (request['generation'] != generation or request['loss_spec'] != plan['losses'][objective]
                or record['request_sha256'] != digest(request) or len(record['observations']) > 1
                or len(record['draws']) != len(record['observations'])):
            raise ValueError('exact literal arm/objective slot request required')
        from utopia.optimization.native_consumer_evidence_v1 import OPTION
        evidence = request['strategy_provenance'].get(OPTION)
        expected_evidence = plan['strategies_by_arm'][arm]['local-workflow-designer'].get(OPTION)
        if evidence != expected_evidence or (evidence is not None) != (arm == 'literal-consumers'):
            raise ValueError('exact declared source visibility differs')
        if [v['reference'] for v in request['developer_reference_context']['summary']] != [
                'workflow-reference-' + label for label in REFERENCES[:2]]:
            raise ValueError('only common optimizer-visible references required')
        row = {'slot_index': index, 'arm': arm, 'objective': objective, 'generation': generation,
            'status': 'generation-null', 'request_sha256': record['request_sha256'],
            'parent_system_sha256': digest(request['parent_system']),
            'based_on_observation_id': request.get('based_on_observation_id'),
            'generation_error': clone(record['generation_error']), 'physical_job': None, 'loss': None,
            'cross_scores': {key: None for key in SCORES}, 'metrics': literal_metrics([]),
            'requested_activity_cost': None, 'measurements': [], 'source_evidence_visible': evidence is not None,
            'graph_from_parent': None, 'graph_from_anchor': None, 'literal_system_changed': None,
            'technical_failures': [], 'institutional_work_events': None}
        if record['observations'] and record['observations'][0] is not None:
            o = record['observations'][0]; identity = o['suggestion_id']; w = worlds[identity]
            suggestion = record['draws'][0]['suggestion']
            if (identity in used or w['role'] != 'workflow-own-proposal' or w['objective'] != objective
                    or w['arm'] != arm or suggestion is None or suggestion['candidate'] != o['candidate']):
                raise ValueError('actual audited own world and arm/objective slot differ')
            used.add(identity)
            row.update(outcome(identity, objective), loss=o['loss'],
                literal_system_changed=request['parent_system'] != w['system'],
                graph_from_parent=graph_change(request['parent_system'], w['system'], allow_institution_edits=True),
                graph_from_anchor=graph_change(plan['initial_system'], w['system'], allow_institution_edits=True))
        elif record['generation_error'] is None and not any(d.get('technical_error') for d in record['draws']):
            raise ValueError('missing outcome requires its retained original technical null')
        slots.append(row)
    if used != set(worlds):
        raise ValueError('unaccounted audited world')
    paths = {}; comparisons = {}
    for arm in ARMS:
        for objective in OBJECTIVES:
            own = None
            visible = min(r['cross_scores'][objective] for r in references if r['optimizer_visible'])
            known = visible; path = []
            rows = [r for r in slots if r['arm'] == arm and r['objective'] == objective]
            rows.sort(key=lambda r: r['generation'])
            for row in rows:
                if row['status'] == 'complete':
                    own = row['loss'] if own is None else min(own, row['loss'])
                    known = min(known, row['loss'])
                path.append({'generation': row['generation'], 'status': row['status'], 'observed_loss': row['loss'],
                    'best_own_loss': own, 'best_known_loss_including_visible_references': known})
            ties = [r['physical_job'] for r in rows if r['status'] == 'complete' and r['loss'] == own]
            key = arm + '::' + objective; selected = audit['selection']['selected'][key]
            if (selected['loss'] != own or selected['all_tied_ids'] != ties
                    or selected['selected_id'] != (ties[0] if ties else None)
                    or selected['system'] != (worlds[ties[0]]['system'] if ties else None)):
                raise ValueError('original own-only selection differs; no reference substitution')
            paths[key] = path
            comparisons[key] = {'selected_own_loss': own, 'best_visible_reference_loss': visible,
                'own_minus_best_visible': None if own is None else own - visible,
                'known_withheld_hand_control_loss': references[2]['cross_scores'][objective],
                'own_minus_known_withheld_hand_control': None if own is None else own - references[2]['cross_scores'][objective]}
    contrast = {}
    for objective in OBJECTIVES:
        a, b = [comparisons[arm + '::' + objective]['selected_own_loss'] for arm in ARMS]
        contrast[objective] = None if a is None or b is None else b - a
    return {'schema': SCHEMA, 'scientific_source_commit': plan['source_commit'],
        'plan_sha256': plan['content_sha256'], 'audit_content_sha256': audit['content_sha256'],
        'score_order': SCORES, 'loss_specs': clone(plan['losses']), 'references': references,
        'slots': slots, 'loss_paths': paths, 'selection': clone(audit['selection']),
        'comparisons': comparisons, 'literal_consumers_minus_interface_own_best': contrast,
        'physical_worlds': len(worlds), 'consumed_own_slots': len(slots),
        'interpretation': {'development_seed_reused': True, 'independent_optimizer_replications': False,
            'information_package_not_isolated_source_understanding': True,
            'equal_measured_compute_claimed': False, 'structural_change_is_effect': False,
            'causal_mechanism_effect_identified': False, 'new_model_calls': 0, 'new_code_executions': 0,
            'loss_or_selection_changed': False, 'held_out_evaluation': False,
            'scientific_truth': False, 'publication_ready': False}}


def behavior_evidence(root, plan, audit, records):
    construction_rows = []
    for slot in plan['schedule']:
        key = (slot['arm'], slot['objective'], slot['generation']); record = records[key]
        directory = root / 'search' / slot['arm'] / slot['objective'] / 'authoring' / ('proposal-' + record['request_sha256'])
        read = lambda p: checked(json.loads(p.read_text()))
        binding, wrapper = read(directory / 'binding.json'), read(directory / 'result.json')
        if binding['request'] != record['request'] or wrapper['binding_sha256'] != binding['content_sha256']:
            raise ValueError('exact original author session binding required')
        inner = directory / 'editor-session/authoring' / ('generation-' + record['request_sha256'])
        terminal = inner / 'response.json'
        session = {'request_sha256': digest(binding['request']), 'definition': wrapper['definition'],
            'response': read(terminal) if terminal.is_file() else None,
            'steps': [read(p) for p in sorted(inner.glob('step-*.completed.json'))]}
        construction_rows.append({**clone(slot), 'trace': construction(record, session)})
    requests = []; effects = []
    for world in audit['worlds']:
        cell = Path(world['loaded']['context']).resolve().parent
        if not cell.is_relative_to(root):
            raise ValueError('audited physical world outside original run')
        wire, cache = cell / 'wire-requests.jsonl', cell / 'replies/responses.sqlite'
        wires = [json.loads(line) for line in wire.read_text().splitlines()] if wire.is_file() else []
        replies = []
        if cache.is_file():
            with sqlite3.connect(cache.resolve().as_uri() + '?mode=ro', uri=True) as db:
                replies = db.execute('SELECT payload_sha,outcome,data,data_sha FROM replies ORDER BY rowid').fetchall()
        requests.append({'identity': world['identity'], 'seed': world['seed'], 'status': world['status'],
                         'requests': sequence(wires, replies)})
        effects.append({'identity': world['identity'], 'status': world['status'],
            'trace': None if world['physical_proof'] is None else
                trace_world(cell, world, plan['source_commit'], workflow=True),
            'missing_physical_proof_is_zero_events': False})
    return {'construction': construction_rows, 'world_request_sequences': requests,
        'complete_observed_input_classes': groups(requests), 'native_effect_traces': effects,
        'scope': 'Complete original journals, full scientist inputs/literal choices and native receipts; '
            'not semantic program equivalence, independent replication or identified causal mediation.',
        'new_model_calls': 0, 'new_code_executions': 0, 'new_native_worlds': 0}


def export(args):
    root, frozen, out = args.run.resolve(), args.frozen_source.resolve(), args.output.resolve()
    source, scientific = pinned_revision(ROOT), pinned_revision(frozen)
    if out.exists() or any(out.is_relative_to(p) for p in (root, frozen, ROOT)):
        raise ValueError('fresh report outside scientific raw and both sources required')
    pairs = [[getattr(args, kind + '_' + i).resolve() for i in ('one', 'two')] for kind in ('audit', 'cost')]
    if any(a == b or a.read_bytes() != b.read_bytes() for a, b in pairs):
        raise ValueError('two distinct matching original audit and cost pairs required')
    inputs = [root / 'plan.json', root / 'terminal.json', root / 'selection.json', *pairs[0], *pairs[1]]
    hashes = {str(p): file_sha256(p) for p in inputs}
    read = lambda p: checked(json.loads(p.read_text()))
    with (root / 'writer.lock').open('r') as owner:
        fcntl.flock(owner, fcntl.LOCK_EX | fcntl.LOCK_NB)
        before = _inventory(root); plan, audit, cost = [read(p) for p in (inputs[0], inputs[3], inputs[5])]
        if (plan['source_commit'] != scientific or audit['raw_inventory_sha256'] != digest(before)
                or audit['closure']['terminal'] != read(inputs[1]) or audit['selection'] != read(inputs[2])
                or cost['source_commit'] != scientific or cost['plan_sha256'] != plan['content_sha256']
                or cost['input_audit_content_sha256'] != audit['content_sha256']
                or cost['raw_inventory_sha256'] != audit['raw_inventory_sha256']
                or cost['new_model_calls'] or cost['new_code_executions']):
            raise ValueError('unchanged original closure/source/audit/cost/raw required')
        records = {}; observations = {}
        for label in plan['reference_order']:
            o = read(root / 'references' / label / 'observation.json'); observations[o['suggestion_id']] = o
        for arm in ARMS:
            for objective in OBJECTIVES:
                path = root / 'search' / arm / objective / 'campaign/native-adaptive-state.json'
                state = json.loads(path.read_text())
                if state['pending'] is not None or len(state['records']) != plan['generations']:
                    raise ValueError('terminal exact declared own history required')
                for generation, record in enumerate(state['records']):
                    records[arm, objective, generation] = record
                    for o in record['observations']:
                        if o is not None:
                            if o['suggestion_id'] in observations:
                                raise ValueError('duplicate actual observation')
                            observations[o['suggestion_id']] = o
        report = analyze(plan, audit, records, observations)
        report.update(analysis_source_commit=source, raw_inventory_sha256=digest(before),
            cost_content_sha256=cost['content_sha256'], complete_cost_projection=clone(cost))
        report['behavior_evidence'] = behavior_evidence(root, plan, audit, records)
        if before != _inventory(root) or hashes != {str(p): file_sha256(p) for p in inputs}:
            raise ValueError('original inputs changed during readout')
    out.mkdir(parents=True); save(out / 'report.json', report)
    fields = ['slot_index', 'arm', 'objective', 'generation', 'status', 'physical_job', 'loss',
              *SCORES, 'collected_resource_cost', 'uncollected_activity_cost', 'requested_activity_cost']
    with (out / 'slots.csv').open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        writer.writerows({**{k: r[k] for k in fields if k in r}, **r['cross_scores'],
            'collected_resource_cost': r['metrics'][METRIC]['value'],
            'uncollected_activity_cost': r['metrics'][UNCOLLECTED_METRIC]['value']} for r in report['slots'])
    save(out / 'manifest.json', {'schema': SCHEMA + '.export', 'inputs': hashes,
        'analysis_source_commit': source, 'scientific_source_commit': scientific,
        'adapter_file_sha256': file_sha256(Path(__file__)),
        'files': {p.name: file_sha256(p) for p in sorted(out.iterdir())},
        'new_model_calls': 0, 'new_code_executions': 0})
    if (before != _inventory(root) or hashes != {str(p): file_sha256(p) for p in inputs}
            or pinned_revision(ROOT) != source or pinned_revision(frozen) != scientific):
        raise ValueError('original raw or pinned sources changed during export')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    keys = ('run', 'frozen-source', 'audit-one', 'audit-two', 'cost-one', 'cost-two', 'output')
    for key in keys:
        parser.add_argument('--' + key, type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get('SCIENCE_UTOPIA_COLD_CONSUMER_READOUT_WORKER') == '1':
        export(args); return
    result = subprocess.run([sys.executable, '-B', '-c',
        'import runpy,sys;sys.path.insert(0,sys.argv.pop(1));runpy.run_path(sys.argv.pop(1),run_name="__main__")',
        str(args.frozen_source.resolve()), str(Path(__file__).resolve()),
        *[v for key in keys for v in ('--' + key, str(getattr(args, key.replace('-', '_')).resolve()))]],
        cwd=args.frozen_source, env={**os.environ, 'PYTHONHASHSEED': '42',
            'SCIENCE_UTOPIA_COLD_CONSUMER_READOUT_WORKER': '1'}, timeout=1800, check=False)
    if result.returncode:
        raise SystemExit(result.returncode)


if __name__ == '__main__':
    main()
