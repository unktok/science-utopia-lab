"""All common references, old free slots and new numeric slots; no new inference."""
import argparse
import csv
import json
import math
from pathlib import Path

from scripts import run_native_parameter_comparator_v1 as driver
from scripts.analyze_native_open_v7 import _inventory
from utopia.optimization.loss import evaluate_loss
from utopia.system.design_patch import digest, clone


def render(report, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    with plt.rc_context({'font.size': 8, 'axes.spines.top': False, 'axes.spines.right': False,
            'svg.hashsalt': report['schema']}):
        fig, axes = plt.subplots(1, 2, figsize=(10, 4.6))
        for ax, objective, title in zip(axes, report['objectives'], ['Count objective T', 'Content objective U']):
            anchor = report['anchors'][objective]
            ax.axhline(anchor['loss'], color='#596b84', lw=1, ls='--', label='Shared initial reference')
            for method, color in [('prior-free-program', '#9c5d8a'), ('numeric-reserve', '#087f8c')]:
                rows = [r for r in report['slots'] if r['objective'] == objective and r['method'] == method]
                best, path = None, []
                for row in rows:
                    loss = row['assigned_loss']
                    if loss is None:
                        ax.text(row['generation'], .03, 'null', transform=ax.get_xaxis_transform(), ha='center', color=color)
                    else:
                        best = loss if best is None else min(best, loss)
                        ax.scatter(row['generation'], loss, color=color, s=24, zorder=3)
                        if method == 'numeric-reserve':
                            ax.annotate('r=' + str(row['reserve_units']), (row['generation'], loss),
                                xytext=(3, 6), textcoords='offset points', fontsize=7, color=color)
                    path.append(math.nan if best is None else best)
                ax.plot([r['generation'] for r in rows], path, color=color, label=method + ' best own')
            ax.set(title=title, xlabel='Consumed own proposal slot', ylabel='Assigned loss (lower is better)',
                xticks=[0, 1, 2], xlim=(-.3, 2.3))
            ax.grid(axis='y', color='#ededed'); ax.legend(fontsize=7)
        fig.suptitle('Post-hoc native numeric comparator; development seed61001', fontsize=10)
        fig.text(.06, .025, 'Eight audited common references reused; three own proposals per method/objective. '
            'No held-out or independent-history claim.', fontsize=7)
        fig.tight_layout(rect=(0, .07, 1, .94))
        for ext in ('png', 'svg'):
            fig.savefig(output / ('numeric-free-paths.' + ext), dpi=200,
                metadata={'Date': None} if ext == 'svg' else None)
        plt.close(fig)


def export(args):
    root, output = Path(args.run).resolve(), Path(args.output).resolve()
    if output.exists() or output.is_relative_to(root): raise ValueError('fresh report outside raw required')
    p = driver.read(root / 'plan.json'); audits = [driver.read(v) for v in (args.audit_one, args.audit_two)]
    a = audits[0]; before = _inventory(root)
    if (a != audits[1] or a['schema'] != 'scienceutopia.native-parameter-comparator-audit.v1'
            or a['source_commit'] != p['source_commit'] or a['plan_sha256'] != p['content_sha256']
            or a['source_proof']['status'] != 'verified-exact-source-closure'
            or a['closure']['terminal'] != driver.read(root / 'terminal.json')
            or a['closure']['terminal']['status'] != 'closed'
            or a['selection'] != driver.read(root / 'selection.json')
            or a['raw_inventory_sha256'] != digest(before) or a['raw_files'] != len(before)
            or a['new_model_calls'] or a['new_code_executions']):
        raise ValueError('matching unchanged original numeric cold audits required')
    original, prior = driver.origin_evidence(p['origin']); context = driver.context_for(original, p['origin'])
    if context['content_sha256'] != p['reference_context_sha256']: raise ValueError('original reference context changed')
    references = [{'identity': pair['suggestion']['suggestion_id'], 'system_sha256': digest(pair['suggestion']['candidate']),
        'scores': {k: evaluate_loss(v, pair['observation']['metadata']['measurements'])['loss'] for k, v in p['losses'].items()}}
        for pair in context['pairs']]
    old_worlds = {w['identity']: w for w in prior['worlds']}; slots = []
    for objective in p['objectives']:
        state = json.loads((Path(p['origin']['run']) / 'search' / objective / 'campaign/native-adaptive-state.json').read_text())
        if state.get('pending') is not None or len(state['records']) != 3: raise ValueError('all prior free slots required')
        for g, record in enumerate(state['records']):
            if record['request']['generation'] != g or len(record['draws']) != 1 or len(record['observations']) != 1:
                raise ValueError('unique original free proposal slot required')
            suggestion, o = record['draws'][0]['suggestion'], record['observations'][0]
            scores = {k: None for k in p['objectives']}
            if o is not None:
                w = old_worlds[o['suggestion_id']]
                scores = {k: evaluate_loss(v, o['metadata']['measurements'])['loss'] for k, v in p['losses'].items()}
                if (suggestion is None or o['candidate'] != suggestion['candidate'] or o['candidate'] != w['system']
                        or scores != w['scores'] or o['status'] != w['status']):
                    raise ValueError('prior free slot differs from its original audited world')
            elif suggestion is not None or not record['generation_error']:
                raise ValueError('missing prior free observation without generation-null evidence')
            slots.append({'method': 'prior-free-program', 'objective': objective, 'generation': g,
                'identity': o['suggestion_id'] if o else None, 'status': o['status'] if o else 'generation-null',
                'assigned_loss': scores[objective], 'scores': scores, 'reserve_units': None,
                'generation_error': record['generation_error']})
    for w in a['worlds']:
        objective, g = w['objective'], w['generation']
        o = driver.read(root / 'search' / objective / ('generation-' + str(g)) / 'observation.json')
        scores = {k: evaluate_loss(v, o['metadata']['measurements'])['loss'] for k, v in p['losses'].items()}
        if o['candidate'] != w['system'] or o['status'] != w['status'] or scores != w['scores']:
            raise ValueError('numeric slot differs from its cold native proof')
        reserve = driver.space_for(p['anchors'][objective]['reference_suggestion']['candidate']).values(o['candidate'])['coordinate-0']
        slots.append({'method': 'numeric-reserve', 'objective': objective, 'generation': g,
            'identity': w['identity'], 'status': w['status'], 'assigned_loss': scores[objective],
            'scores': scores, 'reserve_units': reserve, 'generation_error': None})
    if len(slots) != 12 or len(references) != 8: raise ValueError('all common/free/numeric slots required')
    anchors = {o: {'identity': p['anchors'][o]['reference_suggestion']['suggestion_id'],
        'loss': p['anchors'][o]['reference_observation']['loss'],
        'space_binding_sha256': p['anchors'][o]['space_binding_sha256']} for o in p['objectives']}
    report = {'schema': 'scienceutopia.native-parameter-comparator-report.v1',
        'source_commit': p['source_commit'], 'plan_sha256': p['content_sha256'],
        'original_audit_sha256': prior['content_sha256'], 'numeric_audit_sha256': a['content_sha256'],
        'objectives': p['objectives'], 'references': references, 'slots': slots, 'anchors': anchors,
        'numeric_selection': clone(a['selection']), 'reused_reference_worlds': 8,
        'reused_free_slots': 6, 'new_numeric_slots': 6, 'posthoc_comparator_design': True,
        'held_out_evaluation': False, 'independent_optimizer_replications': False,
        'isolated_design_freedom_causal_effect_claimed': False, 'publication_ready': False,
        'new_model_calls': 0, 'new_code_executions': 0}
    output.mkdir(parents=True); driver.save(output / 'report.json', report)
    with (output / 'all-slots.csv').open('w', newline='') as handle:
        fields = ['method', 'objective', 'generation', 'identity', 'status', 'assigned_loss', 'throughput', 'content-utility', 'reserve_units']
        writer = csv.DictWriter(handle, fieldnames=fields); writer.writeheader()
        for r in references:
            writer.writerow({'method': 'reused-common-reference', 'identity': r['identity'], 'status': 'complete', **r['scores']})
        for r in slots:
            writer.writerow({**{k: r[k] for k in fields if k in r}, **r['scores']})
    render(report, output)
    if _inventory(root) != before: raise ValueError('raw numeric evidence changed during report')
    return driver.read(output / 'report.json')


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('run', 'audit-one', 'audit-two', 'output'): parser.add_argument('--' + key, type=Path, required=True)
    export(parser.parse_args())


if __name__ == '__main__': main()
