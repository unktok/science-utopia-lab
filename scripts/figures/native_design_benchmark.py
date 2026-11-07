"""Print-sized full-history figures from a closed V2 report; no new inference."""
import argparse
import hashlib
from pathlib import Path

from scripts.reports.native_design_benchmark import SCHEMA,checked
from utopia.system.design_patch import digest
from utopia.utils.data_utils import decode_json,write_json_atomic


def plot_search(report,output):
    checked(report,SCHEMA+'.report')
    output=Path(output)
    if output.exists():raise ValueError('fresh figure directory required')
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
    methods=['parameters','code-fixed-graph','code-and-graph','technical-only','random']
    titles=['Numeric parameters','Code, fixed graph','Code and graph','Technical-only control','Uniform numeric']
    runs=list(report['search_arms']);colors=['#17718c','#a34820','#7851a9']
    output.mkdir(parents=True)
    for objective in ['throughput','selective']:
        fig,axes=plt.subplots(3,2,figsize=(7.2,7.6),layout='constrained',sharex=True,sharey=True)
        axes=axes.ravel()
        reference_values=[v[objective] for v in report['reference_scores'].values() if v[objective] is not None]
        manual=min(reference_values) if reference_values else None
        for ax,method,title in zip(axes,methods,titles):
            arm=objective+':'+method
            for i,run in enumerate(runs):
                body=report['search_arms'][run][arm];rows=body['rows'];color=colors[i%len(colors)]
                ax.step([-1]+[r['generation'] for r in rows],
                    [body['initial_loss']]+[r['best_including_initial_so_far'] for r in rows],
                    where='post',color=color,lw=1.3,alpha=.85)
                for r in rows:
                    if r['own_loss'] is not None:
                        ax.scatter(r['generation'],r['own_loss'],s=20,color=color,zorder=4)
                    else:
                        # Axes-fraction y is a missingness annotation, NEVER a
                        # numeric replacement for a failed scientific loss.
                        ax.plot(r['generation'],.95-.075*i,marker='x',color=color,ms=5,
                            transform=ax.get_xaxis_transform(),linestyle='none')
            if manual is not None:ax.axhline(manual,color='#555',lw=1,ls='--')
            ax.set(title=title,xticks=[-1,0,1,2,3]);ax.grid(alpha=.18)
            ax.set_xlabel('Proposal generation (-1 = initial)')
            ax.set_ylabel('Loss (lower is better)')
        axes[-1].axis('off')
        legend=[Line2D([0],[0],color=colors[i%len(colors)],label=run+' (controller history)') for i,run in enumerate(runs)]
        legend += [Line2D([0],[0],color='#555',ls='--',label='Best declared hand rule (development)'),
            Line2D([0],[0],color='#555',marker='o',ls='none',label='Completed assigned loss'),
            Line2D([0],[0],color='#555',marker='x',ls='none',label='Null trial: marker at top, not a loss')]
        axes[-1].legend(handles=legend,loc='upper left',frameon=False,fontsize=8)
        axes[-1].text(0,.23,'One development world seed42.\nThree separate controller histories.\n'
            'Lines: best including initial;\npoints: all measured candidates.\n'
            'No uncertainty band or superiority claim.',transform=axes[-1].transAxes,fontsize=8,va='top')
        fig.suptitle('Objective: '+('throughput (-A)' if objective=='throughput' else 'selective production (4A - Q + 0.1R)'),fontsize=12)
        if report.get('classification','').startswith('SCRIPTED'):
            fig.text(.5,.5,'SCRIPTED QA - NOT EXPERIMENTAL RESULTS',ha='center',va='center',
                rotation=30,color='#a51f2b',alpha=.23,fontsize=19)
        for suffix in ['png','svg']:fig.savefig(output/(objective+'-paths.'+suffix),dpi=180)
        plt.close(fig)
    manifest={'schema':SCHEMA+'.path-figures','input_report_content_sha256':report['content_sha256'],
        'plot_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())},
        'null_losses_imputed':False,'new_model_calls':0,'new_code_executions':0}
    manifest['content_sha256']=digest(manifest)
    write_json_atomic(output/'manifest.json',manifest,sort_keys=True,allow_nan=False,indent=2)
    return manifest


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('--report',type=Path,required=True);p.add_argument('--output',type=Path,required=True)
    a=p.parse_args(argv);before=a.report.read_bytes()
    r=plot_search(decode_json(before.decode(),strict=True,finite_floats=True),a.output)
    if a.report.read_bytes()!=before:raise ValueError('report changed while plotting')
    print({'content_sha256':r['content_sha256']});return 0


if __name__=='__main__':raise SystemExit(main())
