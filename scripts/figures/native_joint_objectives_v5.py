"""Plot audited objective paths and their actual selected native graph cuts.

No model/simulator calls. Null technical failures are never numerical points.
Synthetic QA figures are labelled and forbidden under any paper/figures path.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import hashlib
import json
import math
from pathlib import Path
import re
import textwrap

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyArrowPatch, FancyBboxPatch

from utopia.system import SystemSpec

ROOT = Path(__file__).resolve().parents[2]
ACTUAL = 'actual-native-development-objective-conditioned-joint-design'
FIXTURE = 'scripted-fixture-not-native-results'
COLORS = ['#316BA4', '#B56935']
CHANNEL_COLORS = {'artifact': '#518DB1', 'signal': '#A2ACB7', 'decision': '#B66E3F'}


def _finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def graph_cut(system):
    """Only edges present in the selected SystemSpec; no illustrative wires."""
    spec = SystemSpec.from_dict(system)
    authored = spec.metadata.get('native_design_region', {}).get('node_ids')
    region = set(authored or ['world.selection'])
    nodes = {n.mechanism_id: n for n in spec.mechanisms}
    if not region or not region <= set(nodes):
        raise ValueError('selected editable native cut is absent')
    phases = {s.mechanism_id: s.phase for s in spec.schedules}
    internal = sorted(region, key=lambda n: (phases[n], n))
    edges = [c for c in spec.to_dict()['connections']
        if c['source_mechanism'] in region or c['target_mechanism'] in region]
    incoming = sorted({e['source_mechanism'] for e in edges if e['source_mechanism'] not in region})
    outgoing = sorted({e['target_mechanism'] for e in edges if e['target_mechanism'] not in region})
    if len(incoming) > 3 or len(outgoing) > 3 or len(internal) > 6:
        raise ValueError('bounded native cut figure supports at most 6 internal / 3 boundary mechanisms per side')
    return {'system_fingerprint': spec.fingerprint, 'authored': bool(authored),
        'internal_nodes': internal, 'incoming_nodes': incoming, 'outgoing_nodes': outgoing,
        'edges': edges, 'phases': {n: phases[n] for n in internal}}


def load_evidence(report):
    if report.get('schema') != 'scienceutopia.native-joint-objectives-analysis.v5':
        raise ValueError('audited joint-objective v5 report required')
    if report.get('classification') not in (ACTUAL, FIXTURE):
        raise ValueError('explicit actual-native or scripted-fixture classification required')
    if report.get('status') not in ('declared-budget-complete', 'terminal-with-preserved-failures'):
        raise ValueError('terminal audit report required; partial worlds are not observations')
    if len(report['arms']) != 2:
        raise ValueError('this paired-objective figure requires exactly two arms')
    result = []
    for arm_id, arm in report['arms'].items():
        rows = arm['audit']['rows']
        if not rows or arm['loss_path'] != [row['loss'] for row in rows]:
            raise ValueError('objective path differs from audited native observations')
        if 'loss_path' in arm['audit'] and arm['audit']['loss_path'] != arm['loss_path']:
            raise ValueError('nested audit loss path differs')
        for row in rows:
            if row['status'] == 'complete':
                if not _finite(row['loss']):
                    raise ValueError('completed native objective must be finite')
            elif row['loss'] is not None:
                raise ValueError('technical failure cannot be assigned a plotted numerical loss')
        selected = arm['selected_index']
        if type(selected) is not int or not 0 <= selected < len(rows) or rows[selected]['status'] != 'complete':
            raise ValueError('selected index must identify a complete actual observation')
        if rows[selected]['loss'] != min(r['loss'] for r in rows if r['status'] == 'complete'):
            raise ValueError('selected system is not the declared-loss incumbent')
        cut = graph_cut(arm['selected_system'])
        selected_fp = rows[selected].get('system_fingerprint', rows[selected].get('difference', {}).get('candidate_fingerprint'))
        if cut['system_fingerprint'] != arm['selected_fingerprint'] or selected_fp != cut['system_fingerprint']:
            raise ValueError('selected graph identity differs from audited actual observation')
        error = arm.get('authoring_error')
        if error is not None and error.get('loss') is not None:
            raise ValueError('technical authoring failure must retain null loss')
        result.append({'id': arm_id, 'loss_spec': arm['loss_spec'], 'rows': rows,
            'selected_index': selected, 'cut': cut, 'authoring_error': error})
    # Stable semantic order: throughput first, rather than arbitrary JSON order.
    return sorted(result, key=lambda a: (len(a['loss_spec']['per_run']['terms']), a['id']))


def _objective_label(loss):
    symbols = {'native.accepted_decisions': 'A', 'native.accepted_peer_score_sum': 'Q',
        'native.review_records': 'R'}
    terms = []
    intercept = loss['per_run'].get('intercept', 0)
    if intercept:
        terms.append(f'{intercept:g}')
    for term in loss['per_run']['terms']:
        coefficient = term['coefficient']
        symbol = symbols.get(term['metric_id'], term['metric_id'])
        magnitude = '' if abs(coefficient) == 1 else f'{abs(coefficient):g}'
        sign = '-' if coefficient < 0 else ('+' if terms else '')
        terms.append(sign + magnitude + symbol)
    return 'L = ' + ' '.join(terms)


def _short(name):
    return re.sub(r'^generated-[0-9a-f]{12}\.', '', name)


def _draw_graph(ax, evidence, letter, color):
    cut = evidence['cut']
    ax.set(xlim=(-.02, 1.02), ylim=(0, 1))
    ax.axis('off')
    title = 'Selected authored system' if cut['authored'] else 'Original incumbent retained'
    ax.text(0, 1.01, f'{letter}   {title}', fontsize=9, fontweight='semibold', color='#26384B', transform=ax.transAxes)
    ax.text(1, 1.01, f"Objective { _objective_label(evidence['loss_spec']) }  |  observation {evidence['selected_index']}",
        fontsize=7.2, ha='right', color=color, transform=ax.transAxes)
    positions, widths = {}, {}
    internal = cut['internal_nodes']
    span = .30 if len(internal) <= 2 else .58
    for i, node in enumerate(internal):
        positions[node] = (.5 if len(internal) == 1 else .5 - span / 2 + i * span / (len(internal) - 1), .5)
        widths[node] = min(.18, .40 / max(1, len(internal) - 1))
    for names, x in ((cut['incoming_nodes'], .07), (cut['outgoing_nodes'], .93)):
        for i, node in enumerate(names):
            positions[node] = (x, .5 if len(names) == 1 else .74 - i * .48 / (len(names) - 1))
            widths[node] = .13
    pairs = defaultdict(list)
    for edge in cut['edges']:
        pairs[(edge['source_mechanism'], edge['target_mechanism'])].append(edge)
    edge_labels = []
    aspect = ax.get_position().height * ax.figure.get_figheight() / (ax.get_position().width * ax.figure.get_figwidth())
    for (source, target), edges in sorted(pairs.items(), key=lambda item:
            (positions[item[0][0]][0], positions[item[0][1]][0], item[0])):
        edges = sorted(edges, key=lambda e: (e['channel'], e['source_port'], e['target_port']))
        for i, edge in enumerate(edges):
            sx, sy = positions[source]
            tx, ty = positions[target]
            start = sx + widths[source] / 2 + .006, sy
            end = tx - widths[target] / 2 - .006, ty
            skipped = sum(sx < positions[n][0] < tx for n in internal)
            bulge = (i - (len(edges) - 1) / 2) * .20
            if skipped:
                bulge += .24
            rad = -2 * bulge * aspect * 1.04 / max(.03, end[0] - start[0])
            ink = CHANNEL_COLORS.get(edge['channel'], '#6E7F8C')
            ax.add_patch(FancyArrowPatch(start, end, arrowstyle='-|>', mutation_scale=8,
                connectionstyle=f'arc3,rad={rad}', linewidth=1.1, color=ink, zorder=1))
            edge_labels.append(f"{len(edge_labels) + 1}  {edge['source_port']} > {edge['target_port']}")
            label_y = (sy + ty) / 2 + bulge + (.035 if bulge >= 0 else -.035)
            ax.text((start[0] + end[0]) / 2, label_y, str(len(edge_labels)),
                fontsize=6.3, color=ink, ha='center', va='center',
                bbox={'facecolor': 'white', 'edgecolor': 'none', 'pad': 1}, zorder=3)
    for node, (x, y) in positions.items():
        inside = node in internal
        boxcolor = color if inside and cut['authored'] else '#7D8C9A'
        ax.add_patch(FancyBboxPatch((x - widths[node] / 2, y - .15), widths[node], .30,
            boxstyle='round,pad=0.007,rounding_size=0.018', facecolor='#F5F8FB' if inside else '#F2F4F6',
            edgecolor=boxcolor, linewidth=1.2 if inside else .8, zorder=4))
        name = _short(node)
        if len(name) > 38:
            name = name[:35] + '...'
        ax.text(x, y, '\n'.join(textwrap.wrap(name, 19 if widths[node] > .12 else 13)),
            ha='center', va='center', fontsize=7 if widths[node] > .12 else 6.1, color='#26384B', zorder=5)
    if len(edge_labels) <= 8:
        ax.text(.5, .10, textwrap.fill('   |   '.join(edge_labels), width=150),
            ha='center', va='center', fontsize=6, color='#6A7784')
    else:
        ax.text(.5, .12, f'{len(edge_labels)} explicit wires; complete port mappings are bound in the figure manifest.',
            ha='center', va='center', fontsize=6, color='#6A7784')
    if evidence['authoring_error'] and len(evidence['rows']) == 1:
        ax.text(.5, .01, 'No eligible fresh native candidate: bounded technical drafts failed.',
            ha='center', fontsize=7, color='#A15252')


def make_figure(report_path, output):
    report_path, output = Path(report_path).resolve(), Path(output).resolve()
    report = json.loads(report_path.read_text())
    evidence = load_evidence(report)
    fixture = report['classification'] == FIXTURE
    if fixture and any(a == 'paper' and b == 'figures' for a, b in zip(output.parts, output.parts[1:])):
        raise ValueError('scripted fixture figures cannot be written into paper/figures')
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'pdf.fonttype': 42, 'font.size': 8})
    fig = plt.figure(figsize=(7.2, 6.2))
    grid = fig.add_gridspec(3, 2, height_ratios=[1.8, 1.25, 1.25],
        left=.09, right=.985, top=.92, bottom=.095, hspace=.58, wspace=.35)
    for i, arm in enumerate(evidence):
        ax = fig.add_subplot(grid[0, i])
        rows, selected = arm['rows'], arm['selected_index']
        xs = list(range(len(rows)))
        ys = [row['loss'] if row['status'] == 'complete' else math.nan for row in rows]
        ax.plot(xs, ys, color=COLORS[i], lw=1.6, marker='o', ms=4.8, zorder=3)
        ax.scatter([selected], [rows[selected]['loss']], s=80, facecolors='none', edgecolors=COLORS[i], linewidths=1.2, zorder=4)
        for x, y in zip(xs, ys):
            if math.isfinite(y):
                ax.annotate(f'{y:g}', (x, y), xytext=(0, 7), textcoords='offset points', ha='center', fontsize=7.3)
        ax.set_xlim(-.3, max(1.3, len(rows) - .7))
        ax.set_xticks(xs, ['Initial' if x == 0 else f'Revision {x}' for x in xs])
        ax.set_xlabel('Design observation (initial native world shared)', fontsize=6.7)
        ax.set_ylabel('Declared loss (lower is preferred)', fontsize=7)
        ax.set_title(f"{'AB'[i]}   {_objective_label(arm['loss_spec'])}", loc='left', fontsize=9.2, pad=11, color=COLORS[i])
        ax.margins(y=.35)
        ax.spines[['top', 'right']].set_visible(False)
        ax.tick_params(labelsize=7)
        ax.grid(axis='y', color='#E4E9EF', lw=.6)
        if arm['authoring_error']:
            ax.text(.98, .025, 'Technical authoring failure: no loss point', ha='right', va='bottom',
                transform=ax.transAxes, fontsize=6.3, color='#A15252')
        _draw_graph(fig.add_subplot(grid[i + 1, :]), arm, 'CD'[i], COLORS[i])
    heading = 'SCRIPTED QA FIXTURE - NOT NATIVE RESULTS' if fixture else 'Objective-conditioned native institutional design'
    fig.text(.09, .975, heading, fontsize=10, fontweight='semibold', color='#26384B')
    fig.text(.09, .035, 'A: accepted decisions. Q: sum of accepted raw peer-review means. R: actual reviews. Independent loss units; no cross-panel ranking.\n'
        'One development seed; shared physical initial world; selected graphs are real incumbents, not necessarily generated improvements.',
        fontsize=6.6, color='#667585', linespacing=1.6)
    output.parent.mkdir(parents=True, exist_ok=True)
    for suffix in ('.pdf', '.png'):
        options = {'metadata': {'CreationDate': None, 'ModDate': None}} if suffix == '.pdf' else {'dpi': 220}
        fig.savefig(output.with_suffix(suffix), **options)
    plt.close(fig)
    manifest = {'schema': 'scienceutopia.native-joint-objectives-figure.v5',
        'classification': report['classification'], 'source_report_sha256': hashlib.sha256(report_path.read_bytes()).hexdigest(),
        'generator_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'arms': [{'id': arm['id'], 'native_loss_path': [r['loss'] for r in arm['rows']],
            'selected_index': arm['selected_index'], 'selected_graph': arm['cut'],
            'authoring_failure_is_loss_point': False} for arm in evidence],
        'scientific_quality_claim': False, 'held_out': False,
        'outputs': {suffix[1:]: hashlib.sha256(output.with_suffix(suffix).read_bytes()).hexdigest() for suffix in ('.pdf', '.png')}}
    output.with_suffix('.manifest.json').write_text(json.dumps(manifest, indent=2, sort_keys=True, allow_nan=False) + '\n')
    return manifest


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True, help='file stem for PDF, PNG and manifest')
    args = parser.parse_args()
    make_figure(args.report, args.output)
