"""Loss paths and cross-scores from one pinned comparison summary; no inference."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path

import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import numpy as np

from scripts.reports.publication_evidence import decode, digest


def path_panel(ax, data, objective, *, paper=False):
    policies = [('loss','#2468a2','Adaptive' if paper else 'Adaptive feedback'),
        ('technical-only','#c15d21','Control' if paper else 'Technical-only / fixed parent')]
    for policy,color,label in policies:
        arm=data['arms'][objective+'-'+policy]
        x=[r['generation'] for r in arm['rows']]
        costs=[r['loss'] if r['status']=='complete' else np.nan for r in arm['rows']]
        best=[v if v is not None else np.nan for v in arm['best_so_far']]
        ax.plot(x,best,color=color,linewidth=2,label=label,
            linestyle='-' if policy=='loss' else '--')
        # Exact ties remain at the exact same coordinates: a hollow square
        # surrounds the filled circle instead of hiding the other arm.
        ax.scatter(x,costs,edgecolors=color,facecolors=color if policy=='loss' else 'none',
            marker='o' if policy=='loss' else 's',s=42 if policy=='loss' else 65,zorder=3)
        for g,r in zip(x,arm['rows']):
            if r['status']!='complete':
                ax.annotate(f'G{g}: null',xy=(g,.03 if policy=='loss' else .13),
                    xycoords=('data','axes fraction'),color=color,fontsize=9,ha='center')
    baseline=data['baseline']['cross_scores'][objective]
    if baseline is not None:
        ax.axhline(baseline,color='#555b66',linestyle='--',linewidth=1,label='Baseline')
    ax.set(title=f'{objective.capitalize()} objective',
        xlabel='Generation' if paper else 'Generation (one candidate / step)',
        ylabel='Loss - lower is better',xticks=[0,1],xlim=(-.2,1.2))
    ax.grid(axis='y',alpha=.18)
    ax.legend(fontsize=8.5 if paper else 8,loc='best')


def render(source, output):
    source, output = Path(source), Path(output)
    saved = source.read_bytes(); data = decode(saved.decode('utf-8'))
    if (data.get('schema') != 'scienceutopia.native-feedback-comparison-audit.v1.summary'
            or data.get('content_sha256') != digest({k:v for k,v in data.items() if k!='content_sha256'})):
        raise ValueError('exact comparison summary schema/content identity required')
    if output.exists():
        raise ValueError('figure directory must be fresh; never overwrite evidence')
    objectives = ('throughput','efficiency')
    plt.rcParams.update({'font.size':10,'axes.spines.top':False,'axes.spines.right':False,
        'svg.fonttype':'none','savefig.facecolor':'white'})
    fig = plt.figure(figsize=(12,9.5), layout='constrained')
    grid = fig.add_gridspec(2,2,height_ratios=[1,1.65])
    rows = [data['baseline']['row'], *data['candidate_rows']]
    labels = ['Shared baseline'] + [r['row_id'].replace('-technical-only', ' / control').replace(
        '-loss',' / feedback').replace(':g',' · G') for r in data['candidate_rows']]
    for col, objective in enumerate(objectives):
        ax = fig.add_subplot(grid[0,col])
        path_panel(ax,data,objective)
        heat = fig.add_subplot(grid[1,col])
        values = np.array([np.nan if r['cross_scores'][objective] is None else r['cross_scores'][objective]
            for r in rows],dtype=float).reshape(-1,1)
        cmap = plt.get_cmap('viridis_r').with_extremes(bad='#e4e7eb')
        image = heat.imshow(np.ma.masked_invalid(values),cmap=cmap,aspect='auto')
        heat.set(yticks=range(len(rows)),yticklabels=labels,xticks=[0],
            xticklabels=[f'All candidates scored by {objective}'],title='Cross-objective evaluation')
        for i,value in enumerate(values[:,0]):
            text = 'null' if np.isnan(value) else f'{value:.3g}'
            heat.text(0,i,text,ha='center',va='center',color='#a51f2b' if np.isnan(value) else '#111111',
                bbox=None if np.isnan(value) else {'facecolor':'white','alpha':.82,'edgecolor':'none','pad':1.5})
        heat.tick_params(axis='y',length=0,labelsize=8)
        fig.colorbar(image,ax=heat,shrink=.75,pad=.02,label='Loss (separate scale per objective)')
    fig.suptitle('Objective-conditioned institution search: a small development comparison',fontsize=14)
    fig.supxlabel('One development seed · two proposals / arm · null = unavailable outcome/score, not a numerical penalty\n'
        f'Source {data["source_commit"][:10]} · descriptive pilot, no method-superiority claim',fontsize=9)
    output.mkdir(parents=True,exist_ok=False)
    for suffix in ('png','svg'):
        fig.savefig(output/f'feedback-comparison.{suffix}',dpi=180)
    plt.close(fig)
    # A separate print-sized path panel avoids shrinking dashboard fonts to
    # illegibility when the paper uses a single-column figure. The complete
    # cross-score matrix is preserved in the dashboard and manuscript table.
    pathfig,axes=plt.subplots(1,2,figsize=(6.5,3.15),layout='constrained')
    for ax,objective in zip(axes,objectives):
        path_panel(ax,data,objective,paper=True)
    pathfig.suptitle('Objective-conditioned institution search',fontsize=11)
    pathfig.supxlabel('One development seed; two candidates per arm; nulls are not numerical penalties.',fontsize=8)
    for suffix in ('png','svg'):
        pathfig.savefig(output/f'search-paths.{suffix}',dpi=240)
    plt.close(pathfig)
    if source.read_bytes()!=saved:
        raise ValueError('summary changed while rendering')
    manifest = {'schema':'scienceutopia.feedback-comparison-figures.v1',
        'input_file_sha256':hashlib.sha256(saved).hexdigest(),
        'input_content_sha256':data['content_sha256'],'source_commit':data['source_commit'],
        'plot_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())},
        'new_model_calls':0,'new_worlds':0,'nulls_imputed':False,'independent_objective_color_scales':True}
    (output/'manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    return manifest


def main(argv=None):
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--summary',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv)
    print(json.dumps(render(args.summary,args.output)))
    return 0


if __name__=='__main__':
    raise SystemExit(main())
