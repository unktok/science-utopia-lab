#!/usr/bin/env python3
"""Prepare, but do not insert, a NeurIPS LaTeX slice from frozen actual v8 evidence."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from scripts.analyze_native_objective_structure_v8 import ACTUAL, ARM_IDS, SCHEMA
from scripts.figures.native_objective_structure_v8 import figure_data
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256


def _verify_outputs(manifest):
    for value in manifest.get('outputs', {}).values():
        path = Path(value['path'])
        if not path.is_file() or file_sha256(path) != value['sha256']:
            raise ValueError('figure output path/hash differs from manifest')


def render_slice(report, results_manifest, methods_manifest, *, results_tex_path, methods_tex_path):
    """Return an include-ready fragment; the caller owns paper integration."""
    figure_data(report)  # Recheck the same empirical facts plotted by the figure.
    if report.get('classification') != ACTUAL:
        raise ValueError('only frozen actual evidence may produce a paper slice')
    if (results_manifest.get('schema') != 'scienceutopia.native-objective-structure-figure.v8'
            or results_manifest.get('report_content_sha256') != report['content_sha256']
            or results_manifest.get('classification') != ACTUAL):
        raise ValueError('empirical figure is not bound to this actual audit')
    if (methods_manifest.get('schema') != 'scienceutopia.native-objective-structure-methods-figure.v8'
            or methods_manifest.get('result_independent') is not True):
        raise ValueError('result-independent v8 methods figure manifest required')
    _verify_outputs(results_manifest); _verify_outputs(methods_manifest)
    matrix = report['selected_cross_objective_matrix']
    def value(row, column):
        item = matrix[row]
        return '--' if item is None or item[column] is None else f"{item[column]:.4g}"
    return rf"""% Auto-generated from independently audited v8 evidence {report['content_sha256']}.
% Prepared fragment only: paper integration remains an explicit reviewed action.
\begin{{figure*}}[t]
  \centering
  \includegraphics[width=\textwidth]{{{methods_tex_path}}}
  \caption{{Preregistered two-objective native structural exploration. The system is optimized while each LossSpec remains frozen. Held-out metrics and promotion are outside this development-engineering pilot.}}
  \label{{fig:native-objective-structure-v8-methods}}
\end{{figure*}}

\begin{{figure*}}[t]
  \centering
  \includegraphics[width=\textwidth]{{{results_tex_path}}}
  \caption{{Audited development loss paths, cross-objective scores of the two selected representatives, and literal graph/source differences. Cross-scores reuse the same worlds and are not independent replications.}}
  \label{{fig:native-objective-structure-v8-results}}
\end{{figure*}}

\begin{{table}}[t]
\centering
\caption{{Selected-system development cross-scores (lower is better within a column; objectives have different units).}}
\label{{tab:native-objective-structure-v8-crossscores}}
\begin{{tabular}}{{lrr}}
\toprule
Selection objective & $-A$ & $3.25A-Q+0.05R$ \\
\midrule
$-A$ & {value(ARM_IDS[0], ARM_IDS[0])} & {value(ARM_IDS[0], ARM_IDS[1])} \\
Reviewed utility & {value(ARM_IDS[1], ARM_IDS[0])} & {value(ARM_IDS[1], ARM_IDS[1])} \\
\bottomrule
\end{{tabular}}
\end{{table}}

\paragraph{{Scope.}} These are objective-conditioned development-engineering observations, not held-out, causal, scientific-value, optimizer-convergence, or improvement evidence. Technical failures remain null rather than numerical penalties.
"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--results-manifest', type=Path, required=True)
    parser.add_argument('--methods-manifest', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--results-tex-path', default='figures/native-objective-structure-v8.pdf')
    parser.add_argument('--methods-tex-path', default='figures/native-objective-structure-v8-methods.pdf')
    args = parser.parse_args()
    report = json.loads(args.report.read_text())
    if report.get('schema') != SCHEMA or report.get('content_sha256') != digest(
            {k: v for k, v in report.items() if k != 'content_sha256'}):
        raise ValueError('hash-bound v8 audit required')
    text = render_slice(report, json.loads(args.results_manifest.read_text()),
        json.loads(args.methods_manifest.read_text()), results_tex_path=args.results_tex_path,
        methods_tex_path=args.methods_tex_path)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(text)
    print(json.dumps({'output': str(args.output), 'audit_sha256': report['content_sha256']}, sort_keys=True))


if __name__ == '__main__':
    main()
