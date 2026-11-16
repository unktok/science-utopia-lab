"""All fifteen fixed labels, two conditions and every predeclared contrast.

Pure analysis/read-only export. No selection, candidate execution or model
request; neither missing pairs nor shared physical jobs become extra samples.
"""
import argparse
import csv
import hashlib
from itertools import combinations
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

from scripts.analyze_native_open_v7 import _inventory
from scripts.native_priority_fixed_bank_v1 import planned_jobs, selection_label
from scripts.reports.native_priority_method_readout_v1 import METHODS, OBJECTIVES, METRICS
from scripts.run_native_priority_fixed_evaluation_v1 import SCHEMA as STUDY, SEEDS
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.optimization.native_resource_cost import INSTRUMENT
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import decode_json, file_sha256

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'scienceutopia.native-priority-fixed-evaluation-readout.v1'
SCORE_ORDER = (*OBJECTIVES, 'throughput')


def read(path):
    return checked(decode_json(Path(path).read_text(), strict=True, finite_floats=True))


def contrast_definitions(bank, *, profile='priority-v1'):
    if profile == 'corrected-choice-v1':
        from scripts.native_corrected_choice_fixed_bank_v1 import SCOPES, label
        result = []
        for entry in bank['entries'][3:]:
            for ref in bank['entries'][:3]:
                result.append({'id': 'control/' + entry['label'] + '-minus-' + ref['label'],
                    'kind': 'fixed-' + entry['selection_scope'] + '-versus-reference',
                    'left': entry['label'], 'right': ref['label']})
        for scope in SCOPES:
            for objective in OBJECTIVES:
                for left, right in combinations(METHODS, 2):
                    result.append({'id': 'method/' + scope + '/' + left + '-minus-' + right + '/' + objective,
                        'kind': 'fixed-' + scope + '-method-policies',
                        'left': label(scope, left, objective), 'right': label(scope, right, objective)})
            for method in METHODS:
                result.append({'id': 'objective/' + scope + '/' + method,
                    'kind': 'fixed-' + scope + '-objective-policies',
                    'left': label(scope, method, OBJECTIVES[0]), 'right': label(scope, method, OBJECTIVES[1])})
        for method in METHODS:
            for objective in OBJECTIVES:
                result.append({'id': 'scope/' + method + '/' + objective,
                    'kind': 'fixed-best-known-versus-own-only',
                    'left': label('best-known', method, objective), 'right': label('own-only', method, objective)})
        return result
    if profile != 'priority-v1': raise ValueError('explicit fixed-evaluation readout profile required')
    entries = bank['entries']; result = []
    for own in entries[3:]:
        for ref in entries[:3]:
            result.append({'id': 'control/' + own['label'] + '-minus-' + ref['label'],
                'kind': 'fixed-own-versus-reference', 'left': own['label'], 'right': ref['label']})
    for history in range(2):
        for objective in OBJECTIVES:
            for left, right in combinations(METHODS, 2):
                result.append({'id': 'method/' + left + '-minus-' + right + '/history-' + str(history) + '/' + objective,
                    'kind': 'fixed-method-selected-policies', 'left': selection_label(left, history, objective),
                    'right': selection_label(right, history, objective)})
        for method in METHODS:
            result.append({'id': 'objective/' + method + '/history-' + str(history),
                'kind': 'fixed-objective-selected-policies', 'left': selection_label(method, history, OBJECTIVES[0]),
                'right': selection_label(method, history, OBJECTIVES[1])})
    return result


