"""Exact observed T/P trade-offs after closure; never optimize a new objective."""
import argparse
import csv
from fractions import Fraction
import json
from pathlib import Path

from scripts.reports.native_preference_regions_v1 import exact, regions
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.utils.data_utils import file_sha256

ROOT = Path(__file__).resolve().parents[2]
SCHEMA = 'scienceutopia.native-capacity-observed-preference-geometry.v1'
OBJECTIVES = ['throughput', 'founder-activity']


def summarize(report):
    checked(report)
    if (report['schema'] != 'scienceutopia.native-capacity-objective-report.v1'
            or report['score_order'] != OBJECTIVES
            or report['interpretation']['held_out_evaluation']
            or report['interpretation']['new_model_calls']
            or report['interpretation']['new_code_executions']):
        raise ValueError('closed original T/P development report required')
    worlds = report['physical_worlds']
    if (not worlds or len({w['identity'] for w in worlds}) != len(worlds)
            or len({w['seed'] for w in worlds}) != 1):
        raise ValueError('distinct actual worlds at one development seed required')
    grouped = {}; failed = []
    for w in worlds:
        if set(w['scores']) != set(OBJECTIVES):
            raise ValueError('literal T/P score pair required')
        if w['status'] != 'complete':
            if any(v is not None for v in w['scores'].values()):
                raise ValueError('technical null must not receive an imputed loss')
            failed.append(w['identity']); continue
        t, p = (exact(w['scores'][name]) for name in OBJECTIVES)
        if any(v > 0 or v.denominator != 1 for v in (t, p)):
            raise ValueError('original negative integer counts required')
        grouped.setdefault((t, p), []).append({'identity': w['identity'],
            'role': w['role'], 'system_sha256': w['system_sha256']})
    pairs = sorted(grouped)
    if not pairs:
        raise ValueError('no completed observation; no invented preference geometry')
    curves = []
    for i, (t, p) in enumerate(pairs):
        dominated = any(a <= t and b <= p and (a < t or b < p) for a, b in pairs)
        curves.append({'index': i, 'label': 'G'+str(i+1), 'T': str(t), 'P': str(p),
            'loss_slope': str(t-p), 'loss_intercept': str(p),
            'observed_pareto_nondominated': not dominated,
            'physical_worlds': sorted(grouped[t,p], key=lambda w:w['identity'])})
    geometry = regions([(t-p,p) for t,p in pairs], Fraction(0), Fraction(1))
    for boundary in geometry['boundaries']:
        boundary['weight_T'] = boundary.pop('center')
    supported = {i for row in [*geometry['open_intervals'], *geometry['boundaries']]
                 for i in row['winning_curve_indices']}
    for curve in curves:
        curve['minimizes_some_observed_linear_mixture'] = curve['index'] in supported
    null_slots = [{'objective': s['objective'], 'generation': s['generation'],
        'status': s['status'], 'physical_job': s['physical_job']}
        for s in report['slots'] if s['status'] != 'complete']
    return {'schema': SCHEMA, 'original_report_content_sha256': report['content_sha256'],
        'scientific_source_commit': report['source_commit'], 'plan_sha256': report['plan_sha256'],
        'audit_content_sha256': report['audit_sha256'], 'development_seed': worlds[0]['seed'],
        'family': {'formula': 'L_w = w T + (1-w) P', 'weight_T_interval': ['0','1'],
            'actual_optimized_endpoints': {'0':'founder-activity','1':'throughput'},
            'raw_units_no_normalization': True, 'retrospective_observed_archive_only': True,
            'new_objective_adopted': False, 'interior_objectives_optimized': False},
        'curves': curves, 'geometry': geometry,
        'failed_world_ids': sorted(failed), 'unavailable_own_slots': null_slots,
        'physical_attempts': len(worlds), 'complete_observed_worlds': len(worlds)-len(failed),
        'scope': 'Exact lower envelope and Pareto comparisons of literal recorded T/P counts. '
            'Not global or expected policy optima, a new optimization, a causal mechanism test, '
            'scientific truth or a change to either actual selected institution. Raw units are '
            'explicit: weights are not invariant to rescaling an objective. Each score point may '
            'contain different programs, developer controls or repeated executions; none becomes '
            'an independent optimizer replication or a program-equivalence class. The original '
            'four own slots and all nulls remain in the source report. Pareto nondominance does '
            'not guarantee optimality under any linear scalarization. A policy reoptimized under '
            'an interior weight could produce different records. No hidden adoption veto is added.',
        'candidate_reselection': False, 'new_model_calls': 0, 'new_code_executions': 0,
        'new_native_worlds': 0, 'publication_ready': False}


