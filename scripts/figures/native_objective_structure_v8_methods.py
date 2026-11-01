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
    fig, ax = plt.subplots(figsize=(10.4, 4.7))
    ax.set_xlim(0, 10.4); ax.set_ylim(0, 4.7); ax.axis('off')

    def box(x, y, w, h, text, color, *, dashed=False, fontsize=8.2):
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
    box(.25, 3.35, 1.55, .75, 'Frozen LossSpec 1\nThroughput  $L=-A$', blue)
    box(.25, 2.15, 1.55, .75, 'Frozen LossSpec 2\nReviewed utility\n$L=3.25A-Q+0.05R$', orange)
    box(2.25, 2.75, 1.65, .9, 'Objective-visible external\nstructural authoring\n(no host repair)', '#775DA6')
    box(4.35, 2.75, 1.45, .9, '2 generations ×\n2 conditional-IID\ndesigns per arm', '#775DA6')
    box(6.25, 2.75, 1.55, .9, 'Original native world\n5 fixed Qwen researchers\n2 years, seed 42', green)
    box(8.25, 2.75, 1.65, .9, 'Independent checkpoint\nmeasurement\n8 native diagnostics', green)
    box(4.35, 1.20, 1.45, .8, 'Adaptive feedback uses\nthat arm loss only', grey)
    box(6.25, 1.20, 1.55, .8, 'Cross-score every\ncompleted draw under\nboth frozen losses', grey)
    box(8.25, 1.20, 1.65, .8, 'Loss paths + selected\n2×2 matrix + exact\ngraph/source diffs', grey)
    box(.55, .12, 3.20, .60, 'Held-out metrics\nnot defined/measured in v8', '#9A5465', dashed=True, fontsize=7.8)
    box(4.20, .12, 3.20, .60, 'Promotion policy\nnot defined/applied in v8', '#9A5465', dashed=True, fontsize=7.8)

    arrow(1.80, 3.73, 2.25, 3.30, blue)
    arrow(1.80, 2.53, 2.25, 3.10, orange)
    arrow(3.90, 3.20, 4.35, 3.20)
    arrow(5.80, 3.20, 6.25, 3.20)
    arrow(7.80, 3.20, 8.25, 3.20)
    arrow(9.08, 2.75, 9.08, 2.00)
    arrow(8.25, 1.60, 7.80, 1.60)
    arrow(6.25, 1.60, 5.80, 1.60, label='bound arm loss')
    arrow(4.35, 1.60, 3.25, 2.75, dashed=True, label='next generation')
    arrow(7.02, 1.20, 5.80, .72, color='#9A5465', dashed=True)

    ax.text(.25, 4.45, 'Two-objective original-native structural exploration: methods and evidence boundary',
            fontsize=12, weight='bold', color='#172633')
    ax.text(.25, 4.18, 'The optimized object is the system. Objectives stay frozen; technical failures stay null.',
            fontsize=8.8, color='#53616D')
    ax.text(7.75, .40, 'Development engineering only\nNo improvement or scientific-value claim',
            fontsize=7.8, color='#9A5465', ha='left', va='center')
    paths = {kind: output.with_suffix('.'+kind) for kind in ('pdf', 'png', 'svg')}
    for kind, path in paths.items():
        fig.savefig(path, dpi=210 if kind == 'png' else None, bbox_inches='tight', facecolor='white')
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
