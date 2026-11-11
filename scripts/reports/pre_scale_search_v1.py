"""All-slot search paths and shared-policy evaluation from a CLOSED O/E audit.

Read-only descriptive reporting, not fresh simulation, candidate selection or
an independent original-source audit. Failed scores remain explicit nulls.
"""
import argparse
from collections import Counter
from copy import deepcopy
import json
from pathlib import Path
import statistics

from scripts.reports.native_design_benchmark import descriptive,number
from utopia.optimization.native_numeric_designer import checked
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256,write_json_atomic

OBJECTIVES=('throughput','efficiency')
METHODS=('parameters','code-fixed-graph','code-and-graph','random')


def development_bindings(rows,worlds,*,seed=41001):
    """Join exact original audit arrival order, never match repeated specs by guess."""
    forwards=iter(w for w in worlds if w['role']!='selection-fixed-evaluation');result={}
    for row in rows:
        if row['status']=='generation-failure':
            if row['system'] is not None or row['forward_complete']:raise ValueError('unsubmitted slot has a forward/system')
            result[row['row_id']]=None;continue
        world=next(forwards,None)
        role='developer-reference' if row['arm'] is None else 'search:'+row['arm']
        if (world is None or world['role']!=role or world['seed']!=seed
                or world['status']!=row['status'] or world['system']!=row['system']
                or world['scores']!=row['cross_scores']):
            raise ValueError('development row differs from ordered original physical world')
        if row['arm'] is None and world['identity']!='reference-'+row['row_id'].removeprefix('reference:'):
            raise ValueError('reference identity differs from ordered original physical world')
        result[row['row_id']]=world['identity']
    if next(forwards,None) is not None:raise ValueError('unaccounted development physical world')
    return result


