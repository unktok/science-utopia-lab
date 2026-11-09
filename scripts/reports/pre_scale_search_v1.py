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


def summarize(audit):
    checked(audit)
    if audit['schema']!='scienceutopia.pre-scale-search-audit.v1':
        raise ValueError('closed original-source search/evaluation audit required')
    selection=audit['selection'];rows=selection['all_rows']
    initial=next(r for r in rows if r['row_id']=='reference:open-seed')
    if len(rows)!=22 or len({r['row_id'] for r in rows})!=22:
        raise ValueError('all six reference and sixteen candidate rows required')
    expected={o+':'+m for o in OBJECTIVES for m in METHODS}
    if set(selection['selected'])!=expected:raise ValueError('every objective/method selection required')
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
        if sorted(r['seed'] for r in subset)!=[51001,51011,51017]:raise ValueError('three declared evaluation seeds required')
        summaries[label]={k:descriptive([{'value':number(r['scores'][k])} for r in subset],'value')
            for k in ('throughput','efficiency','selective')}
    paired=[]
    for row in evaluation:
        if not row['label'].startswith('selected:'):continue
        for reference in ('open-seed','reviewed-accept-all','no-review-accept-all','no-review-reject-all'):
            other=next((r for r in evaluation if r['label']=='reference:'+reference and r['seed']==row['seed']),None)
            if other is None:raise ValueError('missing predeclared evaluation reference')
            paired.append({'label':row['label'],'reference':reference,'seed':row['seed'],
                'shared_same_physical_job':row['physical_job']==other['physical_job'],
                'differences':{k:None if row['scores'][k] is None or other['scores'][k] is None else
                    row['scores'][k]-other['scores'][k] for k in ('throughput','efficiency','selective')}})
    result={'schema':'scienceutopia.pre-scale-search-report.v1','audit_sha256':audit['content_sha256'],
        'source_commit':audit['source_commit'],'plan_sha256':audit['plan_sha256'],
        'search_slots':slots,'status_counts':dict(Counter(r['status'] for r in slots)),
        'optimization_paths':paths,'references':[r for r in rows if r['arm'] is None],
        'evaluation_rows':evaluation,'evaluation_summary':summaries,'paired_reference_differences':paired,
        'physical_evaluation_worlds':len({r['physical_job'] for r in evaluation}),
        'logical_evaluation_rows':len(evaluation),'worlds':[
            {'identity':r['identity'],'role':r['role'],'seed':r['seed'],'status':r['status'],'scores':r['scores'],
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
            for method,color in zip(METHODS,colors):
                path=report['optimization_paths'][objective+':'+method]
                ax.plot([0,1,2],[path['initial_comparison_loss']]+[
                    r['best_including_initial_for_final_comparison'] for r in path['candidate_slots']],
                    color=color,marker='o',ms=3,label=method)
                for i,r in enumerate(path['candidate_slots'],1):
                    if r['own_loss'] is None and r['best_including_initial_for_final_comparison'] is not None:ax.annotate('×',(i,r['best_including_initial_for_final_comparison']),
                        xytext=(0,6),textcoords='offset points',ha='center',color=color)
            ax.set(title=title,xlabel='Consumed candidate slots',ylabel='Best own loss incl. initial',xticks=[0,1,2])
        handles,labels=axes[0].get_legend_handles_labels()
        fig.legend(handles,labels,loc='lower center',ncol=2,frameon=False,fontsize=8)
        fig.subplots_adjust(left=.09,right=.99,top=.86,bottom=.32,wspace=.3)
        for ext in ('png','svg'):
            fig.savefig(output/('objective-conditioned-paths.'+ext),dpi=240,
                metadata={'Date':None} if ext=='svg' else None)
        plt.close(fig)


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--audit',type=Path,required=True)
    p.add_argument('--output',type=Path,required=True);args=p.parse_args()
    if args.output.exists():raise ValueError('fresh report destination required')
    original=file_sha256(args.audit);report=summarize(json.loads(args.audit.read_text()))
    args.output.mkdir(parents=True);write_json_atomic(args.output/'report.json',report,sort_keys=True,allow_nan=False)
    render(report,args.output)
    if file_sha256(args.audit)!=original:raise ValueError('audit changed during projection')
    manifest={'schema':'scienceutopia.pre-scale-search-figures.v1','input_file_sha256':original,
        'report_content_sha256':report['content_sha256'],
        'files':{p.name:file_sha256(p) for p in sorted(args.output.iterdir()) if p.is_file()},
        'new_model_calls':0,'new_native_worlds':0}
    write_json_atomic(args.output/'manifest.json',{**manifest,'content_sha256':digest(manifest)},sort_keys=True,allow_nan=False)
    print(json.dumps({'output':str(args.output),'report':report['content_sha256'],'new_model_calls':0}))


if __name__=='__main__':main()
