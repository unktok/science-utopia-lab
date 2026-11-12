"""Portable descriptive tables and figures from two matching closed choice reads.

This reader never executes an institution or contacts a scientist/designer.
Request attempts, committed memories and annual states stay separate units.
"""
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
SCHEMA = 'scienceutopia.native-instruction-timing-summary.v1'
CONDITIONS = ('cut', 'early', 'late')
OBJECTIVES = ('throughput', 'content-utility')


def finite(value):
    return type(value) in (int, float) and math.isfinite(value)


def summarize(report):
    checked(report)
    if (report['schema'] != 'scienceutopia.native-instruction-timing-report.v1'
            or report['new_model_calls'] != 0 or report['new_code_executions'] != 0
            or report['policy_selection'] is not False
            or tuple(w['condition'] for w in report['worlds']) != CONDITIONS
            or len({w['seed'] for w in report['worlds']}) != 1
            or len({w['identity'] for w in report['worlds']}) != 3):
        raise ValueError('complete matching three-condition choice report required')
    worlds, decisions = [], []
    for w in report['worlds']:
        if ([s['year'] for s in w['annual']] != [1, 2, 3, 4]
                or any(not finite(w['scores'][o]) for o in OBJECTIVES)
                or len({r['wire_index'] for r in w['direction_requests']}) != len(w['direction_requests'])):
            raise ValueError('all native years, finite losses and unique request indices required')
        rows = []
        for r in w['direction_requests']:
            if (type(r['year']) is not int or r['year'] not in (1, 2, 3, 4)
                    or type(r['wire_index']) is not int or r['wire_index'] < 0
                    or r['unique_actor_attribution'] != (len(r['matching_actual_memory_actor_ids']) == 1)
                    or type(r['literal_instruction_present']) is not bool
                    or (r['selected_is_shortest_displayed'] is not None
                        and type(r['selected_is_shortest_displayed']) is not bool)):
                raise ValueError('literal decision attempt and attribution required')
            known = r['selected_catalog_duration_years']
            minimum = r['minimum_displayed_duration_years']
            if ((known is not None and (type(known) is not int or known < 1))
                    or (minimum is not None and (type(minimum) is not int or minimum < 1))):
                raise ValueError('positive original catalog durations or explicit unknown required')
            row = {k: clone(r[k]) for k in (
                'wire_index', 'year', 'payload_sha256', 'literal_instruction_present',
                'frame_status', 'reply_status', 'selected_topic',
                'selected_catalog_duration_years', 'minimum_displayed_duration_years',
                'selected_is_shortest_displayed', 'unique_actor_attribution',
                'matching_actual_memory_actor_ids')}
            row.update(condition=w['condition'], identity=w['identity'], seed=w['seed'])
            # Only the literal displayed set supports this comparison. A related
            # topic omitted from that table is not a disobedience/invalidity case.
            row['displayed_shorter_alternative_to_selected'] = (
                None if r['selected_is_shortest_displayed'] is None else not r['selected_is_shortest_displayed'])
            rows.append(row)
        annual = []
        for state in w['annual']:
            authors = state['authors']
            if (len({a['id'] for a in authors}) != len(authors)
                    or any(type(a['is_active']) is not bool or not finite(a['resources']) for a in authors)):
                raise ValueError('literal distinct annual authors and resources required')
            annual.append({'year': state['year'], 'authors': len(authors),
                'active_authors': sum(a['is_active'] for a in authors),
                'total_author_resources': math.fsum(a['resources'] for a in authors),
                'project_states': clone(authors)})
        assessable = [r for r in rows if r['selected_is_shortest_displayed'] is not None]
        durations = [r['selected_catalog_duration_years'] for r in rows
                     if r['selected_catalog_duration_years'] is not None]
        worlds.append({'identity': w['identity'], 'condition': w['condition'], 'seed': w['seed'],
            'scores': clone(w['scores']), 'annual': annual,
            'direction_request_attempts': len(rows),
            'direction_requests_with_literal_instruction': sum(r['literal_instruction_present'] for r in rows),
            'committed_direction_memories': len(w['direction_memories']),
            'stored_instruction_records': len(w['stored_instructions']),
            'uniquely_attributed_request_attempts': sum(r['unique_actor_attribution'] for r in rows),
            'shortest_displayed_assessable_attempts': len(assessable),
            'shortest_displayed_selected_attempts': sum(r['selected_is_shortest_displayed'] for r in assessable),
            'known_selected_duration_attempts': len(durations),
            'mean_catalog_duration_on_known_attempts': None if not durations else math.fsum(durations)/len(durations),
            'physical_wire_requests': w['physical_wire_requests'],
            'committed_responses': w['committed_responses'],
            'wire_without_committed_reply': w['wire_without_committed_reply']})
        decisions.extend(rows)
    cut = worlds[0]['scores']
    for w in worlds:
        w['loss_difference_from_cut'] = {o: w['scores'][o]-cut[o] for o in OBJECTIVES}
    return {'schema': SCHEMA, 'scientific_source_commit': report['scientific_source_commit'],
        'original_report_content_sha256': report['content_sha256'],
        'plan_sha256': report['plan_sha256'], 'audit_content_sha256': report['audit_content_sha256'],
        'raw_inventory_sha256': report['raw_inventory_sha256'], 'worlds': worlds, 'decisions': decisions,
        'scope': 'Three developer controls on one reused seed. All direction request attempts remain '
            'listed, including uncommitted/ambiguous/unparseable attempts. Attempt counts are not '
            'independent researcher choices or repetitions. Known-duration means condition on '
            'observed catalog matches. A shortest displayed choice need not be optimal; legacy '
            'related topics may be unlisted. Cut-relative differences are descriptive, not '
            'mediation estimates or optimizer/invention advantages. Annual project states do '
            'not reconstruct unsaved within-year boundaries. No loss or selection is changed.',
        'new_model_calls': 0, 'new_code_executions': 0, 'new_native_worlds': 0,
        'policy_selection': False, 'publication_ready': False}


