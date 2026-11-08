"""Finite-study supplement figures; loss scales and timing scopes stay separate."""
from pathlib import Path

from scripts.reports.native_design_tex import METHODS, LABELS, RUNS
from scripts.reports.native_design_supplement import LOSSES


def plot(data, output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.colors import Normalize
    from matplotlib.lines import Line2D
    import numpy as np
    output = Path(output)
    plt.rcParams.update({'font.size':9, 'axes.spines.top':False, 'axes.spines.right':False})
    bounds = {}
    for loss in LOSSES:
        known = [r['cross_scores'][loss] for r in data['trials'] if r['cross_scores'][loss] is not None]
        bounds[loss] = min(known), max(known)
    palettes = [plt.get_cmap(n) for n in ('Blues', 'Greens', 'Purples')]
    for objective in LOSSES[:2]:
        fig, axes = plt.subplots(1, 5, figsize=(14.5,5.8), layout='constrained', sharey=True)
        for method, title, ax in zip(METHODS, LABELS, axes):
            rows = sorted([r for r in data['trials'] if r['arm'] == objective+':'+method],
                          key=lambda r:(r['run'],r['generation']))
            pixels = np.ones((12,3,4)); pixels[:,:,:3] = .94
            for y, row in enumerate(rows):
                for x, loss in enumerate(LOSSES):
                    value = row['cross_scores'][loss]
                    lo, hi = bounds[loss]; level = 0 if value is None else (value-lo)/(hi-lo or 1)
                    if value is not None: pixels[y,x] = palettes[x](.12+.72*level)
                    label = {'generation-failure':'G','technical-failure':'X','loss-unavailable':'M'}.get(row['status'],'?') if value is None else f'{value:.2f}'
                    ax.text(x,y,label,ha='center',va='center',fontsize=8,
                            color='white' if value is not None and level>.6 else '#142536')
            ax.imshow(pixels, aspect='auto', interpolation='none')
            ax.set(xticks=[0,1,2],xticklabels=['T','C','E*'],yticks=range(12),
                   yticklabels=[r['run'].removeprefix('run-')+'/g'+str(r['generation']) for r in rows],
                   title=title)
            ax.set_xticks(np.arange(-.5,3,1),minor=True);ax.set_yticks(np.arange(-.5,12,1),minor=True)
            ax.grid(which='minor',color='white',lw=1); ax.tick_params(which='minor',length=0)
            ax.set_xlabel('Raw cross-score (display rounded)')
        axes[0].set_ylabel('Controller history / proposal generation')
        fig.suptitle(('T' if objective=='throughput' else 'C')+' search: all 60 attempts under common losses')
        fig.supxlabel('G: generation null; X: runtime null; M: measurement null (none is zero). E* is diagnostic.\n'
            'Independent color scales: '+', '.join(f'{label} [{lo:.2f}, {hi:.2f}]'
            for label,(lo,hi) in zip(('T','C','E'),bounds.values()))+'. No cross-loss aggregate/ranking.',fontsize=9)
        for ext in ('png','svg'):fig.savefig(output/('all-cross-scores-'+objective+'.'+ext),dpi=180)
        plt.close(fig)

    colors = ('#17718c','#a34820','#7851a9')
    for objective in LOSSES[:2]:
        fig, axes = plt.subplots(3,2,figsize=(8.2,8.2),layout='constrained',sharey=True)
        axes = axes.ravel()
        for method, title, ax in zip(METHODS, LABELS, axes):
            for run,color in zip(RUNS,colors):
                rows = sorted([r for r in data['trials'] if r['run']==run and r['arm']==objective+':'+method],
                              key=lambda r:r['generation'])
                xs = [0]+[r['cumulative_designer_host_model_seconds'] for r in rows]
                ys = [rows[0]['initial_loss']]+[r['best_including_initial_so_far'] for r in rows]
                ax.step(xs,ys,where='post',color=color)
                for row in rows:
                    x = row['cumulative_designer_host_model_seconds']
                    if x is None: continue  # Unknown timing is not zero.
                    if row['own_loss'] is not None:
                        ax.scatter(x,row['own_loss'],s=20,color=color,zorder=3)
                    else:
                        ax.plot(x,.94-.07*RUNS.index(run),'x',color=color,
                                transform=ax.get_xaxis_transform(),ms=5)
            ax.set(title=title,xlabel='Cumulative designer model-call seconds',ylabel='Assigned loss (lower is better)')
            if method=='random': ax.set_xticks([0])
            ax.grid(alpha=.18)
        axes[-1].axis('off')
        axes[-1].legend(handles=[Line2D([0],[0],color=c,label=r) for r,c in zip(RUNS,colors)],
                        loc='upper left',frameon=False)
        axes[-1].text(0,.64,'Lines include the shared initial observation.\nDots: losses; crosses: axes-relative null markers.\n'
            'All failed authoring steps consume designer time.\nUniform has no designer calls: x=0, not free worlds.\n'
            'Excludes scientist, load, calibration, initial/reference\nand other host time. Not total compute or wall time.\n'
            'Same development seed42; no superiority inference.',va='top',fontsize=8,transform=axes[-1].transAxes)
        fig.suptitle(('T' if objective=='throughput' else 'C')+' search: assigned loss vs one measured cost component')
        for ext in ('png','svg'):fig.savefig(output/('designer-cost-paths-'+objective+'.'+ext),dpi=180)
        plt.close(fig)

    metrics = ('final_active_authors','final_author_resources')
    summaries = [s for s in data['outside_metric_summaries'] if s['years']==2]
    fig,axes = plt.subplots(1,2,figsize=(10,8),layout='constrained',sharey=True)
    for ax,metric,title in zip(axes,metrics,('Final active authors','Final researcher resources (sum)')):
        for y,row in enumerate(summaries):
            values = row['metrics'][metric]['raw']
            for i,v in enumerate(values):
                if v is not None:ax.scatter(v,y+(i-2)*.09,s=18,color=plt.get_cmap('tab10')(i))
            mean = row['metrics'][metric]['mean']
            if mean is not None:ax.scatter(mean,y,s=28,marker='D',facecolors='none',edgecolors='#222')
        ax.set(title=title,yticks=range(len(summaries)),
               yticklabels=[s['label'].replace('reference:','R | ').replace('selected:','') for s in summaries])
        ax.grid(axis='x',alpha=.2)
    axes[0].invert_yaxis()
    axes[0].set_xlim(0,5.5);axes[0].set_xticks(range(6))
    fig.suptitle('Outside diagnostics: five unused two-year seeds (fixed selections)')
    fig.supxlabel('Raw seeds: blue31001, orange31013, green31019, red31033, purple31039.\n'
                  'Hollow diamond: descriptive mean, not CI. Shared labels add no replication.\n'
                  'Final snapshot, not lifetime participation or scientific quality; four-year values stay separate in data.',fontsize=9)
    for ext in ('png','svg'):fig.savefig(output/('outside-activity-resources-2y.'+ext),dpi=180)
    plt.close(fig)
