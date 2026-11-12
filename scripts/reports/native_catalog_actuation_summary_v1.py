"""Deterministic tables/figures from matching closed catalog-control exports."""
import argparse
import csv
import json
import math
from pathlib import Path

from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.system.design_patch import clone
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'scienceutopia.native-catalog-actuation-summary.v1'
CONDITIONS = ('cut', 'information', 'project')
OBJECTIVES = ('throughput', 'founder-activity')
COLORS = ('#68788f', '#118b82', '#bc713c')
LABELS = ('No effect', 'Advice', 'Assignment')


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def summarize(report):
    checked(report)
    if (report['schema'] != 'scienceutopia.native-catalog-actuation-report.v1'
            or report['new_model_calls'] or report['new_code_executions']
            or report['loss_or_selection_changed']
            or tuple(w['condition'] for w in report['worlds']) != CONDITIONS
            or len({w['identity'] for w in report['worlds']}) != 3
            or len({w['seed'] for w in report['worlds']}) != 1):
        raise ValueError('exact three-control report with unchanged outcomes required')
    catalog = {d['topic']: d['years'] for d in report['catalog']['directions']}
    worlds, projects, founders = [], [], None
    for world in report['worlds']:
        if world['status'] not in ('complete', 'failed'):
            raise ValueError('known complete/failed control status required')
        complete = world['status'] == 'complete'
        if (any(not finite(world['scores'][o]) for o in OBJECTIVES) if complete
                else any(world['scores'][o] is not None for o in OBJECTIVES)):
            raise ValueError('complete scores must be finite; technical nulls must remain null')
        years = [s['year'] for s in world['annual']]
        if years != list(range(1, len(years) + 1)) or len(years) > 4 or complete and years != [1, 2, 3, 4]:
            raise ValueError('exact original annual prefix required')
        annual = []
        for state in world['annual']:
            authors = state['authors']; ids = sorted(a['id'] for a in authors)
            if (len(ids) != 5 or len(set(ids)) != 5
                    or any(type(a['is_active']) is not bool or not finite(a['resources']) for a in authors)):
                raise ValueError('five actual retained founder records required')
            if founders is None: founders = ids
            if founders != ids: raise ValueError('common original founder identities differ')
            active = sum(a['is_active'] for a in authors)
            annual.append({'year': state['year'], 'active_founders': active,
                'total_founder_resources': math.fsum(a['resources'] for a in authors)})
            for a in sorted(authors, key=lambda a: a['id']):
                direction = a['newest_direction']; topic = None if direction is None else direction.get('direction')
                start, end = a['project_start_year'], a['project_end_year']
                if type(start) is not int or type(end) is not int: raise ValueError('literal native project dates required')
                duration = catalog.get(topic)
                if topic is not None and (duration is None or end - start + 1 != duration):
                    raise ValueError('actual project dates must preserve original catalog duration')
                projects.append({'condition': world['condition'], 'status': world['status'], 'seed': world['seed'],
                    'actor_id': a['id'], 'year': state['year'], 'is_active': a['is_active'],
                    'resources': a['resources'], 'topic': topic, 'catalog_duration_years': duration,
                    'project_start_year': start, 'project_end_year': end})
        if complete and world['scores']['founder-activity'] != -sum(s['active_founders'] for s in annual):
            raise ValueError('P differs from actual founder boundary states')
        wires, replies = world['physical_wire_requests'], world['committed_responses']
        if (type(wires) is not int or type(replies) is not int or not 0 <= replies <= wires
                or world['wire_without_committed_reply'] != wires - replies):
            raise ValueError('actual request/reply counts required')
        requests = world['direction_requests']
        if len({r['wire_index'] for r in requests}) != len(requests):
            raise ValueError('duplicate direction request attempt')
        worlds.append({'identity': world['identity'], 'condition': world['condition'], 'seed': world['seed'],
            'status': world['status'], 'scores': clone(world['scores']), 'annual': annual,
            'physical_wire_requests': wires, 'committed_responses': replies,
            'wire_without_committed_reply': wires - replies, 'direction_request_attempts': len(requests),
            'direction_inputs_with_advisory_agenda': sum(r['literal_instruction_present'] for r in requests),
            'verified_catalog_project_effects': len(world['catalog_project_effects'])})
    cut = worlds[0]
    for world in worlds:
        world['loss_difference_from_cut'] = {o: world['scores'][o] - cut['scores'][o]
            if world['status'] == cut['status'] == 'complete' else None for o in OBJECTIVES}
    return {'schema': SCHEMA, 'scientific_source_commit': report['scientific_source_commit'],
        'original_report_content_sha256': report['content_sha256'], 'plan_sha256': report['plan_sha256'],
        'audit_content_sha256': report['audit_content_sha256'], 'raw_inventory_sha256': report['raw_inventory_sha256'],
        'worlds': worlds, 'founder_ids': founders or [], 'annual_project_states': projects,
        'scope': 'Three developer controls at one reused seed. All project rows are saved year-end states, '
            'not completed-project counts or within-year activity. P counts native active founder flags, '
            'not meaningful scientific work. Assignment replaces a planning choice; fewer requests do '
            'not establish advice obedience. Failed prefixes remain diagnostic and acquire no loss. '
            'Cut-relative differences are descriptive, not independent replication, automatic invention '
            'or optimizer superiority. No outcome or selection changes.',
        'new_model_calls': 0, 'new_code_executions': 0, 'new_native_worlds': 0,
        'loss_or_selection_changed': False, 'publication_ready': False}


