"""Plot a conditional readout diagnostic, not rerouting or confidence intervals."""
import argparse
import json
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256,write_json_atomic


def selected_rows(report,audit):
    checked(report);checked(audit)
    if (report['schema']!='scienceutopia.fixed-record-panel-sensitivity.v1'
            or report['input_full_audit_content_sha256']!=audit['content_sha256']
            or report['plan_sha256']!=audit['plan_sha256'] or report['source_commit']!=audit['source_commit']):
        raise ValueError('matching original-audit panel diagnostic required')
    labels=('reference:reviewed-accept-all','selected:efficiency:parameters')
    worlds={r['identity']:r for r in report['worlds']};rows=[]
    for seed in (51001,51011,51017):
        for label in labels:
            matches=[r for r in audit['logical_evaluation'] if (r['label'],r['seed'])==(label,seed)]
            if len(matches)!=1:raise ValueError('one exact label/seed physical join required')
            world=worlds.get(matches[0]['physical_job'])
            if world is None or world['seed']!=seed or world['role']!='selection-fixed-evaluation':
                raise ValueError('paired readout lacks its exact completed physical world')
            low,high=world['conditional_one_review_readout_Q_range']
            if not low<=world['original_Q']<=high:raise ValueError('full-panel Q outside subset envelope')
            rows.append({'label':label,'seed':seed,'world':world})
    return rows


def render(report,audit,output):
    rows=selected_rows(report,audit)
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.lines import Line2D
    colors={'reference:reviewed-accept-all':'#177d88','selected:efficiency:parameters':'#a96924'}
    with plt.rc_context({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,
            'svg.hashsalt':'fixed-panel-readout-v1'}):
        fig,ax=plt.subplots(figsize=(7.8,3.8))
        for i,row in enumerate(rows):
            w=row['world'];lo,hi=w['conditional_one_review_readout_Q_range'];color=colors[row['label']]
            ax.plot([lo,hi],[i,i],lw=3,color=color,alpha=.45,solid_capstyle='butt')
            ax.scatter([w['original_Q']],[i],s=30,color=color,zorder=3)
            ax.text(1.02,i,f'A={w["accepted_decisions"]}, R={w["actual_review_records"]}',
                transform=ax.get_yaxis_transform(),va='center',fontsize=8,color='#444444')
        labels=[('Reviewed accept-all' if r['label'].startswith('reference:') else 'E / numerical')+
            '  s'+str(r['seed']) for r in rows]
        ax.set(yticks=range(6),yticklabels=labels,ylim=(5.55,-.6),xlabel='Q readout (original score units)')
        for y in (1.5,3.5):ax.axhline(y,color='#eeeeee',lw=.7)
        ax.grid(axis='x',color='#eeeeee',lw=.6);ax.set_axisbelow(True)
        handles=[Line2D([],[],color='#444444',marker='o',ls='',ms=4,label='Actual full-panel Q'),
            Line2D([],[],color='#999999',lw=3,label='One-score readout envelope (hindsight)')]
        fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,.095),ncol=2,frameon=False,fontsize=8)
        fig.suptitle('Fixed-record panel readout sensitivity',fontsize=11,y=.98)
        fig.text(.5,.915,'Within each world: recorded accepted papers and actual review work stay fixed.',ha='center',fontsize=8)
        fig.text(.5,.035,'Not confidence intervals, avoided review costs, new policy effects, or independent scientific quality.',ha='center',fontsize=7.5,color='#555555')
        fig.subplots_adjust(left=.285,right=.83,top=.84,bottom=.28)
        for ext in ('png','svg'):
            fig.savefig(output/('fixed-panel-readout.'+ext),dpi=240,
                metadata={'Date':None} if ext=='svg' else None)
        plt.close(fig)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('report','audit','output'):parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args()
    if args.output.exists():raise ValueError('fresh diagnostic figure destination required')
    originals={p:file_sha256(p) for p in (args.report,args.audit)}
    report=json.loads(args.report.read_text());audit=json.loads(args.audit.read_text())
    args.output.mkdir(parents=True);render(report,audit,args.output)
    if any(file_sha256(p)!=sha for p,sha in originals.items()):raise ValueError('diagnostic inputs changed')
    result={'schema':'scienceutopia.fixed-record-panel-figures.v1','input_report_content_sha256':report['content_sha256'],
        'input_audit_content_sha256':audit['content_sha256'],'projection_source_sha256':file_sha256(Path(__file__)),
        'files':{p.name:file_sha256(p) for p in args.output.iterdir()},'new_model_calls':0,'new_native_worlds':0}
    write_json_atomic(args.output/'manifest.json',{**result,'content_sha256':digest(result)},sort_keys=True,allow_nan=False)


if __name__=='__main__':main()
