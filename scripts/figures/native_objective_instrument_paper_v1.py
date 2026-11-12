"""Print-readable loss paths from the complete retained native T/U report."""
import argparse
import json
import math
from pathlib import Path

from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.utils.data_utils import file_sha256

ROOT=Path(__file__).resolve().parents[2]
REFERENCES=('reviewed-all-connected','one-reviewer-all-connected','no-review-all-connected',
            'no-review-reject-all-connected','reviewed-all-disconnected')


def reference_groups(report, objective):
    checked(report)
    if (report['schema']!='scienceutopia.native-objective-instrument-report.v1'
            or tuple(r['label'] for r in report['references'])!=REFERENCES):
        raise ValueError('exact complete native T/U report and reference order required')
    grouped={}
    for i,r in enumerate(report['references'],1):grouped.setdefault(r['scores'][objective],[]).append('R'+str(i))
    return sorted(grouped.items())


def render(report,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    if (len(report['slots'])!=8 or {(s['objective'],s['generation']) for s in report['slots']}
            !={(o,g) for o in ('throughput','content-utility') for g in range(4)}):
        raise ValueError('all eight original proposal slots required')
    with plt.rc_context({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,
                         'svg.hashsalt':'native-objective-instrument-paper-v1'}):
        fig,axes=plt.subplots(1,2,figsize=(6.6,2.8))
        for ax,objective,title in zip(axes,('throughput','content-utility'),('Count objective T','Content objective U')):
            colors={'R1':'#746c93','R2':'#596b84','R3':'#687b86','R4':'#778a6a','R5':'#b77b35'}
            for loss,labels in reference_groups(report,objective):
                color=colors[labels[0]]
                ax.axhline(loss,color=color,lw=1.1,ls='--',label=', '.join(labels),zorder=1)
            rows=sorted((r for r in report['slots'] if r['objective']==objective),key=lambda r:r['generation'])
            best=None;path=[]
            for r in rows:
                if r['loss'] is None:
                    ax.text(r['generation'],.035,'null',transform=ax.get_xaxis_transform(),
                            ha='center',va='bottom',color='#a9444a',fontsize=8.5)
                else:
                    ax.scatter(r['generation'],r['loss'],s=27,color='#087f8c',zorder=4)
                    best=r['loss'] if best is None else min(best,r['loss'])
                path.append(math.nan if best is None else best)
            ax.plot([r['generation'] for r in rows],path,color='#087f8c',lw=1.5,label='Best submitted',zorder=3)
            ax.set(title=title,xlabel='Proposal generation',ylabel='Assigned loss (lower is better)',
                   xticks=[0,1,2,3],xlim=(-.3,3.3))
            ax.margins(y=.16);ax.set_axisbelow(True);ax.grid(axis='y',color='#eceff1',lw=.7)
            ax.legend(fontsize=8,loc='center right',framealpha=.95,handlelength=1.8)
        fig.tight_layout(pad=.5,w_pad=1.1)
        for ext in ('png','svg'):
            fig.savefig(out/('loss-paths.'+ext),dpi=240,metadata={'Date':None} if ext=='svg' else None)
        plt.close(fig)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--report',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);a=p.parse_args();source=pinned_revision(ROOT)
    if a.output.exists():raise ValueError('fresh paper-figure output required')
    before=file_sha256(a.report);r=checked(json.loads(a.report.read_text()));a.output.mkdir(parents=True)
    render(r,a.output)
    if file_sha256(a.report)!=before or pinned_revision(ROOT)!=source:raise ValueError('source or original report changed')
    save(a.output/'manifest.json',{'schema':'scienceutopia.native-objective-instrument-paper-figures.v1',
        'source_commit':source,'report_file_sha256':before,'report_content_sha256':r['content_sha256'],
        'files':{p.name:file_sha256(p) for p in sorted(a.output.iterdir())},
        'new_model_calls':0,'new_code_executions':0,'coordinates_or_losses_changed':False})


if __name__=='__main__':main()
