"""All-reference paired evaluation figures from a CLOSED V2 report.

Individual world-seed differences, available-pair means and technical missingness
are descriptive. Shared policy jobs are never new independent observations.
"""
import argparse
from copy import deepcopy
import hashlib
from pathlib import Path
import re

from scripts.reports.native_design_benchmark import SCHEMA,checked,descriptive,number
from utopia.system.design_patch import digest
from utopia.utils.data_utils import decode_json,write_json_atomic

METHODS=('parameters','code-fixed-graph','code-and-graph','technical-only','random')
TITLES=('Numeric parameters','Code, fixed graph','Code and graph','Technical-only','Uniform numeric')
OBJECTIVES=('throughput','selective')
COLORS=('#176e8b','#b45324','#8053a5','#308559','#9c536b')


def panel_data(report):
    """Rejoin plotted pairs to physical jobs; never execute an audit or a policy."""
    checked(report,SCHEMA+'.report')
    arms=[o+':'+m for o in OBJECTIVES for m in METHODS]
    if set(report['selection']['selected'])!=set(arms):
        raise ValueError('exact declared selected arms required')
    references=list(report['reference_scores'])
    if not references or any(not re.fullmatch(r'[a-z0-9_-]+',name) for name in references):
        raise ValueError('safe exact reference identities required')
    lookup={};conditions={}
    for job in report['evaluation']:
        seed,years=job['seed'],job['years']
        if type(seed) is not int or type(years) is not int or years not in (2,4):
            raise ValueError('declared integer world seed and horizon required')
        if seed not in conditions.setdefault(years,[]):conditions[years].append(seed)
        for label in job['labels']:
            key=label,seed,years
            if key in lookup:raise ValueError('duplicate physical label/condition')
            lookup[key]=job
    if set(conditions)!={2,4} or len(conditions[2])!=5 or len(conditions[4])!=1:
        raise ValueError('five two-year seeds and separate one-seed four-year diagnostic required')
    panels=[]
    for reference in references:
        for years,seeds in sorted(conditions.items()):
            rows=[]
            for arm in arms:
                objective=arm.split(':')[0]
                selected=report['selection']['selected'][arm]['system'] is not None
                if not selected:
                    if report['paired_vs_all_references'][arm]:
                        raise ValueError('unselected policy has evaluated pairs')
                    rows.append({'arm':arm,'objective':objective,'selection_available':False,
                        'pairs':[],'summary':None})
                    continue
                block=report['paired_vs_all_references'][arm][reference][objective][str(years)]
                pairs=block['pairs']
                if [p['seed'] for p in pairs]!=seeds or any(p['years']!=years for p in pairs):
                    raise ValueError('paired seed chronology/horizon differs from physical jobs')
                for pair in pairs:
                    target=lookup[('selected:'+arm,pair['seed'],years)]
                    baseline=lookup[('reference:'+reference,pair['seed'],years)]
                    a,b=number(target['cross_scores'][objective]),number(baseline['cross_scores'][objective])
                    delta=number(a-b) if a is not None and b is not None else None
                    if (pair['target_job_id']!=target['job_id'] or pair['reference_job_id']!=baseline['job_id']
                            or pair['physically_shared'] is not (target['job_id']==baseline['job_id'])
                            or pair['target_loss']!=a or pair['reference_loss']!=b or pair['difference']!=delta):
                        raise ValueError('plot difference does not match exact physical scores/sharing')
                summary=descriptive(pairs,'difference')
                if block['summary']!=summary:raise ValueError('available-pair summary differs')
                rows.append({'arm':arm,'objective':objective,'selection_available':True,
                    'pairs':deepcopy(pairs),'summary':summary})
            panels.append({'reference':reference,'years':years,'seeds':seeds.copy(),'rows':rows,
                'single_seed_diagnostic':years==4})
    result={'schema':SCHEMA+'.evaluation-plot-data',
        'input_report_content_sha256':report['content_sha256'],'classification':report['classification'],
        'panels':panels,'all_references_retained':True,'null_losses_imputed':False,
        'horizons_pooled':False,'shared_jobs_are_independent_observations':False,
        'confidence_intervals_or_significance_claimed':False,
        'scope':'Own declared loss for each selected arm versus EVERY reference. Cross-objective scores remain in the input report. Means condition on available pairs, not full expected performance.'}
    result['content_sha256']=digest(result);return result


