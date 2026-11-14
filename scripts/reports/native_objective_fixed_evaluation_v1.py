"""Every fixed policy, control, unused seed and null after two cold audits."""
import argparse
import csv
import json
from pathlib import Path

from scripts.analyze_native_open_v7 import _inventory
from scripts.run_native_objective_fixed_evaluation_v1 import jobs_for
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_numeric_designer import checked,save
from utopia.system.design_patch import clone,digest
from utopia.utils.data_utils import file_sha256

SCHEMA='scienceutopia.native-objective-fixed-report.v1'


def summarize(plan,audit,*,study='count-content-v1'):
    checked(plan);checked(audit)
    if study=='count-content-v1':
        plan_schema='scienceutopia.native-objective-fixed-evaluation.v1.plan'
        audit_schema='scienceutopia.native-objective-fixed-evaluation-audit.v1';schema=SCHEMA
    elif study=='capacity-v1':
        plan_schema='scienceutopia.native-capacity-fixed-evaluation.v1.plan'
        audit_schema='scienceutopia.native-capacity-fixed-evaluation-audit.v1'
        schema='scienceutopia.native-capacity-fixed-report.v1'
        if plan['objectives']!=['throughput','founder-activity']:
            raise ValueError('literal T/P objectives required')
    elif study=='planning-v1':
        plan_schema='scienceutopia.native-planning-fixed-evaluation.v1.plan'
        audit_schema='scienceutopia.native-planning-fixed-evaluation-audit.v1'
        schema='scienceutopia.native-planning-fixed-report.v1'
        from utopia.system.native_planning_controls import ORDER
        if (plan['objectives']!=['throughput','content-utility']
                or plan['evaluation']['reference_labels']!=list(ORDER)):
            raise ValueError('literal planning T/U objectives and all eight controls required')
    elif study=='joint-v1':
        plan_schema='scienceutopia.native-joint-fixed-evaluation.v1.plan'
        audit_schema='scienceutopia.native-joint-fixed-evaluation-audit.v1'
        schema='scienceutopia.native-joint-fixed-report.v1'
        from utopia.system.native_planning_controls import ORDER
        from scripts.run_native_joint_fixed_evaluation_v1 import contrasts_for
        if (plan['objectives']!=['throughput','content-utility'] or plan['evaluation']['reference_labels']!=list(ORDER)
                or len(plan['selection_order'])!=8 or len(set(plan['selection_order']))!=8
                or set(plan['selection_order'])!=set(plan['fixed_selection']['selected'])
                or set(plan['selection_definitions'])!=set(plan['selection_order'])
                or plan['contrasts']!=contrasts_for()):
            raise ValueError('all eight frozen own labels, common references and declared contrasts required')
    elif study=='workflow-v1':
        plan_schema='scienceutopia.native-workflow-fixed-evaluation.v1.plan'
        audit_schema='scienceutopia.native-workflow-fixed-evaluation-audit.v1'
        schema='scienceutopia.native-workflow-fixed-report.v1'
        from scripts.run_native_workflow_fixed_evaluation_v1 import REFERENCES
        if plan['objectives']!=['throughput','content-utility'] or plan['evaluation']['reference_labels']!=REFERENCES:
            raise ValueError('literal workflow T/U objectives and both controls required')
    elif study=='longitudinal-v1':
        from scripts.run_native_longitudinal_fixed_evaluation_v1 import SCHEMA as family, REFERENCES
        from scripts.run_native_longitudinal_comparison_v1 import ARMS, OBJECTIVES
        plan_schema=family+'.plan'
        audit_schema='scienceutopia.native-longitudinal-fixed-evaluation-audit.v1'
        schema='scienceutopia.native-longitudinal-fixed-report.v1'
        if (plan['objectives']!=list(OBJECTIVES) or plan['arms']!=list(ARMS)
                or plan['evaluation']['reference_labels']!=REFERENCES
                or plan['selection_order']!=[a+'::'+o for a in ARMS for o in OBJECTIVES]):
            raise ValueError('literal four objective/arm selections and both controls required')
    else:raise ValueError('explicit supported fixed-report study required')
    if (plan['schema']!=plan_schema
            or audit['schema']!=audit_schema
            or audit['source_commit']!=plan['source_commit'] or audit['plan_sha256']!=plan['content_sha256']
            or audit['closure']['terminal']['status']!='closed' or audit['closure']['terminal']['completed_jobs']!=len(plan['jobs'])
            or audit['source_proof']['status']!='verified-exact-source-closure' or not audit['held_out_world_seeds']
            or audit['fixed_selection']!=plan['fixed_selection'] or audit['origin_audit_content_sha256']!=plan['origin_audit_content_sha256']
            or audit['new_model_calls'] or audit['new_code_executions'] or plan['jobs']!=jobs_for(plan)):
        raise ValueError('matching normally closed fixed-evaluation audit/selection required')
    worlds={w['identity']:w for w in audit['worlds']}
    if len(worlds)!=len(audit['worlds']) or set(worlds)!={j['identity'] for j in plan['jobs']}:
        raise ValueError('exact unique physical evaluation jobs required')
    selected_keys=plan['selection_order'] if study in ('joint-v1','longitudinal-v1') else plan['objectives']
    labels=['reference:'+r for r in plan['evaluation']['reference_labels']]+['selected:'+o for o in selected_keys]
    physical=[];logical=[]
    for job in plan['jobs']:
        w=worlds[job['identity']]
        if any(w[k]!=v for k,v in job.items()) or w['role']!='selection-fixed-evaluation':raise ValueError('literal frozen evaluation job differs')
        scores={k:evaluate_loss(v,w['measurements'])['loss'] for k,v in plan['losses'].items()}
        if scores!=w['scores'] or (w['status']=='complete')!=(scores['throughput'] is not None):
            raise ValueError('additional literal measurements/cross-scores differ')
        physical.append({**clone(job),'status':w['status'],'scores':scores,'measurements':clone(w['measurements'])})
        for label in job['labels']:
            if label not in labels:raise ValueError('unplanned logical evaluation label')
            logical.append({'label':label,'seed':job['seed'],'physical_job':job['identity'],'status':w['status'],'scores':clone(scores)})
    for objective,s in plan['fixed_selection']['selected'].items():
        if s['system'] is None:
            logical.extend({'label':'selected:'+objective,'seed':seed,'physical_job':None,
                'status':'no-completed-submission','scores':{k:None for k in plan['losses']}} for seed in plan['evaluation']['seeds'])
    by={(r['label'],r['seed']):r for r in logical}
    if len(by)!=len(logical) or set(by)!={(label,seed) for label in labels for seed in plan['evaluation']['seeds']}:
        raise ValueError('every logical policy and seed must appear exactly once')
    logical=[by[label,seed] for label in labels for seed in plan['evaluation']['seeds']];paired=[]
    for objective in selected_keys:
        label='selected:'+objective
        for reference in plan['evaluation']['reference_labels']:
            for seed in plan['evaluation']['seeds']:
                a,b=by[label,seed],by['reference:'+reference,seed]
                paired.append({'label':label,'reference':reference,'seed':seed,'physical_job':a['physical_job'],
                    'reference_physical_job':b['physical_job'],'same_physical_job':a['physical_job'] is not None and a['physical_job']==b['physical_job'],
                    'differences':{k:None if a['scores'][k] is None or b['scores'][k] is None else a['scores'][k]-b['scores'][k] for k in plan['losses']}})
    result={'schema':schema,'source_commit':plan['source_commit'],'plan_sha256':plan['content_sha256'],
        'audit_sha256':audit['content_sha256'],'origin_audit_content_sha256':plan['origin_audit_content_sha256'],
        'score_order':clone(plan['objectives']),'seeds':clone(plan['evaluation']['seeds']),
        'labels':labels,'reference_labels':clone(plan['evaluation']['reference_labels']),
        'fixed_selection':clone(plan['fixed_selection']),'physical_worlds':physical,'logical_rows':logical,'paired_differences':paired,
        'interpretation':{'candidate_reselection':False,'baseline_fallback':False,'independent_optimizer_replications':False,
            'new_literature_or_independent_critic_errors':False,'scientific_truth':False,'publication_ready':False,
            'missing_losses_imputed':False,'new_model_calls':0,'new_code_executions':0}}
    if study=='joint-v1':
        contrasts=[]
        for definition in plan['contrasts']:
            for seed in plan['evaluation']['seeds']:
                a,b=by['selected:'+definition['left'],seed],by['selected:'+definition['right'],seed]
                contrasts.append({**clone(definition),'seed':seed,'left_physical_job':a['physical_job'],
                    'right_physical_job':b['physical_job'],
                    'same_physical_job':a['physical_job'] is not None and a['physical_job']==b['physical_job'],
                    'differences':{k:None if a['scores'][k] is None or b['scores'][k] is None else a['scores'][k]-b['scores'][k]
                        for k in plan['losses']}})
        result.update(selection_order=clone(selected_keys),selection_definitions=clone(plan['selection_definitions']),
            contrast_definitions=clone(plan['contrasts']),fixed_policy_contrasts=contrasts,
            data_identity=clone(plan['scientist']['dataset_identity']))
    if study=='workflow-v1':
        result['objective_choice_differences']=[]
        for seed in plan['evaluation']['seeds']:
            a,b=by['selected:throughput',seed],by['selected:content-utility',seed]
            result['objective_choice_differences'].append({'seed':seed,
                'left':'selected:throughput','right':'selected:content-utility',
                'left_physical_job':a['physical_job'],'right_physical_job':b['physical_job'],
                'same_physical_job':a['physical_job'] is not None and a['physical_job']==b['physical_job'],
                'differences':{k:None if a['scores'][k] is None or b['scores'][k] is None
                    else a['scores'][k]-b['scores'][k] for k in plan['losses']}})
    if study=='longitudinal-v1':
        result.update(selection_order=clone(selected_keys), information_arms=clone(plan['arms']),
            objective_choice_differences=[], information_access_differences=[])
        def contrast(left,right,seed):
            a,b=by['selected:'+left,seed],by['selected:'+right,seed]
            return {'seed':seed,'left':'selected:'+left,'right':'selected:'+right,
                'left_physical_job':a['physical_job'],'right_physical_job':b['physical_job'],
                'same_physical_job':a['physical_job'] is not None and a['physical_job']==b['physical_job'],
                'differences':{k:None if a['scores'][k] is None or b['scores'][k] is None
                    else a['scores'][k]-b['scores'][k] for k in plan['losses']}}
        for seed in plan['evaluation']['seeds']:
            for arm in plan['arms']:
                result['objective_choice_differences'].append({'arm':arm,
                    **contrast(arm+'::throughput',arm+'::content-utility',seed)})
            for objective in plan['objectives']:
                result['information_access_differences'].append({'objective':objective,
                    **contrast('parent-trajectory::'+objective,'scalar::'+objective,seed)})
    result['content_sha256']=digest(result);return result


