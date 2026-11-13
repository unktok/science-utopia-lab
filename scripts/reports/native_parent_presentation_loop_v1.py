"""All four histories and eight controls after original double cold proof."""
import argparse
import json
import math
from pathlib import Path

from utopia.system.design_patch import clone, digest


def first_planner_trace(request, inner, steps):
    """Record what was supplied and returned, not a claim about model beliefs."""
    started = json.loads((inner/'step-00.started.json').read_text())
    view = json.loads(started['prompt'])
    first = steps[0]
    if started['step'] != first['step'] or first['step'] != 0:
        raise ValueError('original first planner step required')
    from utopia.optimization.native_parent_evidence_v46 import OPTION, MODE, describe
    literal = request.get('strategy_provenance', {}).get(OPTION) == MODE
    evidence = view.get('planning_parent_evidence')
    if literal:
        if view['literal_current_system'] != request['parent_system'] or evidence != describe(request):
            raise ValueError('literal first planner source/observation differs')
    elif view['literal_current_system'] is not None or evidence is not None:
        raise ValueError('control first planner unexpectedly contains literal treatment')
    transition = first.get('transition') or {}
    transport = first['model_reply'].get('transport') or {}
    response = transport.get('response_payload') or {}
    plan = (transition['result']['stored_model_authored_plan']
            if transition.get('tool') == 'plan' and transition.get('ok') else None)
    return {'first_prompt_sha256': digest(started['prompt']),
        'first_prompt_utf8_bytes': len(started['prompt'].encode()),
        'literal_parent_included': literal, 'selected_parent_system_sha256': digest(request['parent_system']),
        'planning_parent_evidence': clone(evidence), 'first_step_status': first['status'],
        'first_tool': transition.get('tool'), 'untrusted_first_plan': clone(plan),
        'reported_prompt_eval_count': response.get('prompt_eval_count'),
        'reported_eval_count': response.get('eval_count'), 'reported_done_reason': response.get('done_reason'),
        'reasoning_or_causal_effect_inferred': False}

from scripts.reports.native_objective_instrument_loop_v1 import export as export_study, cross_score_groups


def render(report, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    if len(report['slots']) != 12 or len(report['references']) != 8 or len(report['arm_order']) != 4:
        raise ValueError('complete four-history/twelve-slot presentation report required')
    palette = {'control': '#087f8c', 'literal': '#b47835'}
    with plt.rc_context({'font.size': 8, 'svg.hashsalt': report['schema'],
                        'axes.spines.top': False, 'axes.spines.right': False}):
        fig, axes = plt.subplots(1, 2, figsize=(10, 6.2))
        for ax, objective in zip(axes, report['score_order']):
            for i, ref in enumerate(report['references']):
                ax.axhline(ref['scores'][objective], color='#b4bac1', ls='--', lw=.7,
                    label='Eight fresh references' if i == 0 else None)
            for presentation, color in palette.items():
                rows = sorted([r for r in report['slots'] if r['objective'] == objective
                    and r['presentation'] == presentation], key=lambda r:r['generation'])
                best = None; path = []
                for row in rows:
                    if row['loss'] is not None:
                        best = row['loss'] if best is None else min(best, row['loss'])
                        ax.scatter(row['generation'], row['loss'], color=color,
                            marker='o' if presentation == 'control' else 'x', s=35, zorder=3)
                    else:
                        ax.text(row['generation'], .02 if presentation == 'control' else .08,
                            presentation+' null', transform=ax.get_xaxis_transform(), ha='center', fontsize=6)
                    path.append(math.nan if best is None else best)
                ax.plot([r['generation'] for r in rows], path, color=color,
                    ls='-' if presentation == 'control' else ':', label=presentation+' best own')
            ax.set(title=objective, xlabel='Consumed proposal generation', ylabel='Assigned loss (lower is better)',
                xticks=[0,1,2], xlim=(-.3,2.3))
            ax.grid(axis='y', color='#ededed'); ax.legend(fontsize=7)
        fig.suptitle('First-planner parent presentation: every assigned loss and own best', fontsize=10)
        fig.text(.06, .235, 'One development history per objective/presentation; shared fresh references. '
                 'Equal points overlap; no jitter or independent-replication claim.', fontsize=7)
        reference_key = ['R'+str(i+1)+' = '+r['label'] for i,r in enumerate(report['references'])]
        for x, labels in ((.06,reference_key[:4]),(.55,reference_key[4:])):
            fig.text(x,.045,'\n'.join(labels),va='bottom',fontsize=6.5,linespacing=1.5)
        fig.tight_layout(rect=(0,.28,1,.94))
        for ext in ('png','svg'):
            fig.savefig(output/('objective-loss-paths.'+ext), dpi=200,
                metadata={'Date':None} if ext == 'svg' else None)
        plt.close(fig)
        groups, missing = cross_score_groups(report)
        fig, axes = plt.subplots(1,2,figsize=(10,6),gridspec_kw={'width_ratios':[1,1.3]})
        ax, key = axes
        for group in groups:
            ax.scatter(group['T'], group['U'], color='#087f8c', s=35)
            ax.annotate(group['group'], (group['T'],group['U']), xytext=(4,4), textcoords='offset points')
        ax.set(xlabel='Count loss T',ylabel='Content loss U',title='Exact observed score points')
        ax.grid(color='#ededed'); key.axis('off')
        import textwrap
        cells = [[g['group'],f"{g['T']:g}",f"{g['U']:g}",textwrap.fill(', '.join(g['labels']),32)] for g in groups]
        if cells:
            table = key.table(cellText=cells,colLabels=['Point','T','U','All world labels'],
                colWidths=[.12,.14,.14,.60],bbox=(0,.35,1,.60),cellLoc='left')
            table.auto_set_font_size(False); table.set_fontsize(6.5)
            for (i,j), cell in table.get_celld().items():
                cell.set_edgecolor('#d8dee5'); cell.set_linewidth(.5)
                if i == 0: cell.set_facecolor('#edf2f5')
        labels = ['R'+str(i+1)+' = '+r['label'] for i,r in enumerate(report['references'])]
        labels += ['T/U = assigned objective; C/L = control/literal; digit = generation.']
        if missing: labels += ['Unavailable cross-scores: '+', '.join(missing)]
        key.text(0,.30,'\n'.join(labels),va='top',fontsize=6.5,linespacing=1.5)
        fig.suptitle('Both fixed criteria on all completed worlds; every tie retained',fontsize=10)
        fig.tight_layout(rect=(0,.02,1,.94))
        for ext in ('png','svg'):
            fig.savefig(output/('objective-cross-scores.'+ext),dpi=200,
                metadata={'Date':None} if ext == 'svg' else None)
        plt.close(fig)


def export(args):
    return export_study(args, study='parent-presentation-v1', renderer=render)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for key in ('run','audit-one','audit-two','output'):
        parser.add_argument('--'+key,type=Path,required=True)
    export(parser.parse_args())


if __name__ == '__main__':
    main()