def summarize(audit,*,plan=None):
    checked(audit)
    native=audit['schema']=='scienceutopia.native-institution-loop-audit.v1'
    if native:
        if plan is None:raise ValueError('native loop requires its exact frozen plan')
        checked(plan)
        if (plan['schema']!='scienceutopia.native-institution-loop.v1.plan'
                or plan['source_commit']!=audit['source_commit'] or plan['content_sha256']!=audit['plan_sha256']
                or audit.get('closure',{}).get('terminal',{}).get('status')!='closed'
                or audit.get('source_proof',{}).get('status')!='verified-exact-source-closure'
                or audit.get('new_model_calls')!=0 or audit.get('new_code_executions')!=0):
            raise ValueError('matching closed original-source native loop audit required')
        methods=tuple(plan['methods']);seed=61001;seeds=plan['evaluation']['seeds']
        references=plan['evaluation']['reference_labels'];row_count=20
        if (methods!=('parameters','code-fixed-graph','code-and-graph') or seeds!=[62001,62011,62017]
                or len(plan['reference_order'])!=8 or len(plan['schedule'])!=12):
            raise ValueError('native loop frozen finite design differs')
    elif audit['schema']=='scienceutopia.pre-scale-search-audit.v1' and plan is None:
        methods=METHODS;seed=41001;seeds=[51001,51011,51017];row_count=22
        references=('open-seed','reviewed-accept-all','no-review-accept-all','no-review-reject-all')
    else:
        raise ValueError('closed original-source search/evaluation audit required')
    selection=audit['selection'];rows=selection['all_rows']
    initial=next(r for r in rows if r['row_id']=='reference:open-seed')
    if len(rows)!=row_count or len({r['row_id'] for r in rows})!=row_count:
        raise ValueError('all declared reference and candidate rows required')
    expected={o+':'+m for o in OBJECTIVES for m in methods}
    if set(selection['selected'])!=expected:raise ValueError('every objective/method selection required')
    physical_bindings=development_bindings(rows,audit['worlds'],seed=seed)
    paths={};slots=[]
    for arm in sorted(expected):
        objective,method=arm.split(':',1)
        candidates=[r for r in rows if r['arm']==arm]
        if len(candidates)!=2:raise ValueError('two terminal candidate slots per arm required')
        best=initial['cross_scores'][objective];trajectory=[]
        for g,row in enumerate(candidates):
            value=number(row['cross_scores'][objective])
            if value is not None:best=value if best is None else min(best,value)
            if row['status']=='generation-failure' and (value is not None or row['forward_complete']):
                raise ValueError('generation failure cannot carry a measured forward')
            entry={'row_id':row['row_id'],'arm':arm,'generation':g,'status':row['status'],
                'forward_complete':row['forward_complete'],'own_loss':value,
                'cross_scores':deepcopy(row['cross_scores']),
                'system_sha256':digest(row['system']) if row['system'] is not None else None,
                'best_including_initial_for_final_comparison':best}
            trajectory.append(entry);slots.append(entry)
        paths[arm]={'objective':objective,'method':method,'initial_comparison_loss':initial['cross_scores'][objective],
            'initial_exposed_before_first_proposal':False,'candidate_slots':trajectory,
            'fixed_selection':deepcopy(selection['selected'][arm]),
            'strict_development_gain_over_initial':None if selection['selected'][arm]['loss'] is None
                or initial['cross_scores'][objective] is None else
                    selection['selected'][arm]['loss']<initial['cross_scores'][objective]}
    arrival={row['row_id']:i for i,row in enumerate(rows)}
    slots.sort(key=lambda row:arrival[row['row_id']])
    worlds={r['identity']:r for r in audit['worlds']}
    if len(worlds)!=len(audit['worlds']):raise ValueError('unique physical world IDs required')
    evaluation=[];seen=set()
    for logical in audit['logical_evaluation']:
        key=(logical['label'],logical['seed'])
        if key in seen:raise ValueError('logical evaluation duplicated')
        seen.add(key);world=worlds[logical['physical_job']]
        if world['role']!='selection-fixed-evaluation' or world['seed']!=logical['seed']:
            raise ValueError('logical evaluation has wrong physical seed/role')
        evaluation.append({**logical,'status':world['status'],'scores':deepcopy(world['scores'])})
    labels=sorted({r['label'] for r in evaluation});summaries={}
    for label in labels:
        subset=[r for r in evaluation if r['label']==label]
        if sorted(r['seed'] for r in subset)!=seeds:raise ValueError('three declared evaluation seeds required')
        summaries[label]={k:descriptive([{'value':number(r['scores'][k])} for r in subset],'value')
            for k in ('throughput','efficiency','selective')}
    paired=[]
    for row in evaluation:
        if not row['label'].startswith('selected:'):continue
        for reference in references:
            other=next((r for r in evaluation if r['label']=='reference:'+reference and r['seed']==row['seed']),None)
            if other is None:raise ValueError('missing predeclared evaluation reference')
            paired.append({'label':row['label'],'reference':reference,'seed':row['seed'],
                'shared_same_physical_job':row['physical_job']==other['physical_job'],
                'differences':{k:None if row['scores'][k] is None or other['scores'][k] is None else
                    row['scores'][k]-other['scores'][k] for k in ('throughput','efficiency','selective')}})
    result={'schema':'scienceutopia.native-institution-loop-report.v1' if native else 'scienceutopia.pre-scale-search-report.v1','audit_sha256':audit['content_sha256'],
        'source_commit':audit['source_commit'],'plan_sha256':audit['plan_sha256'],
        'search_slots':slots,'status_counts':dict(Counter(r['status'] for r in slots)),
        'development_world_bindings':physical_bindings,
        'systems_by_sha256':{digest(system):deepcopy(system) for system in
            [row['system'] for row in rows if row['system'] is not None]+[w['system'] for w in audit['worlds']]},
        'authoring':deepcopy(audit.get('authoring')),
        'selection_pooled':deepcopy(selection['pooled']),'selection_frozen_utc':selection['frozen_utc'],
        'optimization_paths':paths,'references':[r for r in rows if r['arm'] is None],
        'evaluation_rows':evaluation,'evaluation_summary':summaries,'paired_reference_differences':paired,
        'physical_evaluation_worlds':len({r['physical_job'] for r in evaluation}),
        'logical_evaluation_rows':len(evaluation),'worlds':[
            {'identity':r['identity'],'role':r['role'],'seed':r['seed'],'status':r['status'],'scores':r['scores'],
             'system_sha256':digest(r['system']),
             'physical_forward_status':r['physical_proof'].get('status'),
             'measurement':deepcopy(r['physical_proof'].get('measurement')),
             'checkpoint_sha256':r['physical_proof'].get('checkpoint_sha256'),
             'scientist_call_component_seconds':sum(v['interval_llm_elapsed_seconds'] for v in
                r['physical_proof'].get('annual_checkpoints',[])) if r['physical_proof'].get('annual_checkpoints') else None}
            for r in audit['worlds']],
        'limits':['One two-step controller history per objective/method, one development world seed; descriptive feasibility, not a powered method ranking.',
            'Every failed generation/execution remains a consumed slot; no replacement or numerical imputation.',
            'Common initial is a final comparison option, not an exposed pre-first-proposal observation.',
            'Identical policies share physical evaluation jobs explicitly; logical labels are not extra independent samples.',
            'Scientist call intervals exclude readiness, designer calls, role loads, retrieval and other host overhead.',
            'A changed source/specification or lower proxy loss is not automatically useful institutional invention or scientific progress.'],
        'new_model_calls':0,'new_native_worlds':0,'scientific_goal_complete':False}
    if native:
        result.update(methods=list(methods),evaluation_seeds=list(seeds),
            figure_scope='Native routing-v2 pilot; not a method-superiority study')
    result['content_sha256']=digest(result)
    return result