def render(summary, output):
    """Exact native-year cells; do not jitter repeated attempts into fake years."""
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import Patch

    with plt.rc_context({'font.size': 9, 'axes.spines.top': False,
                         'axes.spines.right': False, 'svg.hashsalt': SCHEMA}):
        fig, axes = plt.subplots(1, 2, figsize=(6.6, 2.7))
        for ax, objective, title in zip(axes, OBJECTIVES, ('Count loss T', 'Content-opinion loss U')):
            values = [w['scores'][objective] for w in summary['worlds']]
            ax.bar(CONDITIONS, values, color=['#66758b', '#087f8c', '#c6893b'], width=.55)
            for i, value in enumerate(values):
                ax.annotate(format(value, '.6g'), (i, value), xytext=(0, -12 if value < 0 else 5),
                            textcoords='offset points', ha='center', fontsize=9)
            ax.set(title=title, ylabel='Assigned loss (lower is better)')
            ax.margins(y=.25); ax.set_axisbelow(True); ax.grid(axis='y', color='#edf0f2')
        fig.tight_layout()
        for ext in ('png', 'svg'):
            fig.savefig(output/('losses.'+ext), dpi=240, metadata={'Date': None} if ext == 'svg' else None)
        plt.close(fig)

        cells, labels = [], []
        for w in summary['worlds']:
            authors = sorted({a['id'] for s in w['annual'] for a in s['project_states']})
            records = [r for r in summary['decisions'] if r['identity'] == w['identity']]
            if any(not r['unique_actor_attribution'] for r in records):
                authors.append(None)
            for index, actor in enumerate(authors, 1):
                # Local display labels never imply an actor match across worlds.
                labels.append(w['condition']+' / '+('unattributed' if actor is None else 'actor '+str(index)))
                own = [r for r in records if (r['unique_actor_attribution'] and
                       r['matching_actual_memory_actor_ids'] == [actor]) or
                       (actor is None and not r['unique_actor_attribution'])]
                cells.append([[r for r in own if r['year'] == year] for year in (1, 2, 3, 4)])
        fig, ax = plt.subplots(figsize=(6.6, max(3.8, len(labels)*.24+1.25)))
        for y, row in enumerate(cells):
            for x, records in enumerate(row, 1):
                flags = {r['literal_instruction_present'] for r in records}
                color = '#f1f3f5' if not records else '#c6e9e5' if flags == {True} else '#d6dfeb' if flags == {False} else '#efdab7'
                ax.add_patch(plt.Rectangle((x-.48, y-.46), .96, .92, color=color, lw=0))
                text = '—' if not records else ', '.join('?' if r['selected_catalog_duration_years'] is None
                            else str(r['selected_catalog_duration_years']) for r in records)
                ax.text(x, y, text, ha='center', va='center', fontsize=8)
        ax.set(xlim=(.5, 4.5), ylim=(len(labels)-.5, -.5), xticks=(1, 2, 3, 4),
            yticks=range(len(labels)), yticklabels=labels, xlabel='Original native year',
            title='Selected catalog duration per direction request (years)')
        ax.tick_params(axis='both', length=0)
        ax.legend(handles=[Patch(color=c, label=l) for c, l in (
            ('#c6e9e5', 'Advice in input'), ('#d6dfeb', 'No advice in input'),
            ('#efdab7', 'Mixed attempts'), ('#f1f3f5', 'No attributed request'))],
            loc='upper center', bbox_to_anchor=(.5, -.09), ncol=2, fontsize=8, frameon=False)
        fig.text(.02, .01, '? = unknown duration; comma list = multiple attempts; actor labels are local to each control.',
                 fontsize=7)
        fig.tight_layout(rect=(0, .10, 1, 1))
        for ext in ('png', 'svg'):
            fig.savefig(output/('choice-years.'+ext), dpi=200, metadata={'Date': None} if ext == 'svg' else None)
        plt.close(fig)


