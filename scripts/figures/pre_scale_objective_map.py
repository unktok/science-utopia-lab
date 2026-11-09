"""Print-sized rendering of the retained observed-profile coefficient map.

Numerical grid unchanged; no new search, observations or original-source audit.
"""
import argparse
import json
from pathlib import Path

from utopia.optimization.native_numeric_designer import checked
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256,write_json_atomic


def render(source,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import BoundaryNorm,ListedColormap
    from matplotlib.patches import Patch
    import numpy as np
    data=checked(json.loads(Path(source).read_text()));g=data['coefficient_grid']
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    colors=['#e8b55b','#45a8b0','#5356a8','#8b8b8b','#cf74aa']
    with plt.rc_context({'font.size':8.5,'axes.titlesize':9,'axes.spines.top':False,
        'axes.spines.right':False,'svg.hashsalt':'pre-scale-observed-map-print-v1'}):
        fig,axes=plt.subplots(1,2,figsize=(6.7,3.45))
        for ax,scope,title in zip(axes,('references','all_observations'),
            ('Nine references','References + 64 complete candidates')):
            ax.pcolormesh(g['alphas'],g['betas'],g['panels'][scope],shading='nearest',
                cmap=ListedColormap(colors),norm=BoundaryNorm(np.arange(-.5,5.5),5),rasterized=True)
            for label,x,y in (('C',4.,.1),('E*',0.,.5),('U*',3.25,.05)):
                ax.scatter([x],[y],s=18,facecolor='white',edgecolor='#202020',linewidth=.8,zorder=4)
                ax.annotate(label,(x,y),xytext=(4,5),textcoords='offset points',fontsize=8)
            ax.set(title=title,xlabel=r'$\alpha$: acceptance coefficient',
                ylabel=r'$\beta$: review-cost coefficient',xlim=(g['alphas'][0],g['alphas'][-1]),
                ylim=(g['betas'][0],g['betas'][-1]))
        labels=[(0,'No publication / no review'),(1,'Publication without review'),
                (2,'Review-backed publication'),(4,'Mixed-family tie')]
        fig.legend(handles=[Patch(facecolor=colors[i],label=label) for i,label in labels],
            loc='lower center',ncol=2,frameon=False,bbox_to_anchor=(.5,.005),fontsize=8)
        fig.subplots_adjust(left=.085,right=.99,top=.9,bottom=.28,wspace=.28)
        for ext in ('png','svg'):
            fig.savefig(output/('observed-objective-map-print.'+ext),dpi=240,
                metadata={'Date':None} if ext=='svg' else None)
        plt.close(fig)
    value={'schema':'scienceutopia.observed-objective-map-print.v1','input_file_sha256':file_sha256(source),
        'analysis_content_sha256':data['content_sha256'],'coefficient_grid_sha256':digest(g),
        'new_model_calls':0,'new_native_worlds':0,'numerical_grid_changed':False,
        'files':{p.name:file_sha256(p) for p in sorted(output.glob('observed-objective-map-print.*'))}}
    write_json_atomic(output/'manifest.json',{**value,'content_sha256':digest(value)},sort_keys=True,allow_nan=False)
    return value


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--analysis',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    print(json.dumps(render(args.analysis,args.output)))


if __name__=='__main__':main()