def summarize(p, audit, *, profile='priority-v1'):
    from scripts.run_native_priority_fixed_evaluation_v1 import profile_contract
    study, _, _, _, jobs = profile_contract(profile)
    schema = ('scienceutopia.native-corrected-choice-fixed-evaluation-readout.v1'
        if profile == 'corrected-choice-v1' else SCHEMA)
    checked(p); checked(audit); bank = checked(p['fixed_selection'])
    if (p['schema'] != study + '.plan' or audit['schema'] != study + '.audit'
            or audit['source_commit'] != p['source_commit'] or audit['plan_sha256'] != p['content_sha256']
            or audit['source_proof']['status'] != 'verified-exact-source-closure'
            or audit['closure']['terminal']['status'] != 'closed'
            or audit['closure']['terminal']['completed_jobs'] != len(p['jobs'])
            or audit['new_model_calls'] or audit['new_code_executions'] or not audit['held_out_world_seeds']
            or audit['fixed_selection'] != bank or audit['origin_audit_content_sha256'] != p['origin_audit_content_sha256']
            or p['evaluation']['seeds'] != SEEDS or p['losses'] != bank['losses']
            or set(p['losses']) != set(SCORE_ORDER)
            or p['claims']['candidate_reselection'] or p['claims']['reference_fallback']):
        raise ValueError('exact normally closed frozen-policy evaluation audit required')
    draft = jobs(bank, p['evaluation']['seeds'])
    if p['jobs'] != draft['jobs'] or len(audit['worlds']) != len(p['jobs']):
        raise ValueError('every exact declared physical job and literal sharing required')
    worlds = {}; physical = []; by_label = {}
    for job, world in zip(p['jobs'], audit['worlds']):
        if (world['identity'] in worlds or any(world.get(k) != v for k, v in job.items())
                or world['role'] != 'selection-fixed-evaluation' or len(world['measurements']) > 1):
            raise ValueError('ordered unique exact frozen-policy world required')
        worlds[world['identity']] = world
        scores = {k: evaluate_loss(v, world['measurements']) for k, v in p['losses'].items()}
        if (world['scores'] != {k: v['loss'] for k, v in scores.items()}
                or (world['status'] == 'complete') != (scores['throughput']['status'] == 'complete')):
            raise ValueError('literal measurement-derived cross-scores/status required')
        measurement = world['measurements'][0] if world['measurements'] else {}
        row = {**clone(job), 'system_sha256': digest(job['system']), 'status': world['status'],
            'scores': {k: v['loss'] for k, v in scores.items()},
            'metrics': clone(measurement.get('metrics', {})),
            'native_workflow_interval': clone(measurement.get('native_workflow_interval')),
            'annual_resources': clone(measurement.get(INSTRUMENT, {}).get('annual', [])),
            'resource_instrument_recorded': INSTRUMENT in measurement}
        # Exact programs are in the original pinned plan/audit/bank, not
        # duplicated on every logical label or presented as new discoveries.
        row.pop('system'); physical.append(row)
        for label in job['labels']:
            key = (label, job['seed'])
            if key in by_label: raise ValueError('logical label maps to multiple physical jobs')
            by_label[key] = row
    logical = []
    for entry in bank['entries']:
        for seed in p['evaluation']['seeds']:
            physical_row = by_label.get((entry['label'], seed)); available = entry['system'] is not None
            if available != (physical_row is not None): raise ValueError('missing selection cannot acquire fallback or a physical job')
            metadata = {k: clone(v) for k, v in entry.items() if k not in ('system', 'selection_available')}
            logical.append({**metadata, 'seed': seed, 'selection_available': available,
                'physical_job': None if physical_row is None else physical_row['identity'],
                'status': 'selection-unavailable' if physical_row is None else physical_row['status'],
                'scores': {k: None for k in p['losses']} if physical_row is None else clone(physical_row['scores']),
                'metrics': {} if physical_row is None else clone(physical_row['metrics'])})
    logical_keys = {(r['label'], r['seed']) for r in logical}
    expected_keys = {(e['label'], seed) for e in bank['entries'] if e['system'] is not None for seed in SEEDS}
    if set(by_label) != expected_keys or len(logical_keys) != 30:
        raise ValueError('all thirty logical rows, including unavailable selection rows, required')
    definitions = contrast_definitions(bank, **({} if profile == 'priority-v1' else {'profile': profile}))
    logical_by = {(r['label'], r['seed']): r for r in logical}
    contrasts = []; summaries = []
    for definition in definitions:
        pairs = []
        for seed in SEEDS:
            left, right = (logical_by[(definition[k], seed)] for k in ('left', 'right'))
            differences = {k: None if left['scores'][k] is None or right['scores'][k] is None
                else left['scores'][k] - right['scores'][k] for k in p['losses']}
            row = {**clone(definition), 'seed': seed, 'left_status': left['status'], 'right_status': right['status'],
                'left_physical_job': left['physical_job'], 'right_physical_job': right['physical_job'],
                'same_physical_job': left['physical_job'] is not None and left['physical_job'] == right['physical_job'],
                'differences': differences}
            contrasts.append(row); pairs.append(row)
        summaries.append({**clone(definition), 'scores': {score: {
            'available_pairs': sum(row['differences'][score] is not None for row in pairs),
            'missing_seeds': [row['seed'] for row in pairs if row['differences'][score] is None],
            'descriptive_available_pair_mean': (sum(row['differences'][score] for row in pairs if row['differences'][score] is not None)
                / sum(row['differences'][score] is not None for row in pairs))
                if any(row['differences'][score] is not None for row in pairs) else None}
            for score in p['losses']}})
    return {'schema': schema, 'scientific_source_commit': p['source_commit'], 'plan_content_sha256': p['content_sha256'],
        'input_audit_content_sha256': audit['content_sha256'], 'origin_audit_content_sha256': p['origin_audit_content_sha256'],
        'fixed_bank_content_sha256': bank['content_sha256'], 'seeds': clone(SEEDS),
        'labels': [e['label'] for e in bank['entries']], 'score_order': list(SCORE_ORDER),
        'physical_rows': physical, 'logical_rows': logical, 'contrast_definitions': definitions,
        'fixed_policy_contrasts': contrasts, 'descriptive_contrast_summaries': summaries,
        'coverage': {'logical_policy_labels': 15, 'logical_rows': 30, 'physical_worlds': len(physical),
            'complete_physical_worlds': sum(w['status'] == 'complete' for w in physical),
            'failed_physical_worlds': sum(w['status'] != 'complete' for w in physical),
            'selection_unavailable_rows': sum(r['status'] == 'selection-unavailable' for r in logical)},
        'missing_own_selections': clone(bank['missing_own_selections']),
        'interpretation': 'Fixed programs in two new world-seed conditions, not repeated independent searches. '
            'All U/C/T cross-scores and unavailable pairs remain. Shared labels are not extra physical samples; '
            'available-pair means are descriptive, not superiority tests. U is abstract opinion, K collected cost; '
            'C gains need not reduce requested work. Development parents are annotations, not effects of generated edits.'
            + (' Best-known reference origins remain explicit and are not own discoveries; both scopes are separate.'
                if profile == 'corrected-choice-v1' else ''),
        'new_model_calls': 0, 'new_code_executions': 0, 'selection_changed': False,
        'method_superiority_claimed': False, 'publication_ready': False}