def render(summary, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    with plt.rc_context({'font.size': 8, 'axes.spines.top': False,
                         'axes.spines.right': False, 'svg.hashsalt': SCHEMA}):
        fig, axes = plt.subplots(1, 2, figsize=(6.6, 4.3))
        colors = plt.get_cmap('tab10')
        for curve in summary['curves']:
            i = curve['index']; color = colors(i % 10)
            t,p = float(Fraction(curve['T'])),float(Fraction(curve['P']))
            n = len(curve['physical_worlds'])
            axes[0].plot([0,1],[p,t],color=color,lw=1.3,
                label=f'{curve["label"]}: T={curve["T"]}, P={curve["P"]} (n={n})')
            axes[1].scatter([t],[p],color=[color],s=38,
                marker='D' if curve['observed_pareto_nondominated'] else 'o')
            axes[1].annotate(curve['label'],(t,p),xytext=(5,5),textcoords='offset points',fontsize=7)
        for span in summary['geometry']['open_intervals']:
            left,right = float(Fraction(span['left'])),float(Fraction(span['right']))
            curve = summary['curves'][span['winning_curve_indices'][0]]
            a,b = float(Fraction(curve['loss_slope'])),float(Fraction(curve['loss_intercept']))
            axes[0].plot([left,right],[a*left+b,a*right+b],color='black',lw=2.5,zorder=3)
        for boundary in summary['geometry']['boundaries'][1:-1]:
            x = float(Fraction(boundary['weight_T']))
            axes[0].axvline(x,color='#9ca3af',ls=':',lw=.8)
        axes[0].set(xlim=(0,1),xlabel='Hypothetical weight on T (raw units)',
            ylabel='Conditional recorded loss',title='Observed lower envelope (black)')
        axes[1].set(xlabel='T: negative publication count',ylabel='P: negative founder-boundary count',
            title='Observed score points (lower is better)')
        axes[1].margins(.15)
        for ax in axes:ax.grid(alpha=.18);ax.set_axisbelow(True)
        handles,labels = axes[0].get_legend_handles_labels()
        fig.legend(handles,labels,loc='lower center',bbox_to_anchor=(.5,.095),
            ncol=3,fontsize=6.5,frameon=False)
        fig.text(.02,.04,'Diamonds: observed Pareto points; score ties are grouped, not equivalent programs.',fontsize=7)
        fig.text(.02,.01,f'{summary["complete_observed_worlds"]} completed worlds; '
            f'{len(summary["unavailable_own_slots"])} unavailable own slots. No new optimization or reselection.',fontsize=7)
        fig.tight_layout(rect=(0,.26,1,1))
        for ext in ('png','svg'):
            fig.savefig(output/('observed-tp-geometry.'+ext),dpi=220,
                metadata={'Date':None} if ext=='svg' else None)
        plt.close(fig)


def export(args):
    source = pinned_revision(ROOT); path,output = args.report.resolve(),args.output.resolve()
    if output.exists() or output.is_relative_to(path.parent) or path.is_relative_to(output):
        raise ValueError('fresh separate output required')
    before = file_sha256(path); summary = summarize(json.loads(path.read_text()))
    output.mkdir(parents=True);save(output/'summary.json',summary);render(summary,output)
    with (output/'score-groups.csv').open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['group','T','P','pareto','linear_supported','identity','role','system_sha256'])
        writer.writeheader()
        for c in summary['curves']:
            for w in c['physical_worlds']:
                writer.writerow({'group':c['label'],'T':c['T'],'P':c['P'],
                    'pareto':c['observed_pareto_nondominated'],
                    'linear_supported':c['minimizes_some_observed_linear_mixture'],**w})
    if file_sha256(path)!=before or pinned_revision(ROOT)!=source:
        raise ValueError('original report or reader source changed')
    save(output/'manifest.json',{'schema':SCHEMA+'.export','analysis_source_commit':source,
        'report_file_sha256':before,'original_report_content_sha256':summary['original_report_content_sha256'],
        'files':{p.name:file_sha256(p) for p in sorted(output.iterdir())},
        'new_model_calls':0,'new_native_worlds':0,'candidate_reselection':False})
    print(json.dumps({'complete_observed_worlds':summary['complete_observed_worlds'],
        'score_groups':len(summary['curves']),'new_optimization':False}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--report',type=Path,required=True);parser.add_argument('--output',type=Path,required=True)
    export(parser.parse_args())


if __name__=='__main__':main()