def render(report,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors=['#087f8c','#9c5d8a','#b47835'];positions={label:i for i,label in enumerate(report['labels'])}
    short=lambda s:s.replace('reference:','').replace('selected:','Selected ').replace('-connected',' + resource').replace('-disconnected',' - resource')
    with plt.rc_context({'font.size':8,'axes.spines.top':False,'axes.spines.right':False,'svg.hashsalt':report['schema']}):
        fig,axes=plt.subplots(1,2,figsize=(10,4.2))
        for ax,objective in zip(axes,report['score_order']):
            for ordinal,(seed,color) in enumerate(zip(report['seeds'],colors)):
                rows=[r for r in report['logical_rows'] if r['seed']==seed]
                known=[r for r in rows if r['scores'][objective] is not None]
                ax.scatter([positions[r['label']]+(ordinal-1)*.13 for r in known],
                    [r['scores'][objective] for r in known],s=25,color=color,label=str(seed),zorder=3)
            for label in report['labels']:
                if all(r['scores'][objective] is None for r in report['logical_rows'] if r['label']==label):
                    ax.text(positions[label],.03,'unavailable',transform=ax.get_xaxis_transform(),ha='center',rotation=90,color='#a9444a',fontsize=6)
            ax.set(title=objective,ylabel='Fixed loss (lower is better)',xticks=range(len(positions)),
                xticklabels=[short(s) for s in report['labels']]);ax.tick_params(axis='x',labelrotation=60)
            for tick in ax.get_xticklabels():tick.set_ha('right')
            ax.grid(axis='y',color='#ededed');ax.legend(title='World seed',fontsize=6,title_fontsize=7)
        count = ('two' if report['schema'] in ('scienceutopia.native-workflow-fixed-report.v1',
            'scienceutopia.native-longitudinal-fixed-report.v1') else
            'eight' if report['schema']=='scienceutopia.native-planning-fixed-report.v1' else 'five')
        fig.suptitle('Frozen submitted policies and '+count+' controls: unused world seeds, no reselection',fontsize=10)
        fig.tight_layout(rect=(0,0,1,.94))
        for ext in ('png','svg'):fig.savefig(output/('fixed-policy-seed-scores.'+ext),dpi=200,metadata={'Date':None} if ext=='svg' else None)
        plt.close(fig)
        selected_names=report['selection_order'] if report['schema']=='scienceutopia.native-longitudinal-fixed-report.v1' else report['score_order']
        fig,axes=plt.subplots(len(selected_names),2,figsize=(10,2.8*len(selected_names)))
        for ax,(selected,objective) in zip(axes.flat,[(s,o) for s in selected_names for o in report['score_order']]):
            rows=[r for r in report['paired_differences'] if r['label']=='selected:'+selected]
            for ordinal,(seed,color) in enumerate(zip(report['seeds'],colors)):
                known=[r for r in rows if r['seed']==seed and r['differences'][objective] is not None]
                ax.scatter([report['reference_labels'].index(r['reference'])+(ordinal-1)*.13 for r in known],
                    [r['differences'][objective] for r in known],s=22,color=color,label=str(seed),zorder=3)
            if not any(r['differences'][objective] is not None for r in rows):
                ax.text(.5,.5,'Unavailable: no paired completed loss',transform=ax.transAxes,ha='center',color='#a9444a')
            ax.axhline(0,color='#777777',lw=.8);ax.grid(axis='y',color='#ededed')
            title = ('Selected '+selected.replace('::', ' / ')+'\nScored by '+objective
                if report['schema']=='scienceutopia.native-longitudinal-fixed-report.v1'
                else 'Selected '+selected+' / scored by '+objective)
            ax.set(title=title,ylabel='Selected minus reference loss',
                xticks=range(len(report['reference_labels'])),xticklabels=[short(r) for r in report['reference_labels']])
            ax.tick_params(axis='x',labelrotation=25,labelsize=6)
            for tick in ax.get_xticklabels():tick.set_ha('right')
        fig.suptitle('Every paired difference; below zero favors the fixed submission',fontsize=10)
        fig.tight_layout(rect=(0,0,1,.95))
        for ext in ('png','svg'):fig.savefig(output/('fixed-policy-paired-differences.'+ext),dpi=200,metadata={'Date':None} if ext=='svg' else None)
        plt.close(fig)


def export(args,*,study='count-content-v1',renderer=None):
    root=Path(args.run).resolve();output=Path(args.output).resolve();paths=[Path(args.audit_one),Path(args.audit_two),root/'plan.json']
    if output.exists() or output.is_relative_to(root):raise ValueError('fresh report outside scientific raw required')
    if paths[0].read_bytes()!=paths[1].read_bytes():raise ValueError('two original-source evaluation audits differ')
    before=_inventory(root);audit=checked(json.loads(paths[0].read_text()));plan=checked(json.loads(paths[2].read_text()))
    inputs={str(p):file_sha256(p) for p in paths}
    if digest(before)!=audit['raw_inventory_sha256']:raise ValueError('evaluation raw differs from audit')
    report=summarize(plan,audit,study=study)
    if before!=_inventory(root) or inputs!={str(p):file_sha256(p) for p in paths}:raise ValueError('evaluation report inputs changed')
    output.mkdir(parents=True);save(output/'report.json',{k:v for k,v in report.items() if k!='content_sha256'})
    (render if renderer is None else renderer)(report,output)
    for name,rows,fields,nested in [('logical-scores',report['logical_rows'],['label','seed','physical_job','status'],'scores'),
            ('paired-differences',report['paired_differences'],['label','reference','seed','physical_job','reference_physical_job','same_physical_job'],'differences')]:
        with (output/(name+'.csv')).open('x',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=fields+report['score_order']);writer.writeheader()
            for r in rows:writer.writerow({**{k:r[k] for k in fields},**r[nested]})
    if study=='joint-v1':
        fields=['id','kind','left','right','seed','left_physical_job','right_physical_job','same_physical_job']
        with (output/'fixed-contrasts.csv').open('x',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=fields+report['score_order']);writer.writeheader()
            for r in report['fixed_policy_contrasts']:writer.writerow({**{k:r[k] for k in fields},**r['differences']})
    if study=='workflow-v1':
        fields=['seed','left','right','left_physical_job','right_physical_job','same_physical_job']
        with (output/'objective-choice-differences.csv').open('x',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=fields+report['score_order']);writer.writeheader()
            for r in report['objective_choice_differences']:writer.writerow({**{k:r[k] for k in fields},**r['differences']})
    if study=='longitudinal-v1':
        for name,dimension in (('objective_choice_differences','arm'),('information_access_differences','objective')):
            fields=[dimension,'seed','left','right','left_physical_job','right_physical_job','same_physical_job']
            with (output/(name.replace('_','-')+'.csv')).open('x',newline='') as f:
                writer=csv.DictWriter(f,fieldnames=fields+report['score_order']);writer.writeheader()
                for r in report[name]:writer.writerow({**{k:r[k] for k in fields},**r['differences']})
    save(output/'manifest.json',{'schema':report['schema']+'.export','inputs':inputs,'raw_inventory_sha256':digest(before),
        'report_content_sha256':report['content_sha256'],'files':{p.name:file_sha256(p) for p in sorted(output.iterdir())},
        'new_model_calls':0,'new_code_executions':0})
    print(json.dumps({'physical_worlds':len(report['physical_worlds']),'logical_rows':len(report['logical_rows']),
        'report_content_sha256':report['content_sha256']}))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('run','audit-one','audit-two','output'):p.add_argument('--'+key,type=Path,required=True)
    export(p.parse_args())


if __name__=='__main__':main()