def observed_paths(root, report):
    from scripts.reports.native_observed_request_classes_v1 import sequence, groups
    traces = []
    for row in report['physical_rows']:
        cell = root / 'evaluation' / row['identity'] / 'worlds' / (row['identity'] + '-s' + str(row['seed']))
        wire, cache = cell / 'wire-requests.jsonl', cell / 'replies/responses.sqlite'
        if not cell.resolve().is_relative_to(root.resolve()): raise ValueError('original cell outside evaluation raw')
        available = wire.is_file() and cache.is_file(); requests = None; outcomes = []
        if available:
            wires = [decode_json(line, strict=True, finite_floats=True) for line in wire.read_text().splitlines()]
            with sqlite3.connect(cache.as_uri() + '?mode=ro', uri=True) as db:
                replies = db.execute('SELECT payload_sha,outcome,data,data_sha FROM replies ORDER BY rowid').fetchall()
            if any(hashlib.sha256(body.encode()).hexdigest() != expected for _, _, body, expected in replies):
                raise ValueError('original response-cache body changed')
            outcomes = [outcome for _, outcome, _, _ in replies if outcome != 'response']
            if not outcomes: requests = sequence(wires, replies)
        traces.append({'identity': row['identity'], 'seed': row['seed'], 'labels': clone(row['labels']),
            'status': row['status'] if requests is not None else 'observed-path-unavailable',
            'original_status': row['status'], 'requests': requests, 'wire_file_exists': wire.is_file(),
            'response_cache_exists': cache.is_file(), 'nonresponse_cache_outcomes': outcomes})
    return {'traces': traces, 'complete_observed_input_classes': groups(traces),
        'scope': 'Observed complete physical paths only; no semantic equivalence, independent-label or zero-cost inference'}