def _render(panel,classification,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    with plt.rc_context({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'}):
        fig,axes=plt.subplots(2,1,figsize=(7.2,7.5))
        fig.subplots_adjust(left=.24,right=.95,top=.82,bottom=.17,hspace=.57)
        for ax,objective in zip(axes,OBJECTIVES):
            rows=[r for r in panel['rows'] if r['objective']==objective];labels=[]
            for i,(row,title) in enumerate(zip(rows,TITLES)):
                if not row['selection_available']:
                    labels.append(title+'\n(no selection)');continue
                summary=row['summary'];labels.append(title+f"\n({summary['available']}/{summary['scheduled']} pairs)")
                for j,pair in enumerate(row['pairs']):
                    y=i+(j-(len(row['pairs'])-1)/2)*.12;color=COLORS[j]
                    if pair['difference'] is None:
                        ax.plot(1.025,y,marker='x',color=color,ms=5,linestyle='none',
                            transform=ax.get_yaxis_transform(),clip_on=False)
                    else:
                        ax.scatter(pair['difference'],y,color=color,s=18,
                            marker='s' if pair['physically_shared'] else 'o',zorder=3)
                if summary['mean'] is not None:
                    ax.scatter(summary['mean'],i,marker='D',s=40,edgecolors='#222',
                        facecolors='none',zorder=4)
            ax.axvline(0,color='#888',lw=.8,ls='--');ax.grid(axis='x',alpha=.18)
            ax.set(yticks=range(len(rows)),yticklabels=labels,ylim=(len(rows)-.5,-.5),
                xlabel='Selected loss - reference loss (negative favors selected)',
                title='Search/evaluation objective: '+('throughput (-A)' if objective=='throughput' else 'selective production (4A - Q + 0.1R)'))
            ax.tick_params(axis='y',length=0)
            if not any(r['summary'] is not None and r['summary']['available'] for r in rows):
                ax.text(.5,.5,'No numerical paired differences',transform=ax.transAxes,
                    ha='center',va='center',color='#555')
        horizon='Two-year unused-condition evaluation' if panel['years']==2 else 'Four-year SINGLE-SEED diagnostic'
        fig.suptitle(horizon+'\nReference: '+panel['reference'],fontsize=12,y=.99)
        handles=[Line2D([0],[0],marker='o',color=COLORS[j],ls='none',label='seed '+str(seed))
            for j,seed in enumerate(panel['seeds'])]
        handles += [Line2D([0],[0],marker='D',markerfacecolor='none',color='#222',ls='none',label='Available-pair mean'),
            Line2D([0],[0],marker='s',color='#555',ls='none',label='Same physical job'),
            Line2D([0],[0],marker='x',color='#555',ls='none',label='Missing: outside plot, not a loss')]
        fig.legend(handles=handles,loc='upper center',bbox_to_anchor=(.5,.925),ncol=3,frameon=False,fontsize=8)
        fig.text(.24,.07,'Raw seed differences; small vertical offsets only separate seeds. No confidence interval.\n'
            'Null pairs are not zero; means use available pairs only. Shared jobs add no replication.\n'
            'Two/four-year outcomes at the same seed are not independent samples.',fontsize=8,va='top')
        if classification.startswith('SCRIPTED'):
            fig.text(.53,.5,'SCRIPTED QA - NOT EXPERIMENTAL RESULTS',ha='center',va='center',
                rotation=30,color='#a51f2b',alpha=.23,fontsize=17)
        for suffix in ('png','svg'):
            fig.savefig(output/(panel['reference']+'-'+str(panel['years'])+'y.'+suffix),dpi=180)
        plt.close(fig)


def plot_evaluation(report,output):
    data=panel_data(report);output=Path(output)
    if output.exists():raise ValueError('fresh evaluation figure directory required')
    output.mkdir(parents=True)
    for panel in data['panels']:_render(panel,report['classification'],output)
    write_json_atomic(output/'plot-data.json',data,sort_keys=True,allow_nan=False,indent=2)
    manifest={'schema':SCHEMA+'.evaluation-figures','input_report_content_sha256':report['content_sha256'],
        'plot_data_content_sha256':data['content_sha256'],
        'plot_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())},
        'new_model_calls':0,'new_code_executions':0,'horizons_pooled':False,'null_losses_imputed':False}
    manifest['content_sha256']=digest(manifest)
    write_json_atomic(output/'manifest.json',manifest,sort_keys=True,allow_nan=False,indent=2)
    return manifest


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--report',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(argv);before=a.report.read_bytes()
    result=plot_evaluation(decode_json(before.decode(),strict=True,finite_floats=True),a.output)
    if a.report.read_bytes()!=before:raise ValueError('input report changed during figure rendering')
    print({'content_sha256':result['content_sha256'],'files':len(result['files'])});return 0


if __name__=='__main__':raise SystemExit(main())
