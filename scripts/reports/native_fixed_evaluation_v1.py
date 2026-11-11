"""Portable, all-slot report of the CLOSED separate fixed-policy evaluation.

Never selects a new policy, reads live results, calls a model or repairs code.
Two matching original-source cold audits are required at the CLI boundary.
"""
import argparse
import csv
import json
from pathlib import Path

from scripts.run_native_fixed_candidate_evaluation_v1 import fixed_selection,jobs_for
from scripts.run_causal_authoring_assay_v1 import differences
from scripts.reports.native_design_benchmark import descriptive
from scripts.reports.pre_scale_search_v1 import render_evaluation
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_numeric_designer import checked,save
from utopia.system import SystemSpec
from utopia.system.design_patch import clone,digest
from utopia.utils.data_utils import file_sha256

SCHEMA='scienceutopia.native-fixed-evaluation-report.v1'


def summarize(plan,audit,original,origin):
    for value in (plan,audit,original,origin):checked(value)
    if (plan['schema']!='scienceutopia.native-fixed-candidate-evaluation.v1.plan'
            or audit['schema']!='scienceutopia.native-fixed-candidate-evaluation-audit.v1'
            or audit['source_commit']!=plan['source_commit'] or audit['plan_sha256']!=plan['content_sha256']
            or audit['closure']['terminal']['status']!='closed'
            or audit['closure']['terminal']['completed_jobs']!=len(plan['jobs'])
            or audit.get('source_proof',{}).get('status')!='verified-exact-source-closure'
            or audit['new_model_calls']!=0 or audit['new_code_executions']!=0
            or audit['original_search_status']!='stopped'
            or audit['origin_audit_content_sha256']!=origin['content_sha256']
            or plan['origin_audit_content_sha256']!=origin['content_sha256']
            or plan['fixed_selection']!=fixed_selection(original,origin)
            or audit['fixed_selection']!=plan['fixed_selection'] or plan['jobs']!=jobs_for(plan)):
        raise ValueError('matching closed evaluation and unchanged stopped origin required')
    if len(audit['worlds'])!=len(plan['jobs']):raise ValueError('all physical jobs required')
    objectives=tuple(plan['losses']);worlds=[];logical=[]
    seeds=plan['evaluation']['seeds'];labels=['reference:'+r for r in plan['evaluation']['reference_labels']]
    labels+=['selected:'+arm for arm in plan['arm_order']]
    if len(labels)!=len(set(labels)):raise ValueError('unique logical labels required')
    for job,world in zip(plan['jobs'],audit['worlds']):
        if (any(job[k]!=world[k] for k in job) or world['status']!='complete'
                or world['role']!='selection-fixed-evaluation'):
            raise ValueError('physical evaluation differs from frozen job')
        m=world['physical_proof']['measurement']
        if m['system_fingerprint']!=SystemSpec.from_dict(job['system']).fingerprint:
            raise ValueError('physical measurement system identity differs')
        scores={k:evaluate_loss(v,[m])['loss'] for k,v in plan['losses'].items()}
        if scores!=world['scores'] or any(v is None for v in scores.values()):
            raise ValueError('physical measurement and literal scores differ')
        row={'physical_job':job['identity'],'seed':job['seed'],'policy_sha256':job['policy_sha256'],
            'labels':clone(job['labels']),'scores':scores,'measurement':clone(m),
            'system_sha256':digest(job['system'])}
        worlds.append(row)
        for label in job['labels']:
            if label not in labels:raise ValueError('unaccounted logical label')
            logical.append({'label':label,'seed':job['seed'],'physical_job':job['identity'],
                'status':'complete','scores':clone(scores)})
    for arm,selection in plan['fixed_selection']['selected'].items():
        if selection['system'] is None:
            logical.extend({'label':'selected:'+arm,'seed':s,'physical_job':None,
                'status':'no-completed-submission','scores':{k:None for k in objectives}} for s in seeds)
    lookup={(r['label'],r['seed']):r for r in logical}
    if len(lookup)!=len(logical) or set(lookup)!={(label,s) for label in labels for s in seeds}:
        raise ValueError('exactly one complete or explicitly unavailable row per label and seed required')
    logical=[lookup[label,s] for label in labels for s in seeds]
    summary={label:{k:descriptive([{'value':lookup[label,s]['scores'][k]} for s in seeds],'value')
        for k in objectives} for label in labels}
    paired=[]
    for label in labels:
        if not label.startswith('selected:'):continue
        for reference in plan['evaluation']['reference_labels']:
            for seed in seeds:
                a,b=lookup[label,seed],lookup['reference:'+reference,seed]
                paired.append({'label':label,'reference':reference,'seed':seed,
                    'physical_job':a['physical_job'],'reference_physical_job':b['physical_job'],
                    'shared_same_physical_job':a['physical_job'] is not None and a['physical_job']==b['physical_job'],
                    'differences':{k:None if a['scores'][k] is None else a['scores'][k]-b['scores'][k]
                        for k in objectives}})
    submitted=[w for w in origin['worlds'] if w['role'].startswith('search:')]
    attempts=plan['fixed_selection']['all_attempts'];schedule=original['schedule'];slots=[]
    if (len(submitted)!=len(attempts) or len(attempts)+plan['fixed_selection']['unsubmitted_slots']!=len(schedule)
            or plan['fixed_selection']['unsubmitted_slots']!=1
            or plan['fixed_selection']['missing_slot']!=schedule[-1]):
        raise ValueError('complete chronological stopped-prefix slots required')
    for i,slot in enumerate(schedule):
        row={**clone(slot),'slot_index':i,'loss':None,'physical_job':None,
            'status':'not-submitted','cross_scores':{k:None for k in objectives},'changed_paths':None}
        if i<len(attempts):
            a,w=attempts[i],submitted[i];objective=original['assignments'][slot['arm']]['objective']
            if (any(a[k]!=slot[k] for k in ('arm','generation')) or a['status']!=w['status']
                    or w['role']!='search:'+slot['arm'] or a['loss']!=w['scores'][objective]):
                raise ValueError('stopped attempt differs from original chronological world')
            base=original['campaign_bindings']['run-00'][slot['arm']]['initial_system']
            row.update(loss=a['loss'],physical_job=w['identity'],status=w['status'],cross_scores=clone(w['scores']),
                changed_paths=differences(base,w['system']),
                connections_changed=base['connections']!=w['system']['connections'],
                schedules_changed=base['schedules']!=w['system']['schedules'])
        slots.append(row)
    result={'schema':SCHEMA,'source_commit':plan['source_commit'],'plan_sha256':plan['content_sha256'],
        'audit_sha256':audit['content_sha256'],'origin_audit_sha256':origin['content_sha256'],
        'original_search_status':'stopped','search_slots':slots,'fixed_selection':{
            arm:{k:clone(v) for k,v in choice.items() if k!='system'}
            for arm,choice in plan['fixed_selection']['selected'].items()},
        'physical_worlds':worlds,'evaluation_rows':logical,'evaluation_summary':summary,
        'paired_reference_differences':paired,'evaluation_seeds':clone(seeds),
        'physical_evaluation_worlds':len(worlds),'logical_evaluation_rows':len(logical),
        'unavailable_label_seed_rows':sum(r['physical_job'] is None for r in logical),
        'figure_scope':'Separate fixed-policy evaluation',
        'evaluation_title':f'Fixed submissions: {sum(r["physical_job"] is not None for r in logical)} observed label/seed rows; '
            f'{sum(r["physical_job"] is None for r in logical)} unavailable; {len(worlds)} physical worlds',
        'evaluation_footer':'Right edge: available / 3. 0/3 = no completed policy. Shared labels are not independent samples.',
        'interpretation':{'equal_search_budgets':False,'independent_optimizer_replications':False,
            'three_seeds_are_descriptive':True,'selective_score_is_not_optimized':True,
            'loss_improvement_is_not_scientific_truth':True,'baseline_fallback':False,
            'selection_changed':False,'new_model_calls':0,'new_native_worlds':0,'publication_ready':False}}
    result['content_sha256']=digest(result);return result