def export(args, *, profile='priority-v1'):
    root, frozen, out = args.run.resolve(), args.frozen_source.resolve(), args.output.resolve()
    if out.exists() or any(out.is_relative_to(p.resolve()) for p in (ROOT, root, frozen)):
        raise ValueError('fresh report outside reader/scientific source and raw required')
    reader, scientific = pinned_revision(ROOT), pinned_revision(frozen)
    p = read(root / 'plan.json')
    if any(out.is_relative_to(Path(p['origin'][k]).resolve()) for k in ('run', 'source', 'analysis', 'readouts')):
        raise ValueError('report cannot enter the original development evidence/source')
    audits, costs = [args.audit_one.resolve(), args.audit_two.resolve()], [args.cost_one.resolve(), args.cost_two.resolve()]
    if (audits[0] == audits[1] or costs[0] == costs[1] or audits[0].read_bytes() != audits[1].read_bytes()
            or costs[0].read_bytes() != costs[1].read_bytes()):
        raise ValueError('distinct matching paired original evaluation audits and costs required')
    files = [root / name for name in ('plan.json', 'started.json', 'terminal.json')] + audits + costs
    hashes = {str(f): file_sha256(f) for f in files}; before = _inventory(root)
    audit, cost = read(audits[0]), read(costs[0])
    if (p['source_commit'] != scientific or audit['raw_inventory_sha256'] != digest(before)
            or audit['raw_files'] != len(before) or audit['closure']['started'] != read(root / 'started.json')
            or audit['closure']['terminal'] != read(root / 'terminal.json')
            or cost['source_commit'] != scientific or cost['plan_sha256'] != p['content_sha256']
            or cost['input_audit_content_sha256'] != audit['content_sha256']
            or cost['raw_inventory_sha256'] != digest(before) or cost['new_model_calls'] or cost['new_code_executions']):
        raise ValueError('unchanged normal original evaluation closure and paired costs required')
    report = summarize(p, audit, **({} if profile == 'priority-v1' else {'profile': profile}))
    report['behavior_evidence'] = observed_paths(root, report)
    report.update(analysis_source_commit=reader, cost_content_sha256=cost['content_sha256'],
        cost_summary={k: clone(cost.get(k)) for k in ('scientist', 'common_content_observer', 'auxiliary', 'scope')})
    if before != _inventory(root) or hashes != {str(f): file_sha256(f) for f in files}:
        raise ValueError('original evaluation records changed during readout')
    out.mkdir(parents=True); save(out / 'report.json', report)
    fields = ['label', 'seed', 'role', 'physical_job', 'status', *report['score_order'], *METRICS]
    with (out / 'logical-scores.csv').open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        for row in report['logical_rows']:
            writer.writerow({**{k: row[k] for k in fields if k in row}, **row['scores'],
                **{k: row['metrics'].get(k, {}).get('value') for k in METRICS}})
    fields = ['id', 'kind', 'seed', 'left', 'right', 'left_status', 'right_status', 'left_physical_job',
        'right_physical_job', 'same_physical_job', *report['score_order']]
    with (out / 'contrasts.csv').open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader()
        writer.writerows({**{k: row[k] for k in fields if k in row}, **row['differences']}
            for row in report['fixed_policy_contrasts'])
    save(out / 'manifest.json', {'schema': report['schema'] + '.export', 'inputs': hashes, 'analysis_source_commit': reader,
        'scientific_source_commit': scientific, 'adapter_file_sha256': file_sha256(Path(__file__)),
        'files': {f.name: file_sha256(f) for f in sorted(out.iterdir())}, 'new_model_calls': 0, 'new_code_executions': 0})
    if (before != _inventory(root) or hashes != {str(f): file_sha256(f) for f in files}
            or pinned_revision(ROOT) != reader or pinned_revision(frozen) != scientific):
        raise ValueError('scientific/reader source or original evaluation records changed during export')


def main(*, profile='priority-v1', worker_path=None):
    parser = argparse.ArgumentParser(description=__doc__)
    keys = ('run', 'frozen-source', 'audit-one', 'audit-two', 'cost-one', 'cost-two', 'output')
    for key in keys: parser.add_argument('--' + key, type=Path, required=True)
    args = parser.parse_args()
    if os.environ.get('SCIENCE_UTOPIA_PRIORITY_FIXED_READOUT_WORKER') == '1':
        export(args, profile=profile); return
    result = subprocess.run([sys.executable, '-B', '-c',
        'import runpy,sys;sys.path.insert(0,sys.argv.pop(1));runpy.run_path(sys.argv.pop(1),run_name="__main__")',
        str(args.frozen_source.resolve()), str(Path(__file__).resolve() if worker_path is None else worker_path.resolve()),
        *[value for key in keys for value in ('--' + key, str(getattr(args, key.replace('-', '_')).resolve()))]],
        cwd=args.frozen_source, env={**os.environ, 'PYTHONHASHSEED': '42', 'SCIENCE_UTOPIA_PRIORITY_FIXED_READOUT_WORKER': '1'},
        timeout=1800, check=False)
    if result.returncode: raise SystemExit(result.returncode)


if __name__ == '__main__': main()