def render(summary, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch
    output = Path(output)
    with plt.rc_context({'font.size': 9, 'axes.spines.top': False,
                         'axes.spines.right': False, 'svg.hashsalt': SCHEMA}):
        fig, axes = plt.subplots(1, 3, figsize=(9.3, 2.8))
        for ax, objective, title in zip(axes[:2], OBJECTIVES, ('Throughput loss T', 'Founder activity loss P')):
            for i, world in enumerate(summary['worlds']):
                value = world['scores'][objective]
                if value is None:
                    ax.annotate('null', (i, 0), ha='center', va='bottom', fontsize=9)
                else:
                    ax.bar(i, value, color=COLORS[i], width=.56)
                    ax.annotate(format(value, '.6g'), (i, value), xytext=(0, -12 if value < 0 else 5),
                        textcoords='offset points', ha='center', fontsize=9)
            ax.set(xticks=range(3), xticklabels=LABELS, title=title, ylabel='Loss (lower is better)')
            ax.tick_params(axis='x', labelsize=8); ax.margins(y=.25)
            ax.set_axisbelow(True); ax.grid(axis='y', color='#edf0f2')
        for i, world in enumerate(summary['worlds']):
            rows = world['annual']
            if rows:
                axes[2].plot([r['year'] for r in rows], [r['active_founders'] for r in rows],
                    color=COLORS[i], marker=('o', 's', '^')[i], ms=(8, 6, 4)[i],
                    markerfacecolor='none', label=LABELS[i],
                    linestyle='-' if world['status'] == 'complete' else '--')
        axes[2].set(title='Saved founder activity', xlabel='Native year', ylabel='Active founder flags',
            xticks=(1, 2, 3, 4), yticks=range(6), ylim=(-.3, 5.4))
        axes[2].grid(axis='y', color='#edf0f2'); axes[2].legend(frameon=False, fontsize=7)
        fig.tight_layout()
        for ext in ('png', 'svg'):
            fig.savefig(output / ('losses-and-activity.' + ext), dpi=220,
                metadata={'Date': None} if ext == 'svg' else None)
        plt.close(fig)

        founders = summary['founder_ids']; height = max(3., len(founders) * .70 + 1.6)
        fig, axes = plt.subplots(1, 3, figsize=(9.3, height), sharey=True)
        for ax, condition, label in zip(axes, CONDITIONS, LABELS):
            rows = {(r['actor_id'], r['year']): r for r in summary['annual_project_states'] if r['condition'] == condition}
            for i, actor in enumerate(founders):
                for year in (1, 2, 3, 4):
                    row = rows.get((actor, year))
                    color = '#f5f6f8' if row is None else '#c7e8df' if row['is_active'] else '#e1e4e9'
                    ax.add_patch(plt.Rectangle((year - .47, i - .44), .94, .88, color=color, lw=0,
                        hatch='//' if row is None else None))
                    text = 'missing' if row is None else 'no project' if row['topic'] is None else (
                        str(row['catalog_duration_years']) + 'y\n' + str(row['project_start_year']) + '–' + str(row['project_end_year']))
                    ax.text(year, i, text, ha='center', va='center', fontsize=8)
            ax.set(title=label, xlabel='Saved native year', xticks=(1, 2, 3, 4), xlim=(.5, 4.5),
                yticks=range(len(founders)), yticklabels=['Founder ' + str(i + 1) for i in range(len(founders))],
                ylim=(len(founders) - .5, -.5))
            ax.tick_params(axis='both', length=0)
        fig.legend(handles=[Patch(color=c, label=l) for c, l in (
            ('#c7e8df', 'Native active flag'), ('#e1e4e9', 'Native inactive flag'),
            ('#f5f6f8', 'Unsaved boundary'))], loc='lower center', ncol=3, frameon=False, fontsize=8)
        fig.suptitle('Actual project states: catalog duration and native start–end year', fontsize=11)
        fig.tight_layout(rect=(0, .07, 1, .94))
        for ext in ('png', 'svg'):
            fig.savefig(output / ('project-states.' + ext), dpi=220,
                metadata={'Date': None} if ext == 'svg' else None)
        plt.close(fig)


def export(args):
    one, two, output = args.one.resolve(), args.two.resolve(), args.output.resolve()
    source = pinned_revision(ROOT)
    if (one == two or one.read_bytes() != two.read_bytes() or output.exists()
            or any(output.is_relative_to(p.parent) or p.is_relative_to(output) for p in (one, two))):
        raise ValueError('two matching distinct reports and fresh separate output required')
    inputs = {str(p): file_sha256(p) for p in (one, two)}
    summary = summarize(json.loads(one.read_text())); output.mkdir(parents=True)
    save(output / 'summary.json', summary)
    rows = summary['annual_project_states']
    fields = ['condition', 'status', 'seed', 'actor_id', 'year', 'is_active', 'resources', 'topic',
        'catalog_duration_years', 'project_start_year', 'project_end_year']
    with (output / 'annual-project-states.csv').open('x', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=fields); writer.writeheader(); writer.writerows(rows)
    render(summary, output)
    if inputs != {str(p): file_sha256(p) for p in (one, two)} or pinned_revision(ROOT) != source:
        raise ValueError('closed inputs or reader source changed')
    save(output / 'manifest.json', {'schema': SCHEMA + '.export', 'analysis_source_commit': source,
        'inputs': inputs, 'files': {p.name: file_sha256(p) for p in sorted(output.iterdir())},
        'new_model_calls': 0, 'new_code_executions': 0, 'new_native_worlds': 0, 'visual_review_complete': False})
    print(json.dumps({'worlds': 3, 'project_state_rows': len(rows)}), flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('one', 'two', 'output'): parser.add_argument('--' + name, type=Path, required=True)
    export(parser.parse_args())


if __name__ == '__main__': main()
