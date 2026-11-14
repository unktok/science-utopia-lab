"""Print-sized annual paths from double-audited stopped-study control cells."""
import argparse
import json
from pathlib import Path

from scripts.audit_native_workflow_stopped_controls_v1 import SCHEMA as AUDIT_SCHEMA
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'scienceutopia.workflow-completed-controls-paper.v1'
LABELS = {'workflow-reference-r7-original': 'Original R7',
    'workflow-reference-post-funding-cost': 'Hand timing/routing'}


def summarize(audit):
    checked(audit)
    if (audit['schema'] != AUDIT_SCHEMA or audit['scientific_study_closed'] is not False
            or audit['original_closure']['terminal']['status'] != 'stopped'
            or audit['selection'] is not None or audit['fixed_evaluation_eligible'] is not False
            or audit['source_proof']['status'] != 'verified-exact-source-closure'
            or audit['new_model_calls'] or audit['new_code_executions']
            or {w['identity'] for w in audit['worlds']} != set(LABELS)
            or len(audit['worlds']) != 2 or len(audit['effect_traces']) != 2):
        raise ValueError('exact separate completed-control proof, not normal study closure, required')
    traces = {t['identity']: t for t in audit['effect_traces']}
    if len(traces) != 2: raise ValueError('unique original control traces required')
    rows = []
    for world in audit['worlds']:
        trace = traces[world['identity']]; proof = world['physical_proof']
        if (world['status'] != 'complete' or world['role'] != 'developer-reference'
                or world['seed'] != 61001 or proof['status'] != 'complete'
                or [r['year'] for r in trace['annual']] != [1, 2, 3, 4]
                or [r['checkpoint_sha256'] for r in trace['annual']]
                    != [r['checkpoint_sha256'] for r in proof['annual_checkpoints']]):
            raise ValueError('literal complete original checkpoint/trace lineage required')
        annual = []
        for r in trace['annual']:
            boundary = r['workflow_boundary']; cash = boundary['all_author_cashflows']
            annual.append({'year': r['year'], 'active_original_authors': r['active_founders'],
                'original_author_resources': r['total_founder_resources'],
                'all_author_grants': cash['grant_income'], 'all_author_research_cost': cash['annual_research_cost'],
                'internal_transfer_debit': cash['institution_transfer_out'],
                'internal_transfer_credit': cash['institution_transfer_in']})
        rows.append({'identity': world['identity'], 'label': LABELS[world['identity']],
            'scores': world['scores'], 'seed': world['seed'], 'annual': annual})
    return {'schema': SCHEMA + '.data', 'audit_content_sha256': audit['content_sha256'],
        'scientific_source_commit': audit['source_commit'], 'analysis_adapter': audit['external_adapter'],
        'worlds': rows, 'scientific_study_closed': False,
        'causal_cost_order_effect_identified': False, 'automatic_invention': False,
        'independent_experimental_replication': False, 'additional_objective_or_veto': False,
        'new_model_calls': 0, 'new_scientist_worlds': 0}


def render(data, out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    with plt.rc_context({'font.size': 9, 'axes.titlesize': 10, 'axes.spines.top': False,
            'axes.spines.right': False, 'svg.hashsalt': SCHEMA}):
        fig, axes = plt.subplots(1, 2, figsize=(6.4, 2.85))
        for world, color, marker, line in zip(data['worlds'], ['#526b7b', '#087f8c'], ['o', 'D'], ['-', '--']):
            years = [r['year'] for r in world['annual']]
            for ax, key in zip(axes, ['active_original_authors', 'original_author_resources']):
                ax.plot(years, [r[key] for r in world['annual']], label=world['label'], color=color,
                    marker=marker, markerfacecolor='none', markersize=5, lw=1.5, ls=line)
        for ax in axes:
            ax.set(xlabel='World year (end boundary)', xticks=[1, 2, 3, 4], xlim=(.85, 4.15))
            ax.grid(axis='y', color='#e9edef'); ax.set_axisbelow(True)
        axes[0].set(title='A. Active original authors', ylabel='Authors', yticks=range(6), ylim=(0, 5.6))
        axes[1].set(title='B. Original-author resources', ylabel='Resource units', yticks=[0, 40, 80, 120], ylim=(0, 140))
        handles, labels = axes[0].get_legend_handles_labels()
        fig.legend(handles, labels, loc='lower center', ncol=2, frameon=False, fontsize=8)
        fig.tight_layout(rect=(0, .10, 1, 1), pad=.5, w_pad=1.1)
        for extension in ('png', 'svg'):
            fig.savefig(out / ('annual-paths.' + extension), dpi=300,
                metadata={'Date': None} if extension == 'svg' else None)
        plt.close(fig)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for key in ('audit-one', 'audit-two', 'output'): p.add_argument('--' + key, type=Path, required=True)
    args = p.parse_args(); source = pinned_revision(ROOT)
    paths = [args.audit_one, args.audit_two]; inputs = {str(p.resolve()): file_sha256(p) for p in paths}
    if args.output.exists() or args.audit_one.read_bytes() != args.audit_two.read_bytes():
        raise ValueError('fresh output and two byte-identical original-source control reports required')
    data = summarize(checked(json.loads(args.audit_one.read_text())))
    args.output.mkdir(parents=True); save(args.output / 'data.json', data); render(data, args.output)
    if inputs != {str(p.resolve()): file_sha256(p) for p in paths} or pinned_revision(ROOT) != source:
        raise ValueError('paper source or audit inputs changed')
    save(args.output / 'manifest.json', {'schema': SCHEMA, 'source_commit': source, 'inputs': inputs,
        'files': {p.name: file_sha256(p) for p in sorted(args.output.iterdir())},
        'original_coordinates_changed': False, 'new_model_calls': 0, 'new_scientist_worlds': 0})


if __name__ == '__main__': main()
