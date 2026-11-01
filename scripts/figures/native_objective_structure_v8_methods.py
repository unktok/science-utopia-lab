#!/usr/bin/env python3
"""Result-independent methods flow for the native objective/structure v8 pilot."""
from __future__ import annotations

import argparse
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from utopia.utils.data_utils import file_sha256, write_json_atomic


def create(output):
    output = Path(output)
    output.parent.mkdir(parents=True, exist_ok=True)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 8.5,
        'pdf.fonttype': 42, 'ps.fonttype': 42})
    # NeurIPS text width is 5.5in: author at final physical width so 9pt text
    # remains 9pt after inclusion, rather than shrinking a 7.2in canvas.
    fig, ax = plt.subplots(figsize=(5.5, 6.3))
    ax.set_xlim(0, 7.2); ax.set_ylim(0, 6.3); ax.axis('off')
    fig.subplots_adjust(left=.015, right=.985, bottom=.015, top=.985)

    def box(x, y, w, h, text, color, *, dashed=False, fontsize=9):
        patch = FancyBboxPatch((x, y), w, h, boxstyle='round,pad=.06,rounding_size=.08',
            linewidth=1.1, edgecolor=color, facecolor=color+'16',
            linestyle='--' if dashed else '-')
        ax.add_patch(patch)
        ax.text(x+w/2, y+h/2, text, ha='center', va='center', color='#172633', fontsize=fontsize)
        return patch

    def arrow(x1, y1, x2, y2, color='#5B6872', *, dashed=False, label=None):
        ax.add_patch(FancyArrowPatch((x1, y1), (x2, y2), arrowstyle='-|>', mutation_scale=10,
            linewidth=1.05, color=color, linestyle='--' if dashed else '-'))
        if label: ax.text((x1+x2)/2, (y1+y2)/2+.10, label, ha='center', color=color, fontsize=7.4)

    blue, orange, green, grey = '#2878B5', '#D56A36', '#2C8B75', '#6C7882'
    box(.25, 4.95, 3.05, .72, 'Frozen LossSpec 1: throughput\n$L=-A$', blue)
    box(3.85, 4.95, 3.05, .72, 'Frozen LossSpec 2: reviewed utility\n$L=3.25A-Q+0.05R$', orange)
    box(.25, 3.45, 2.0, .95, 'Objective-visible\nexternal source author\n(no host repair)', '#775DA6')
    box(2.60, 3.45, 1.80, .95, '2 generations ×\n2 conditional-IID\ndesigns per arm', '#775DA6')
    box(4.80, 3.45, 2.10, .95, 'Original native world\n5 fixed Qwen authors\n2 years, seed 42', green)
    box(4.80, 1.95, 2.10, .95, 'Independent checkpoint\nmeasurement\n8 native diagnostics', green)
    box(2.60, 1.95, 1.80, .95, 'Cross-score every\ncompleted draw using\nboth frozen losses', grey)
    box(.25, 1.95, 2.0, .95, 'Loss paths + selected\n2×2 matrix + exact\ngraph/source diffs', grey)
    box(.25, .15, 3.05, .60, 'Held-out metrics\nnot defined/measured in v8', '#9A5465', dashed=True, fontsize=8.5)
    box(3.85, .15, 3.05, .60, 'Promotion policy\nnot defined/applied in v8', '#9A5465', dashed=True, fontsize=8.5)

    # Connect at the actual padded box boundaries; feedback is one continuous
    # external path, not disconnected elbows or lines crossing the text panels.
    arrow(1.78, 4.89, 1.00, 4.46, blue)
    arrow(5.38, 4.89, 1.70, 4.46, orange)
    arrow(2.31, 3.925, 2.54, 3.925)
    arrow(4.46, 3.925, 4.74, 3.925)
    arrow(5.85, 3.39, 5.85, 2.96)
    arrow(4.74, 2.425, 4.46, 2.425)
    arrow(2.54, 2.425, 2.31, 2.425)
    ax.plot([6.96, 7.08, 7.08, .12, .12], [2.425, 2.425, 1.25, 1.25, 3.925],
            color=grey, linewidth=1.05, linestyle='--', solid_joinstyle='round')
    arrow(.12, 3.925, .19, 3.925, grey)
    ax.text(3.60, 1.38, 'Next generation: adaptive feedback uses that arm loss only',
            ha='center', fontsize=8.5, color=grey)

    ax.text(.25, 6.04, 'Objective-conditioned structural exploration: methods',
            fontsize=11.5, weight='bold', color='#172633')
    ax.text(.25, 5.81, 'The system changes; objectives stay frozen; technical failures stay null.',
            fontsize=8.7, color='#53616D')
    ax.text(3.60, .98, 'Development engineering only: no scientific-value or general-benefit claim.',
            fontsize=8.2, color='#9A5465', ha='center', va='center')
    paths = {kind: output.with_suffix('.'+kind) for kind in ('pdf', 'png', 'svg')}
    for kind, path in paths.items():
        fig.savefig(path, dpi=210 if kind == 'png' else None, bbox_inches='tight', facecolor='white')
        if kind == 'svg':
            path.write_text('\n'.join(line.rstrip() for line in path.read_text().splitlines())+'\n')
    plt.close(fig)
    manifest = {'schema': 'scienceutopia.native-objective-structure-methods-figure.v8',
        'result_independent': True, 'new_model_calls': 0, 'new_container_executions': 0,
        'loss_objectives': ['native-joint-v5-throughput', 'native-joint-v5-net-reviewed-utility'],
        'held_out_metrics': 'not-defined-or-measured', 'promotion_policy': 'not-defined-or-applied',
        'outputs': {key: {'path': str(path), 'sha256': file_sha256(path)} for key, path in paths.items()}}
    write_json_atomic(output.with_suffix('.manifest.json'), manifest, sort_keys=True, allow_nan=False)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    create(args.output)


if __name__ == '__main__':
    main()