def export(args):
    one, two, output = args.one.resolve(), args.two.resolve(), args.output.resolve()
    source = pinned_revision(ROOT)
    if (output.exists() or any(output.is_relative_to(p.parent) or p.is_relative_to(output) for p in (one, two))
            or one == two or one.read_bytes() != two.read_bytes()):
        raise ValueError('two matching distinct reports and fresh separate output required')
    inputs = {str(p): file_sha256(p) for p in (one, two)}
    summary = summarize(json.loads(one.read_text()))
    output.mkdir(parents=True)
    save(output/'summary.json', summary)
    with (output/'direction-attempts.csv').open('x', newline='') as stream:
        columns = ['condition', 'identity', 'seed', 'wire_index', 'year', 'payload_sha256',
            'literal_instruction_present', 'frame_status', 'reply_status', 'selected_topic',
            'selected_catalog_duration_years', 'minimum_displayed_duration_years',
            'selected_is_shortest_displayed', 'unique_actor_attribution',
            'matching_actual_memory_actor_ids', 'displayed_shorter_alternative_to_selected']
        writer = csv.DictWriter(stream, fieldnames=columns); writer.writeheader()
        for row in summary['decisions']:
            writer.writerow({**row, 'matching_actual_memory_actor_ids': json.dumps(row['matching_actual_memory_actor_ids'])})
    render(summary, output)
    if (inputs != {str(p): file_sha256(p) for p in (one, two)} or pinned_revision(ROOT) != source):
        raise ValueError('closed report inputs or reader source changed')
    save(output/'manifest.json', {'schema': SCHEMA+'.export', 'analysis_source_commit': source,
        'inputs': inputs, 'original_report_content_sha256': summary['original_report_content_sha256'],
        'files': {p.name: file_sha256(p) for p in sorted(output.iterdir())},
        'new_model_calls': 0, 'new_code_executions': 0, 'new_native_worlds': 0,
        'visual_review_complete': False})
    print(json.dumps({'worlds': 3, 'direction_attempts': len(summary['decisions']),
                      'summary_file_sha256': file_sha256(output/'summary.json')}))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    for name in ('one', 'two', 'output'):
        p.add_argument('--'+name, type=Path, required=True)
    export(p.parse_args())


if __name__ == '__main__':
    main()