def render(report,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors=('#198d91','#7861a5','#bc8037','#777777')
    with plt.rc_context({'font.size':8.5,'axes.spines.top':False,'axes.spines.right':False,
            'svg.hashsalt':'pre-scale-search-v1'}):
        fig,axes=plt.subplots(1,2,figsize=(6.7,2.9))
        for ax,objective,title in zip(axes,OBJECTIVES,('T: throughput objective','E: efficiency objective')):
            any_available=False
            for method,color in zip(report.get('methods',METHODS),colors):
                path=report['optimization_paths'][objective+':'+method]
                values=[path['initial_comparison_loss']]+[
                    r['best_including_initial_for_final_comparison'] for r in path['candidate_slots']]
                any_available=any_available or any(v is not None for v in values)
                ax.plot([0,1,2],values,
                    color=color,marker='o',ms=3,label=method)
                for i,r in enumerate(path['candidate_slots'],1):
                    if r['own_loss'] is None and r['best_including_initial_for_final_comparison'] is not None:ax.annotate('×',(i,r['best_including_initial_for_final_comparison']),
                        xytext=(0,6),textcoords='offset points',ha='center',color=color)
            ax.set(title=title,xlabel='Consumed candidate slots',ylabel='Best own loss incl. initial',xticks=[0,1,2])
            if not any_available:
                ax.set_yticks([]);ax.text(.5,.55,'No available losses',transform=ax.transAxes,ha='center')
        handles,labels=axes[0].get_legend_handles_labels()
        if report.get('figure_scope'):fig.suptitle(report['figure_scope'],fontsize=9)
        fig.legend(handles,labels,loc='lower center',ncol=2,frameon=False,fontsize=8)
        fig.subplots_adjust(left=.09,right=.99,top=.86,bottom=.32,wspace=.3)
        for ext in ('png','svg'):
            fig.savefig(output/('objective-conditioned-paths.'+ext),dpi=240,
                metadata={'Date':None} if ext=='svg' else None)
        plt.close(fig)
        render_evaluation(report,output)


def render_evaluation(report,output):
    """Common-score views keep shared labels, unknowns and physical counts explicit."""
    import matplotlib.pyplot as plt
    labels=list(report['evaluation_summary']);seeds=report.get('evaluation_seeds',(51001,51011,51017))
    colors=('#198d91','#bc8037','#7861a5');lookup={(r['label'],r['seed']):r for r in report['evaluation_rows']}
    fig,axes=plt.subplots(1,3,figsize=(8.0,max(3.6,.27*len(labels)+1.25)),sharey=True)
    for ax,key,title in zip(axes,('throughput','efficiency','selective'),('T: −A','E: −Q + 0.5R','C: 4A − Q + 0.1R')):
        known=[r['scores'][key] for r in report['evaluation_rows'] if r['scores'][key] is not None]
        low,high=(min(known),max(known)) if known else (-1.,1.)
        span=max(high-low,1.);ax.set_xlim(low-.12*span,high+.45*span)
        for i,label in enumerate(labels):
            available=0
            for j,(seed,color) in enumerate(zip(seeds,colors)):
                value=lookup[label,seed]['scores'][key]
                if value is not None:
                    ax.scatter([value],[i+(j-1)*.16],color=color,s=15,label=str(seed) if i==0 else None);available+=1
            ax.text(.98,i,f'{available}/3',transform=ax.get_yaxis_transform(),ha='right',va='center',fontsize=7,color='#666666')
        if not known:ax.set_xticks([])
        ax.set(title=title,xlabel='Lower proxy loss is better',yticks=range(len(labels)),ylim=(len(labels)-.4,-.6))
        ax.grid(axis='y',color='#eeeeee',lw=.5);ax.set_axisbelow(True)
    def label_text(value):
        return value.replace('reference:','Ref · ').replace('selected:throughput:','T · ').replace('selected:efficiency:','E · ')
    axes[0].set_yticklabels([label_text(v) for v in labels],fontsize=7.5)
    # An empty first row must not remove declared seed colors from the legend.
    from matplotlib.lines import Line2D
    handles=[Line2D([],[],color=c,marker='o',ls='',ms=4,label=str(seed)) for seed,c in zip(seeds,colors)]
    fig.legend(handles=handles,loc='lower center',bbox_to_anchor=(.5,.055),ncol=3,frameon=False,fontsize=8)
    fig.text(.5,.025,'Right-edge counts: available / 3. Missing values are not plotted; labels can share worlds.',
        ha='center',fontsize=7.5,color='#666666')
    prefix=report.get('figure_scope','')
    fig.suptitle((prefix+' · ' if prefix else '')+f'Fixed selection · {report["logical_evaluation_rows"]} label/seed rows share {report["physical_evaluation_worlds"]} physical worlds',fontsize=9)
    fig.subplots_adjust(left=.25,right=.99,bottom=.2,top=.85,wspace=.25)
    for ext in ('png','svg'):
        fig.savefig(output/('selection-fixed-common-scores.'+ext),dpi=240,
            metadata={'Date':None} if ext=='svg' else None)
    plt.close(fig)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--audit',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);p.add_argument('--plan',type=Path);args=p.parse_args()
    if args.output.exists():raise ValueError('fresh report destination required')
    original=file_sha256(args.audit);plan_hash=file_sha256(args.plan) if args.plan else None
    report=summarize(json.loads(args.audit.read_text()),plan=json.loads(args.plan.read_text()) if args.plan else None)
    args.output.mkdir(parents=True);write_json_atomic(args.output/'report.json',report,sort_keys=True,allow_nan=False)
    render(report,args.output)
    if file_sha256(args.audit)!=original:raise ValueError('audit changed during projection')
    if args.plan and file_sha256(args.plan)!=plan_hash:raise ValueError('plan changed during projection')
    manifest={'schema':'scienceutopia.pre-scale-search-figures.v1','input_file_sha256':original,
        'report_content_sha256':report['content_sha256'],
        'files':{p.name:file_sha256(p) for p in sorted(args.output.iterdir()) if p.is_file()},
        'new_model_calls':0,'new_native_worlds':0}
    if args.plan:manifest['plan_file_sha256']=plan_hash
    write_json_atomic(args.output/'manifest.json',{**manifest,'content_sha256':digest(manifest)},sort_keys=True,allow_nan=False)
    print(json.dumps({'output':str(args.output),'report':report['content_sha256'],'new_model_calls':0}))


if __name__=='__main__':main()
