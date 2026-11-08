"""Generate a search-outcome table from a CLOSED V2 report, not a raw audit.

All 120 slots, null types and exact selection ties are rejoined. No measured
value is inferred from authored text, rounded before selection or imputed.
"""
import argparse
from collections import Counter
import hashlib
import json
from pathlib import Path
import re

from scripts.reports.native_design_benchmark import SCHEMA, checked, number
from utopia.system.design_patch import digest
from utopia.utils.data_utils import decode_json

METHODS = ('parameters', 'code-fixed-graph', 'code-and-graph', 'technical-only', 'random')
LABELS = ('LLM numeric', 'LLM code, fixed graph', 'LLM code and graph',
          'Technical-only code/graph', 'Uniform numeric')
RUNS = ('run-00', 'run-01', 'run-02')
STATES = ('complete', 'generation-failure', 'technical-failure', 'loss-unavailable')


def summarize(report, *, expected_source):
    checked(report, SCHEMA + '.report')
    if (not re.fullmatch('[a-f0-9]{40}', expected_source)
            or report.get('source_commit') != expected_source
            or not re.fullmatch('[a-f0-9]{64}', report.get('input_audit_content_sha256', ''))
            or report.get('new_model_calls') != 0 or report.get('new_code_executions') != 0):
        raise ValueError('closed report with exact experiment/audit binding required')
    arms = {objective + ':' + method for objective in ('throughput', 'selective') for method in METHODS}
    expected_ids = {f'{run}:{arm}:g{g}' for run in RUNS for arm in arms for g in range(4)}
    candidates = report['all_candidate_rows']
    if len(candidates) != 120 or {r['row_id'] for r in candidates} != expected_ids:
        raise ValueError('exact 120 unique scheduled search rows required')
    if (set(report['search_arms']) != set(RUNS)
            or set(report['selection']['selected']) != arms
            or any(set(report['search_arms'][run]) != arms for run in RUNS)):
        raise ValueError('exact declared runs, methods and selected arms required')
    lookup = {r['row_id']: r for r in candidates}
    output = []
    for objective in ('throughput', 'selective'):
        for method, label in zip(METHODS, LABELS):
            arm = objective + ':' + method
            rows = []; initials = []
            for run in RUNS:
                body = report['search_arms'][run][arm]
                initials.append(number(body['initial_loss']))
                actual = []
                for g in range(4):
                    row = lookup[f'{run}:{arm}:g{g}']
                    if (row['run'] != run or row['arm'] != arm
                            or type(row['generation']) is not int or row['generation'] != g
                            or row['status'] not in STATES):
                        raise ValueError('candidate identity/status differs')
                    value = number(row['own_loss'])
                    if (value != number(row['cross_scores'][objective])
                            or (value is not None) != (row['status'] == 'complete')):
                        raise ValueError('assigned score/status/null meaning differs')
                    actual.append(row); rows.append(row)
                if body['rows'] != actual:
                    raise ValueError('all-row and per-history projections differ')
            if initials != [number(report['reference_scores']['open-seed'][objective])] * 3:
                raise ValueError('common initial reference differs across histories')
            pool = [('reference:open-seed', initials[0])]
            pool += [(r['row_id'], r['own_loss']) for r in rows]
            available = [(identity, value) for identity, value in pool if value is not None]
            best = min((v for _, v in available), default=None)
            ties = [identity for identity, value in available if value == best]
            selected = report['selection']['selected'][arm]
            if (number(selected['loss']) != best or selected['all_tied_row_ids'] != ties
                    or selected['selected_row_id'] != (ties[0] if ties else None)):
                raise ValueError('frozen selection differs from exact losses/all chronology ties')
            if (selected['system'] is None) != (not ties):
                raise ValueError('selected system availability differs')
            counts = Counter(r['status'] for r in rows)
            output.append({'arm': arm, 'objective': objective, 'display_method': label,
                'scheduled': len(rows), 'status_counts': {s: counts[s] for s in STATES},
                'measured_assigned_losses': counts['complete'], 'best_including_initial': best,
                'all_tied_row_ids': ties, 'selected_row_id': selected['selected_row_id'],
                'selected_initial': selected['selected_row_id'] == 'reference:open-seed'})
    result = {'schema': SCHEMA + '.manuscript-search-table',
        'classification': report['classification'], 'source_commit': expected_source,
        'input_report_content_sha256': report['content_sha256'],
        'input_audit_content_sha256': report['input_audit_content_sha256'], 'rows': output,
        'counts': dict(Counter(r['status'] for r in candidates)),
        'controller_histories_are_not_environment_replications': True,
        'null_losses_imputed': False, 'selection_recomputed_before_display_rounding': True,
        'new_model_calls': 0, 'new_code_executions': 0}
    result['content_sha256'] = digest(result)
    return result