def render_paths(report,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    arms=[o+':'+m for o in ('throughput','efficiency')
          for m in ('parameters','code-fixed-graph','code-and-graph')]
    with plt.rc_context({'font.size':8,'axes.spines.top':False,'axes.spines.right':False,
                         'svg.hashsalt':SCHEMA}):
        fig,axes=plt.subplots(2,3,figsize=(8.4,4.5),squeeze=False)
        for ax,arm in zip(axes.flat,arms):
            rows=[r for r in report['search_slots'] if r['arm']==arm];best=None;path=[]
            for row in rows:
                v=row['loss'];best=min(best,v) if best is not None and v is not None else v if best is None else best
                path.append(best)
                if v is not None:ax.scatter([row['generation']],[v],color='#157b80',s=22,zorder=3)
                else:ax.text(row['generation'],.08,'unsubmitted' if row['status']=='not-submitted' else 'technical null',
                    transform=ax.get_xaxis_transform(),ha='center',fontsize=7,color='#9a443e')
            ax.plot([r['generation'] for r in rows],path,color='#157b80',lw=1,label='Best submitted own loss')
            ax.set(title=arm.replace(':',' / '),xlabel='Original generation',ylabel='Assigned loss (lower is better)',
                   xticks=[0,1],xlim=(-.3,1.3))
            ax.grid(axis='y',color='#eeeeee')
            if all(v is None for v in path):ax.set_yticks([])
        fig.suptitle('Stopped original search: all 12 slots; no initial-policy fallback',fontsize=10)
        fig.tight_layout(rect=(0,0,1,.94))
        for ext in ('png','svg'):fig.savefig(output/('stopped-search-paths.'+ext),dpi=240,
            metadata={'Date':None} if ext=='svg' else None)
        plt.close(fig)


def export(args):
    paths=[args.plan,args.audit_one,args.audit_two,args.original_plan,args.origin_audit]
    before={str(p):file_sha256(p) for p in paths}
    if args.output.exists():raise ValueError('fresh report output required')
    if args.audit_one.read_bytes()!=args.audit_two.read_bytes():raise ValueError('two cold evaluation audits differ')
    plan,audit,original,origin=[json.loads(p.read_text()) for p in
        (args.plan,args.audit_one,args.original_plan,args.origin_audit)]
    report=summarize(plan,audit,original,origin)
    args.output.mkdir(parents=True);save(args.output/'report.json',{k:v for k,v in report.items() if k!='content_sha256'})
    render_paths(report,args.output)
    import matplotlib.pyplot as plt
    with plt.rc_context({'svg.hashsalt':SCHEMA,'font.size':8.5,
            'axes.spines.top':False,'axes.spines.right':False}):
        render_evaluation(report,args.output)
    with (args.output/'physical-components.csv').open('x',newline='') as f:
        fields=['physical_job','seed','policy_sha256','labels',*plan['losses'],
                'accepted_decisions','accepted_peer_score_sum','review_records']
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for row in report['physical_worlds']:
            metrics=row['measurement']['metrics']
            writer.writerow({**{k:row[k] for k in fields[:3]},'labels':' | '.join(row['labels']),**row['scores'],
                **{k:metrics['native.'+k]['value'] for k in fields[-3:]}})
    if before!={str(p):file_sha256(p) for p in paths}:raise ValueError('report inputs changed')
    save(args.output/'manifest.json',{'schema':SCHEMA+'.export','inputs':before,
        'report_content_sha256':report['content_sha256'],
        'files':{p.name:file_sha256(p) for p in sorted(args.output.iterdir()) if p.is_file()},
        'new_model_calls':0,'new_native_worlds':0})
    print(json.dumps({'report_content_sha256':report['content_sha256'],
        'physical_worlds':len(report['physical_worlds']),'label_seed_rows':len(report['evaluation_rows'])}))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('plan','audit-one','audit-two','original-plan','origin-audit','output'):
        p.add_argument('--'+key,type=Path,required=True)
    export(p.parse_args())


if __name__=='__main__':main()
