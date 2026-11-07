"""Compact, hash-bound strong-control result and scientific figure; no inference."""
import argparse
from copy import deepcopy
from datetime import datetime
import hashlib
import json
from pathlib import Path

from utopia.system.design_patch import digest
from utopia.utils.data_utils import decode_json

SCHEMA='scienceutopia.native-benchmark-controls.v2.summary'


def summarize(audit):
    if (audit.get('schema')!='scienceutopia.native-benchmark-controls.v2.audit'
            or audit.get('content_sha256')!=digest({k:v for k,v in audit.items() if k!='content_sha256'})):
        raise ValueError('exact source-bound control audit schema/content required')
    rows=[]
    for row in audit['rows']:
        proof=audit['proofs'][row['name']]
        rows.append({**deepcopy(row),'metrics':deepcopy(proof.get('measurement',{}).get('metrics')),
            'costs':{k:proof.get(section,{}).get(field) for k,section,field in [
                ('scientist_responses','response_proof','researcher_responses'),
                ('wire_requests','response_proof','wire_requests'),
                ('code_executions','code_proof','recorded_executions')]}})
    costs={k:{'known_sum':sum(r['costs'][k] for r in rows if r['costs'][k] is not None),
        'unknown_rows':[r['name'] for r in rows if r['costs'][k] is None]} for k in rows[0]['costs']}
    writer=audit['writer'];elapsed=(datetime.fromisoformat(writer['ended']['ended_utc'])-
        datetime.fromisoformat(writer['started']['started_utc'])).total_seconds()
    result={'schema':SCHEMA,'source_commit':audit['source_commit'],'plan_sha256':audit['plan_sha256'],
        'input_audit_content_sha256':audit['content_sha256'],'rows':rows,'best':deepcopy(audit['best']),
        'physical_world_slots':len(rows),'completed':sum(r['status']=='complete' for r in rows),
        'costs':costs,'designer_responses':0,'wall_seconds':elapsed,
        'scope':'Developer-authored controls, one development seed42, two years; no automatic invention, method superiority or real scientific-quality claim.',
        'new_model_calls':0,'new_worlds':0,'nulls_imputed':False}
    result['content_sha256']=digest(result)
    return result


def plot(summary,output,*,print_layout=False):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    if (summary.get('schema')!=SCHEMA or summary['content_sha256']!=digest(
            {k:v for k,v in summary.items() if k!='content_sha256'})):
        raise ValueError('control summary identity differs')
    output=Path(output)
    if output.exists():raise ValueError('fresh figure directory required')
    labels={'legacy':'Original legacy institution','open-seed':'Editable open seed',
        'open-rank-rate':'Rank / rate rule','open-accept-all':'Accept all',
        'open-reject-all':'Reject all','open-score-3':'Review score >= 3','open-score-4':'Review score >= 4',
        'open-no-review-accept-all':'No review + accept all'}
    titles={'throughput':'Throughput: -A','efficiency':'Reviewed utility: -Q + 0.5R',
        'selective':'Selective production: 4A - Q + 0.1R'}
    if print_layout:
        titles={'throughput':'Throughput\n-A','efficiency':'Reviewed utility\n-Q + 0.5R',
            'selective':'Selective production\n4A - Q + 0.1R'}
    plt.rcParams.update({'font.size':9,'axes.spines.top':False,'axes.spines.right':False,'svg.fonttype':'none'})
    fig,axes=plt.subplots(1,3,figsize=(7.2,3.8) if print_layout else (12,5.2),layout='constrained',sharey=True)
    for ax,key in zip(axes,titles):
        values=[r['cross_scores'][key] for r in summary['rows']]
        known=[v for v in values if v is not None]
        span=max(max(known,default=1)-min(known,default=0),1)
        for y,r in enumerate(summary['rows']):
            value=r['cross_scores'][key]
            if value is None:
                ax.text(0,y,'null',va='center',color='#a51f2b');continue
            color='#7b8794' if y<2 else '#8057a6' if 'no-review' in r['name'] else '#26739b'
            best=value==summary['best'][key]['loss']
            ax.barh(y,value,color=color,alpha=.85,height=.62,
                edgecolor='#111' if best else 'none',linewidth=1.3,hatch='//' if best else None)
            inside=print_layout and value<0
            ax.text(value+(.04*span if inside else .025*span if value>=0 else -.025*span),
                y,f'{value:.3f}',va='center',ha='left' if inside or value>=0 else 'right',fontsize=8,
                bbox={'facecolor':'white','alpha':.9,'edgecolor':'none','pad':.7} if inside else None)
        ax.axvline(0,color='#68737d',linewidth=.7);ax.grid(axis='x',alpha=.15)
        ax.set(title=titles[key],xlabel='Loss (lower is better)',yticks=range(len(summary['rows'])))
        ax.set_xlim(min(min(known,default=0),0)-span*.23,max(max(known,default=1),0)+span*.25)
    axes[0].set_yticklabels([labels[r['name']] for r in summary['rows']]);axes[0].invert_yaxis()
    if not print_layout:
        fig.suptitle('Strong rule baselines in the original researcher world',fontsize=14)
        fig.supxlabel('Eight developer controls, one development seed, two years. Hatched bars: all exact minimum ties.\n'
            'Same trajectories cross-scored; independent axis scales. Not an optimizer comparison or scientific-quality measure.',fontsize=9)
    output.mkdir(parents=True)
    for suffix in ['png','svg']:fig.savefig(output/('strong-controls.'+suffix),dpi=180)
    plt.close(fig)
    manifest={'schema':'scienceutopia.native-control-figures.v2','input_content_sha256':summary['content_sha256'],
        'plot_source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'files':{p.name:hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(output.iterdir())},
        'new_model_calls':0,'new_worlds':0,'nulls_imputed':False}
    if print_layout:manifest['layout']='print-sized-7.2-inch-font9'
    (output/'manifest.json').write_text(json.dumps(manifest,sort_keys=True,indent=2)+'\n')


def main(argv=None):
    p=argparse.ArgumentParser(description=__doc__)
    inputs=p.add_mutually_exclusive_group(required=True)
    inputs.add_argument('--audit',type=Path);inputs.add_argument('--summary',type=Path)
    p.add_argument('--output',type=Path,required=True)
    p.add_argument('--figures',type=Path);p.add_argument('--print-layout',action='store_true');a=p.parse_args(argv)
    if a.output.exists():p.error('fresh compact summary required')
    source=a.audit if a.audit is not None else a.summary
    saved=source.read_bytes();value=decode_json(saved.decode(),strict=True,finite_floats=True)
    summary=summarize(value) if a.audit is not None else value
    if (summary.get('schema')!=SCHEMA or summary.get('content_sha256')!=digest(
            {k:v for k,v in summary.items() if k!='content_sha256'})):
        raise ValueError('exact recorded summary identity required; no raw re-audit claimed')
    if a.figures:plot(summary,a.figures,print_layout=a.print_layout)
    if source.read_bytes()!=saved:raise ValueError('control report input changed while reporting')
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(summary,ensure_ascii=False,sort_keys=True,indent=2)+'\n')
    print({'content_sha256':summary['content_sha256'],'completed':summary['completed']});return 0


if __name__=='__main__':raise SystemExit(main())
