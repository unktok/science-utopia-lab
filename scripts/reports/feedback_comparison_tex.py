"""Render the verified summary's literal numbers into a manuscript table.

No simulation, model, source execution or statistical inference. This is not an
independent raw audit: the original-source auditor must produce the input.
"""
import argparse
import math
from pathlib import Path
import re

from scripts.reports.publication_evidence import decode, digest

SCHEMA = 'scienceutopia.native-feedback-comparison-audit.v1.summary'


def number(value):
    if value is None:
        return r'\textemdash'
    if type(value) not in (int,float) or not math.isfinite(value):
        raise ValueError('finite numeric display value or explicit null required')
    return f'{value:.3f}'


def render(data):
    if (data.get('schema') != SCHEMA or not re.fullmatch('[0-9a-f]{40}',data.get('source_commit',''))
            or data.get('content_sha256') != digest({k:v for k,v in data.items() if k!='content_sha256'})):
        raise ValueError('exact source/schema/content-bound comparison summary required')
    rows = data['candidate_rows']
    expected = {f'{objective}-{policy}:g{g}' for objective in ('throughput','efficiency')
        for policy in ('loss','technical-only') for g in range(2)}
    if len(rows)!=8 or {r['row_id'] for r in rows}!=expected:
        raise ValueError('exact eight distinct candidate rows required')
    counts = {k:0 for k in ('complete','generation-failure','technical-failure')}
    lines = [r'% Generated from summary '+data['content_sha256'],
        r'\paragraph{Observed outcomes.}',
        r'All eight declared candidate slots are retained in Table~\ref{tab:pilot-outcomes}.']
    table = [r'\begin{table}[t]',r'\centering\small',
        r'\begin{tabular}{@{}lllrr@{}}',r'\toprule',
        r'Design & Generation & Status & $\ell_T$ & $\ell_E$\\',r'\midrule']
    baseline = data['baseline']
    if baseline['cross_scores']!=baseline['row']['cross_scores']:
        raise ValueError('baseline row/table cross-scores differ')
    table.append('Shared baseline & -- & '+('complete' if baseline['row']['status']=='complete' else 'failure')
        +' & '+number(baseline['cross_scores']['throughput'])+' & '
        +number(baseline['cross_scores']['efficiency'])+r'\\')
    table.append(r'\midrule')
    for row in rows:
        arm = row['arm']; objective, suffix = arm.split('-',1)
        if (type(row['generation']) is not int or row['generation'] not in (0,1)
                or row['row_id'] != f'{arm}:g{row["generation"]}'):
            raise ValueError('candidate arm/generation/row identity differs')
        if objective not in ('throughput','efficiency') or suffix not in ('loss','technical-only'):
            raise ValueError('undeclared objective/proposal arm')
        if row['status'] not in counts:
            raise ValueError('unknown candidate terminal state')
        counts[row['status']] += 1
        if (row['status']=='complete' and row['loss'] != row['cross_scores'][objective]
                or row['status']!='complete' and (row['loss'] is not None
                    or any(v is not None for v in row['cross_scores'].values()))):
            raise ValueError('own/cross-score or failure-null meaning differs')
        label = objective.title()+' / '+('adaptive' if suffix=='loss' else 'control')
        status = {'complete':'complete','generation-failure':'generation failure',
            'technical-failure':'execution failure'}[row['status']]
        table.append(label+' & '+str(row['generation'])+' & '+status+' & '
            +number(row['cross_scores']['throughput'])+' & '+number(row['cross_scores']['efficiency'])+r'\\')
    table += [r'\bottomrule',r'\end{tabular}',
        r'\caption{Same-source development outcomes, scored under both objectives.',
        r'Lower is better. Scores are rounded only for display to three decimals;',
        r'exact values, all ties and nulls remain in the source-bound JSON.',
        r'A dash is an unavailable outcome or score, not a numerical penalty.',
        r'Cross-scoring reuses the same checkpoint; it is not an independent replicate.}',
        r'\label{tab:pilot-outcomes}',r'\end{table}']
    lines += [f'The budget contains {counts["complete"]} completed candidates, '
        f'{counts["generation-failure"]} generation failures, and '
        f'{counts["technical-failure"]} execution failures. No failed slot is replaced.',
        *table,
        r'These are descriptive observations from one development seed and two generations per arm,',
        r'not evidence of expected improvement, significance, or method superiority.']
    return '\n'.join(lines)+'\n'


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    saved=args.summary.read_bytes(); body=render(decode(saved.decode('utf-8')))
    if args.summary.read_bytes()!=saved:
        raise ValueError('summary changed while rendering')
    if args.output.exists() or args.output.is_symlink():
        raise ValueError('manuscript table output must be fresh')
    args.output.parent.mkdir(parents=True,exist_ok=True)
    with args.output.open('x',encoding='utf-8') as stream:
        stream.write(body)
    return 0


if __name__=='__main__':
    raise SystemExit(main())
