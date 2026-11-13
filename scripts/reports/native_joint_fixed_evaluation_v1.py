"""All sixteen policy labels, every seed/null/shared job and eight contrasts."""
import argparse
from pathlib import Path

from scripts.reports.native_objective_fixed_evaluation_v1 import export as original_export


def render(report,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import TwoSlopeNorm
    import numpy as np
    labels,seeds=report['labels'],report['seeds']
    by={(r['label'],r['seed']):r for r in report['logical_rows']}
    key=['R'+str(i+1)+' = '+label.removeprefix('reference:') for i,label in enumerate(labels[:8])]
    key+=['S'+str(i+1)+' = '+label.removeprefix('selected:') for i,label in enumerate(labels[8:])]
    codes=['R'+str(i+1) for i in range(8)]+['S'+str(i+1) for i in range(8)]
    dataset=report.get('data_identity',{}).get('dataset','')
    software_qa=dataset=='explicit-QA-fixture' or str(dataset).startswith('SCRIPTED')
    def mark(fig):
        if software_qa:
            fig.text(.5,.5,'SCRIPTED SOFTWARE QA',ha='center',va='center',rotation=25,
                fontsize=30,color='#a9444a',alpha=.16,zorder=100)
    with plt.rc_context({'font.size':8,'svg.hashsalt':report['schema']}):
        fig,axes=plt.subplots(1,2,figsize=(11.5,10.4))
        for ax,objective,title in zip(axes,report['score_order'],['Count loss T','Content loss U']):
            values=np.array([[np.nan if by[label,seed]['scores'][objective] is None else by[label,seed]['scores'][objective]
                for seed in seeds] for label in labels])
            cmap=plt.get_cmap('viridis_r').with_extremes(bad='#eeeeee')
            chart=ax.imshow(np.ma.masked_invalid(values),aspect='auto',cmap=cmap)
            for i,label in enumerate(labels):
                for j,seed in enumerate(seeds):
                    row=by[label,seed];value=row['scores'][objective]
                    text='unavailable' if value is None else f'{value:.7g}\nP'+row['physical_job'].removeprefix('evaluation-')
                    color='#a9444a' if value is None else ('white' if chart.norm(value)>.58 else '#18242d')
                    ax.text(j,i,text,ha='center',va='center',fontsize=7,color=color)
            ax.set(title=title,xticks=range(len(seeds)),xticklabels=[str(s) for s in seeds],
                yticks=range(len(labels)),yticklabels=codes,xlabel='Unused world seed')
            fig.colorbar(chart,ax=ax,fraction=.045,pad=.025,label='Fixed loss; lower is better')
        fig.suptitle('Frozen institutional policies: every logical label and physical sharing',fontsize=11)
        fig.tight_layout(rect=(0,.25,1,.95))
        for x,rows in ((.05,key[:8]),(.53,key[8:])):
            fig.text(x,.055,'\n'.join(rows),fontsize=6.8,va='bottom',linespacing=1.55)
        fig.text(.05,.018,'Matching P IDs share one physical world, not independent samples. '
            'All losses and unavailable pairs are retained; no reselection.',fontsize=7)
        mark(fig)
        for ext in ('png','svg'):
            fig.savefig(output/('joint-policy-seed-scores.'+ext),dpi=200,metadata={'Date':None} if ext=='svg' else None)
        plt.close(fig)
        definitions=report['contrast_definitions']
        by_pair={(r['id'],r['seed']):r for r in report['fixed_policy_contrasts']}
        fig,axes=plt.subplots(1,2,figsize=(11.5,7.8))
        for ax,objective,title in zip(axes,report['score_order'],['Difference in T','Difference in U']):
            values=np.array([[np.nan if by_pair[d['id'],s]['differences'][objective] is None
                else by_pair[d['id'],s]['differences'][objective] for s in seeds] for d in definitions])
            known=values[np.isfinite(values)];bound=max(1e-12,float(np.max(np.abs(known)))) if len(known) else 1.
            cmap=plt.get_cmap('RdBu_r').with_extremes(bad='#eeeeee')
            chart=ax.imshow(np.ma.masked_invalid(values),aspect='auto',cmap=cmap,
                norm=TwoSlopeNorm(vmin=-bound,vcenter=0,vmax=bound))
            for i,d in enumerate(definitions):
                for j,seed in enumerate(seeds):
                    row=by_pair[d['id'],seed];value=row['differences'][objective]
                    text='unavailable' if value is None else f'{value:.7g}'+('\nshared P' if row['same_physical_job'] else '')
                    ax.text(j,i,text,ha='center',va='center',fontsize=7,
                        color='#a9444a' if value is None else 'white' if abs(value)/bound>.6 else '#18242d')
            ax.set(title=title,xticks=range(len(seeds)),xticklabels=[str(s) for s in seeds],
                yticks=range(len(definitions)),yticklabels=['C'+str(i+1) for i in range(len(definitions))],xlabel='Unused world seed')
            fig.colorbar(chart,ax=ax,fraction=.045,pad=.025,label='Left minus right loss; negative favors left')
        fig.suptitle('Eight predeclared fixed-policy contrasts; no optimizer-superiority inference',fontsize=11)
        fig.tight_layout(rect=(0,.31,1,.94))
        keys=['C'+str(i+1)+' = '+d['id'] for i,d in enumerate(definitions)]
        for x,rows in ((.05,keys[:4]),(.53,keys[4:])):
            fig.text(x,.09,'\n'.join(rows),fontsize=7,va='bottom',linespacing=1.6)
        fig.text(.05,.025,'Each contrast is left minus right as declared in the protocol. '
            'No missing-value imputation, seed expansion or independent-history claim.',fontsize=7)
        mark(fig)
        for ext in ('png','svg'):
            fig.savefig(output/('joint-fixed-contrasts.'+ext),dpi=200,metadata={'Date':None} if ext=='svg' else None)
        plt.close(fig)


def export(args):return original_export(args,study='joint-v1',renderer=render)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('run','audit-one','audit-two','output'):parser.add_argument('--'+key,type=Path,required=True)
    export(parser.parse_args())


if __name__=='__main__':main()