def render(data):
    checked(data, SCHEMA + '.manuscript-search-table')
    lines = ['% Generated from CLOSED report ' + data['input_report_content_sha256'],
        r'\begin{table}[t]', r'\centering\small',
        r'\begin{tabular}{@{}llrrrrrr@{}}', r'\toprule',
        r'Obj. & Proposal space/control & Meas. & G-null & X-null & M-null & Best & Ties\\',
        r'\midrule']
    for index, row in enumerate(data['rows']):
        if index == 5: lines.append(r'\midrule')
        count = row['status_counts']; best = number(row['best_including_initial'])
        value = r'\textemdash' if best is None else f'{best:.3f}'
        if row['selected_initial']: value += r'$^{\ast}$'
        lines.append(' & '.join(['$T$' if row['objective'] == 'throughput' else '$C$',
            row['display_method'], f'{row["measured_assigned_losses"]}/{row["scheduled"]}',
            str(count['generation-failure']), str(count['technical-failure']),
            str(count['loss-unavailable']), value, str(len(row['all_tied_row_ids']))]) + r'\\')
    lines += [r'\bottomrule', r'\end{tabular}',
        r'\caption{\textbf{All scheduled development attempts.} Each row pools three',
        r'controller histories with four proposals each, all at world seed~42.',
        r'Meas.: available assigned losses; G/X-null: generation/execution failures;',
        r'M-null: completed forward with unavailable assigned loss. Nulls are not penalties.',
        r'Best includes the shared initial system; $\ast$ marks its selection, not an invention.',
        r'Ties count all exact minimizers, including the initial reference when tied.',
        r'Only display values are rounded; selection uses unrounded report values.',
        r'Controller histories are not independent environment replications.']
    if data['classification'].startswith('SCRIPTED'):
        lines.append(r'\textbf{SCRIPTED QA -- NOT EXPERIMENTAL RESULTS.}')
    lines += ['}', r'\label{tab:v2-search-outcomes}', r'\end{table}']
    return '\n'.join(lines) + '\n'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--expected-source', required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args(argv)
    if args.output.exists() or args.output.is_symlink():
        parser.error('fresh output directory required; never overwrite evidence')
    before = args.report.read_bytes()
    data = summarize(decode_json(before.decode(), strict=True, finite_floats=True),
                     expected_source=args.expected_source)
    body = render(data)
    if args.report.read_bytes() != before: raise ValueError('report changed during rendering')
    args.output.mkdir(parents=True)
    outputs = {'search-outcomes.tex': body,
        'search-outcomes-data.json': json.dumps(data, sort_keys=True, ensure_ascii=False, allow_nan=False, indent=2) + '\n'}
    for name, content in outputs.items():
        with (args.output / name).open('x', encoding='utf-8') as handle: handle.write(content)
    manifest = {'schema': SCHEMA + '.manuscript-search-table-files',
        'input_file_sha256': hashlib.sha256(before).hexdigest(),
        'input_report_content_sha256': data['input_report_content_sha256'],
        'projection_source_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'files': {name: hashlib.sha256((args.output / name).read_bytes()).hexdigest() for name in outputs}}
    manifest['content_sha256'] = digest(manifest)
    with (args.output / 'manifest.json').open('x', encoding='utf-8') as handle:
        json.dump(manifest, handle, sort_keys=True, allow_nan=False, indent=2); handle.write('\n')
    return 0


if __name__ == '__main__': raise SystemExit(main())
