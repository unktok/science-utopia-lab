"""Plot audited native source-search outcomes, never conditional proxy fits."""
import ast
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parents[2]


def load_evidence(audit, system):
    from utopia.system import SystemSpec
    from utopia.system.code_mechanisms import sha
    if not audit['campaign_budget_completed'] or not audit['common_initial_physical_state'] or len(audit['rows']) != 3:
        raise ValueError('complete three-system native campaign with common initial state required')
    if audit['binding']['world']['proposer'] != 'free-source':
        raise ValueError('not the recorded model source-search campaign')
    for row in audit['rows']:
        if row['status'] != 'complete' or len(row['runs']) != 1 or row['loss'] != -row['runs'][0]['counts']['native.accepted_decisions']:
            raise ValueError('actual accepted-count loss evidence differs')
    spec = SystemSpec.from_dict(system)
    if spec.fingerprint != audit['rows'][-1]['difference']['candidate_fingerprint']:
        raise ValueError('selected system identity differs from actual source campaign')
    node = next(n for n in spec.mechanisms if n.mechanism_id == 'world.selection')
    source = node.parameters['code_artifact']['source']
    if sha(source) != audit['proposals'][-1]['source_sha256']:
        raise ValueError('model-generated source identity differs')
    thresholds = [n.value.value for n in ast.walk(ast.parse(source)) if isinstance(n, ast.Assign)
        and isinstance(n.value, ast.Constant) and any(isinstance(t, ast.Name) and t.id == 'threshold_score' for t in n.targets)]
    if len(thresholds) != 1:
        raise ValueError('no unambiguous actual generated threshold')
    return [row['loss'] for row in audit['rows']], thresholds[0]


def make_figure():
    audit = json.loads((ROOT / 'research/results/native-open-source-v3.json').read_text())
    system = json.loads((ROOT / 'research/artifacts/native-open-source-v3-selected-system.json').read_text())
    losses, threshold = load_evidence(audit, system)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'pdf.fonttype': 42})
    fig, ax = plt.subplots(figsize=(6.4, 1.95))
    fig.subplots_adjust(left=.10, right=.98, bottom=.30, top=.87)
    ax.plot(range(3), losses, color='#3269A8', marker='o', lw=1.5, ms=5)
    for i, value in enumerate(losses):
        ax.annotate(f'{value:g}', (i, value), xytext=(0, 7), textcoords='offset points', ha='center', fontsize=8)
    ax.set_xticks(range(3), ['Initial\nrank / rate', 'Revision 1\nno observed change', f'Revision 2\nscore ≥ {threshold:g}'])
    ax.set_xlim(-.35, 2.35)
    ax.set_ylabel('Native loss\n(negative accepted count)', fontsize=8)
    ax.set_yticks([-3, -2, -1])
    ax.set_ylim(-3.35, -.55)
    ax.tick_params(labelsize=7.2)
    ax.spines[['top', 'right']].set_visible(False)
    ax.grid(axis='y', color='#E0E6ED', lw=.6)
    ax.set_title('Model-written source search: fresh native executions', fontsize=9, loc='left', pad=8)
    fig.text(.98, .025, 'One development seed; 2 years/system; fixed ports/wiring; lower count loss is not better science.',
        ha='right', fontsize=6.9, color='#637285')
    output = ROOT / 'paper/figures/native-open-source-v3'
    fig.savefig(output.with_suffix('.pdf'), metadata={'CreationDate': None, 'ModDate': None})
    fig.savefig(output.with_suffix('.png'), dpi=200)
    plt.close(fig)
    inputs = ['research/results/native-open-source-v3.json',
        'research/artifacts/native-open-source-v3-selected-system.json',
        'scripts/figures/native_open_source.py']
    manifest = {'schema': 'scienceutopia.native-source-search-figure.v1',
        'classification': 'actual-native-development-outcomes-not-heldout',
        'inputs': {p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest() for p in inputs},
        'native_losses': losses, 'source_threshold': threshold, 'scientific_quality_claim': False,
        'outputs': {str(output.with_suffix(s).relative_to(ROOT)): hashlib.sha256(output.with_suffix(s).read_bytes()).hexdigest() for s in ('.pdf', '.png')}}
    output.with_suffix('.manifest.json').write_text(json.dumps(manifest, sort_keys=True, indent=2) + '\n')


if __name__ == '__main__':
    make_figure()
