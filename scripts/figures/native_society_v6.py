"""An audited online society trace, never a reset-world policy comparison."""
from __future__ import annotations

import argparse
import json
import math
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.ticker import MaxNLocator

from utopia.utils.data_utils import file_sha256, write_json_atomic

ACTUAL = 'actual-native-qwen-online-design-pilot'
FIXTURE = 'scripted-fixture-not-native-results'


def load_evidence(report):
    if (report.get('schema') != 'scienceutopia.native-society-v6-audit.v1'
            or report.get('classification') not in (ACTUAL, FIXTURE)):
        raise ValueError('explicit audited actual/fixture society classification required')
    if report.get('status') != 'complete' or report.get('physical_societies') != 1:
        raise ValueError('one complete persistent society required; incomplete years are not plotted')
    if report.get('audit_new_model_calls') != 0 or report.get('causal_benefit_established') is not False:
        raise ValueError('read-only, noncausal online evidence required')
    rows = report.get('rows', [])
    adoptions = report.get('adoptions')
    adoption_count = len(adoptions) if isinstance(adoptions, list) else adoptions
    if (len(rows) != 3 or report.get('loss_path') != [r['loss'] for r in rows]
            or adoption_count != 2):
        raise ValueError('three observed intervals and two actual adoptions required')
    values = []
    for year, row in enumerate(rows, 1):
        if (row['after_year'] != year - 1 or row['through_year'] != year
                or type(row['loss']) not in (int, float) or not math.isfinite(row['loss'])):
            raise ValueError('contiguous complete finite interval observations required')
        metrics = row['measurement']['metrics']
        measured = {}
        for name in ('native.accepted_decisions', 'native.rejected_decisions', 'native.review_records'):
            metric = metrics[name]
            value = metric['value']
            if (metric['status'] != 'measured' or type(value) not in (int, float)
                    or not math.isfinite(value) or value < 0 or int(value) != value):
                raise ValueError('actual finite nonnegative count measurements required')
            measured[name] = int(value)
        values.append({'year': year, 'loss': row['loss'],
            'accepted': measured['native.accepted_decisions'],
            'decisions': measured['native.accepted_decisions'] + measured['native.rejected_decisions'],
            'reviews': measured['native.review_records'], 'system_fingerprint': row['system_fingerprint'],
            'code_nodes': len(row.get('code', [])), 'activity_effect_batches': row['actual_activity_effects']})
    return values


def make_figure(report_path, output):
    defaults = dict(matplotlib.rcParamsDefault)
    defaults.pop('backend', None)
    with matplotlib.rc_context(defaults):
        return _make_figure(report_path, output)


def _make_figure(report_path, output):
    report_path, output = Path(report_path), Path(output)
    report = json.loads(report_path.read_text())
    values = load_evidence(report)
    if report['classification'] == FIXTURE and any(
            a == 'paper' and b == 'figures' for a, b in zip(output.parts, output.parts[1:])):
        raise ValueError('fixture figure cannot become a paper/figures empirical asset')
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 8, 'pdf.fonttype': 42,
                         'axes.spines.top': False, 'axes.spines.right': False})
    fig, axes = plt.subplots(1, 2, figsize=(7.2, 3.8), gridspec_kw={'width_ratios': [1.05, 1]})
    fig.subplots_adjust(left=.085, right=.98, bottom=.30, top=.72, wspace=.34)
    years, losses = [v['year'] for v in values], [v['loss'] for v in values]
    left, right = axes
    left.plot(years, losses, color='#276B91', linewidth=2, marker='o', markersize=5)
    span = max(max(losses) - min(losses), 1)
    left.set(xticks=years, xlabel='Completed scientific interval', ylabel='Interval loss (lower is better)',
             ylim=(min(losses) - .18 * span, max(losses) + .34 * span))
    left.set_title('A   One persistent society; no resets', loc='left', fontsize=9, fontweight='bold', pad=32)
    for x, loss in zip(years, losses):
        left.annotate(f'{loss:g}', (x, loss), xytext=(0, 8), textcoords='offset points',
                      ha='center', fontsize=8, color='#205574')
    for boundary in (1.5, 2.5):
        left.axvline(boundary, color='#A3ACB5', linewidth=.8, linestyle=(0, (3, 3)), zorder=0)
        left.text(boundary, 1.03, f'ADOPT {int(boundary)}', transform=left.get_xaxis_transform(),
                  fontsize=6.5, ha='center', color='#626F7D')
    left.grid(axis='y', color='#E4E9ED', linewidth=.7)
    width = .24
    for offset, key, label, color in [(-width, 'decisions', 'Actual decisions', '#A9BDC9'),
                                     (0, 'accepted', 'Accepted', '#2A7996'),
                                     (width, 'reviews', 'Raw reviews', '#BF9253')]:
        bars = right.bar([year + offset for year in years], [v[key] for v in values], width=width,
                        color=color, label=label, zorder=3)
        for bar in bars:
            if bar.get_height():
                right.text(bar.get_x() + bar.get_width()/2, bar.get_height(), f'{bar.get_height():g}',
                           ha='center', va='bottom', fontsize=7)
    right.set(xticks=years, xlabel='Completed scientific interval', ylabel='Actual native count',
              ylim=(0, max(max(v[k] for k in ('decisions', 'accepted', 'reviews')) for v in values) * 1.3 + 1))
    right.set_title('B   Real paper and review flows', loc='left', fontsize=9, fontweight='bold', pad=32)
    right.yaxis.set_major_locator(MaxNLocator(integer=True, nbins=5))
    right.grid(axis='y', color='#E4E9ED', linewidth=.7, zorder=0)
    right.legend(loc='upper left', bbox_to_anchor=(0, 1.13), ncol=3,
                 frameon=False, fontsize=6, borderaxespad=0, handlelength=1.2,
                 handletextpad=.4, columnspacing=.7)
    label = ('ACTUAL NATIVE QWEN / ONLINE DEVELOPMENT' if report['classification'] == ACTUAL
             else 'SCRIPTED QA FIXTURE / NOT NATIVE RESULTS')
    fig.text(.085, .95, label, fontsize=9, fontweight='bold', color='#223C52')
    fig.text(.085, .90, 'Frozen researcher weights; externally authored institutions; no held-out or causal claim.',
             fontsize=7.5, color='#596776')
    counts = ' / '.join(f"Y{v['year']}: {v['code_nodes']} code, {v['activity_effect_batches']} amendment batches" for v in values)
    fig.text(.085, .13, counts, fontsize=6.7, color='#465463')
    fig.text(.085, .065, 'Sequential loss changes are NOT a counterfactual effect estimate or scientific-value improvement.',
             fontsize=7.3, color='#465463')
    output.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(output.with_suffix('.pdf'), metadata={'CreationDate': None, 'ModDate': None})
    fig.savefig(output.with_suffix('.png'), dpi=180, metadata={'Software': 'Science Utopia Lab'})
    plt.close(fig)
    manifest = {'schema': 'scienceutopia.native-society-figure.v6',
        'classification': report['classification'], 'source_report_sha256': file_sha256(report_path),
        'generator_sha256': file_sha256(Path(__file__)), 'observed_intervals': values,
        'physical_societies': 1, 'adoptions': 2, 'causal_benefit_established': False,
        'scientific_value_claim': False,
        'files': {suffix: file_sha256(output.with_suffix(suffix)) for suffix in ('.pdf', '.png')}}
    write_json_atomic(output.with_suffix('.manifest.json'), manifest, sort_keys=True, allow_nan=False)
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--audit', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(make_figure(args.audit, args.output), sort_keys=True))


if __name__ == '__main__':
    main()
