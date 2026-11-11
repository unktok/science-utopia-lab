"""Read-only all-slot/actual-feedback report after two identical native audits.

No model calls, code execution, new selection, inferred fixes or failed-slot refill.
Component returns are not native validity or scientific improvement.
"""
import argparse
import csv
import json
from pathlib import Path

from scripts.analyze_native_open_v7 import _inventory
from scripts.run_causal_authoring_assay_v1 import differences
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_numeric_designer import checked,save
from utopia.optimization.native_post_edit_feedback_v1 import persistent_diagnostics
from utopia.system import SystemSpec
from utopia.system.design_patch import clone,digest
from utopia.utils.data_utils import file_sha256

SCHEMA='scienceutopia.native-code-tested-loop-report.v1'


def component_trace(steps,response,document=None):
    """Summarize observed probes only; a later return need not be a repair."""
    events=[];comparisons=[];last={};offset=0
    for index,step in enumerate(steps):
        if step['step']!=index:raise ValueError('exact chronological completed steps required')
        transition=step.get('transition')
        result=transition.get('result') if isinstance(transition,dict) else None
        feedback=result.get('component_feedback') if isinstance(result,dict) else None
        if feedback is None:continue
        if (feedback['probe_offset']!=offset or feedback['veto_on_test_failure']
                or feedback['source_repair'] or feedback['new_native_worlds'] or feedback['new_model_calls']):
            raise ValueError('literal non-veto probe prefix required')
        count=0
        for ordinal,test in enumerate(feedback['tests']):
            probes=[]
            for probe in test['results']:
                if test['status']!='tested' or probe['status'] not in ('returned','raised'):
                    raise ValueError('only declared completed probes may be counted')
                count+=1
                row={k:clone(probe[k]) for k in ('fixture_id','status','error_type',
                    'full_error_sha256','reply_content_sha256','result_sha256')}
                row.update(node_id=test['node_id'],artifact_sha256=test['artifact_sha256'],step=index)
                key=(row['node_id'],row['fixture_id']);previous=last.get(key)
                if previous is not None and previous['artifact_sha256']!=row['artifact_sha256']:
                    comparisons.append({'node_id':key[0],'fixture_id':key[1],
                        'from_step':previous['step'],'to_step':index,
                        'from_artifact_sha256':previous['artifact_sha256'],
                        'to_artifact_sha256':row['artifact_sha256'],
                        'transition':previous['status']+'-to-'+row['status'],
                        'scope':'Same saved fixture, later code; not proof of native repair or loss effect.'})
                last[key]=row;probes.append(row)
            events.append({'step':index,'tool':transition['tool'],'node_id':test['node_id'],
                'test_status':test['status'],'artifact_sha256':test.get('artifact_sha256'),
                'exact_archive_filename':f'archive/steps/{index:02d}.json',
                'json_pointer':f'/transition/result/component_feedback/tests/{ordinal}',
                'test_value_sha256':digest(test),'probes':probes})
        if count!=feedback['probe_attempts']:raise ValueError('component suite count differs')
        offset+=count
    probes=[p for e in events for p in e['probes']];summary=response['component_testing']
    if (summary['probe_attempts']!=len(probes) or summary['returned']!=sum(p['status']=='returned' for p in probes)
            or summary['raised']!=sum(p['status']=='raised' for p in probes)
            or summary['new_native_worlds'] or summary['new_model_calls_from_tests'] or summary['veto_on_finish']):
        raise ValueError('staged component totals differ from actual steps')
    return {'events':events,'same_fixture_later_code_comparisons':comparisons,
        'component_testing':clone(summary),'drawn_candidate_artifact_observations':
            None if document is None else persistent_diagnostics(document,steps),
        'completed_steps':len(steps),'automatic_repair_claimed':False}


def summarize(plan,audit,records,traces):
    checked(plan);checked(audit)
    if (plan['schema']!='scienceutopia.native-code-tested-loop.v1.plan'
            or audit['schema']!='scienceutopia.native-code-tested-loop-audit.v1'
            or audit['source_commit']!=plan['source_commit'] or audit['plan_sha256']!=plan['content_sha256']
            or audit['closure']['terminal']['status']!='closed'
            or audit['source_proof']['status']!='verified-exact-source-closure'
            or audit['new_model_calls'] or audit['new_code_executions'] or audit['held_out_evaluation']):
        raise ValueError('matching normal-closure original-source audit required')
    keys={(s['arm'],s['generation']) for s in plan['schedule']}
    if len(keys)!=len(plan['schedule']) or set(records)!=keys or set(traces)!=keys:
        raise ValueError('exactly one record and trace per scheduled slot required')
    authors={(a['arm'],a['generation']):a for a in audit['authoring']}
    worlds={w['identity']:w for w in audit['worlds']}
    if len(authors)!=len(audit['authoring']) or set(authors)!=keys or len(worlds)!=len(audit['worlds']):
        raise ValueError('duplicate or missing authoring/world identity')
    used=set();physical=[]
    for w in audit['worlds']:
        measurement=w['physical_proof'].get('measurement')
        if w['status']=='complete' and measurement is None:raise ValueError('complete world lacks measurements')
        if measurement is not None and measurement['system_fingerprint']!=SystemSpec.from_dict(w['system']).fingerprint:
            raise ValueError('physical measurement system identity differs')
        scores={k:evaluate_loss(v,[measurement] if w['status']=='complete' else [])['loss'] for k,v in plan['losses'].items()}
        if scores!=w['scores']:raise ValueError('actual checkpoint cross-score differs')
        physical.append({'identity':w['identity'],'role':w['role'],'seed':w['seed'],'status':w['status'],
            'scores':clone(scores),'measurement':clone(measurement),
            'partial_measurement_is_not_completed_loss':w['status']!='complete',
            'system_sha256':digest(w['system'])})
    references=[]
    for label in plan['reference_order']:
        identity='reference-'+label;w=worlds[identity];used.add(identity)
        if w['role']!='developer-reference' or w['status']!='complete' or w['system']!=plan['reference_systems'][label]:
            raise ValueError('reference identity or system differs')
        references.append({'label':label,'physical_job':identity,'scores':clone(w['scores'])})
    slots=[]
    for index,slot in enumerate(plan['schedule']):
        key=slot['arm'],slot['generation'];record=records[key];author=authors[key];request=record['request']
        objective=plan['assignments'][key[0]]['objective']
        if (author['request_sha256']!=record['request_sha256'] or digest(request)!=record['request_sha256']
                or record['definition']!=author['definition'] or record['generation_error']!=author['generation_error']
                or request['generation']!=key[1] or request['loss_spec']!=plan['losses'][objective]
                or author['component_testing']!=traces[key]['component_testing']):
            raise ValueError('literal request, definition or feedback differs')
        observations=[o for o in record['observations'] if o is not None]
        if len(observations)>1:raise ValueError('at most one original native observation per slot')
        row={**clone(slot),'slot_index':index,'objective':objective,'request_sha256':record['request_sha256'],
            'history_sha256':digest(request['history']),'history_records':len(request['history']),
            'generation_error':clone(record['generation_error']),'status':'not-submitted',
            'loss':None,'cross_scores':{k:None for k in plan['losses']},'physical_job':None,
            'changed_paths':None,'connections_changed':None,'schedules_changed':None,
            'nodes_added':None,'nodes_removed':None,'component_trace':clone(traces[key])}
        if observations:
            o=observations[0];identity=o['suggestion_id'];w=worlds[identity]
            if identity in used or (w['role'],w['status'],w['system'],w['scores'][objective])!=(
                    'search:'+key[0],o['status'],o['candidate'],o['loss']):
                raise ValueError('slot and unique physical world differ')
            used.add(identity);base=plan['campaign_bindings']['run-00'][key[0]]['initial_system']
            old={m['mechanism_id'] for m in base['mechanisms']};new={m['mechanism_id'] for m in w['system']['mechanisms']}
            row.update(status=o['status'],loss=o['loss'],cross_scores=clone(w['scores']),physical_job=identity,
                changed_paths=differences(base,w['system']),connections_changed=base['connections']!=w['system']['connections'],
                schedules_changed=base['schedules']!=w['system']['schedules'],nodes_added=sorted(new-old),nodes_removed=sorted(old-new))
        slots.append(row)
    if used!=set(worlds):raise ValueError('unaccounted physical world')
    selections={}
    for arm in plan['arm_order']:
        rows=sorted((r for r in slots if r['arm']==arm and r['status']=='complete' and r['loss'] is not None),key=lambda r:r['generation'])
        best=min((r['loss'] for r in rows),default=None);tied=[r for r in rows if r['loss']==best]
        expected={'loss':best,'all_tied_ids':[r['physical_job'] for r in tied],
            'selected_id':tied[0]['physical_job'] if tied else None,
            'system':worlds[tied[0]['physical_job']]['system'] if tied else None,'completed_submissions':len(rows)}
        if expected!=audit['selection']['selected'][arm]:raise ValueError('frozen selection or all ties differ')
        selections[arm]={k:clone(v) for k,v in expected.items() if k!='system'}
    result={'schema':SCHEMA,'source_commit':plan['source_commit'],'plan_sha256':plan['content_sha256'],
        'audit_sha256':audit['content_sha256'],'score_order':list(plan['objectives']),
        'arm_order':clone(plan['arm_order']),'references':references,'slots':slots,
        'physical_worlds':physical,'frozen_selection':selections,'development_seed_reused':True,
        'interpretation':{'held_out_evaluation':False,'independent_optimizer_replication':False,
            'feedback_superiority_demonstrated':False,'new_model_calls':0,'new_code_executions':0,
            'native_loss_is_scientific_truth':False,'baseline_fallback':False,'publication_ready':False}}
    result['content_sha256']=digest(result);return result


def render(report,output):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    import math
    colors=('#64748b','#956139','#4666ac')
    with plt.rc_context({'font.size':8,'axes.spines.top':False,'axes.spines.right':False,'svg.hashsalt':SCHEMA}):
        fig,axes=plt.subplots(1,2,figsize=(8.2,3.2))
        for ax,arm in zip(axes,report['arm_order']):
            rows=[r for r in report['slots'] if r['arm']==arm];objective=rows[0]['objective'];best=None;path=[]
            for reference,color in zip(report['references'],colors):
                ax.axhline(reference['scores'][objective],lw=1,color=color,ls='--',label=reference['label'])
            for row in rows:
                value=row['loss']
                if value is None:
                    ax.text(row['generation'],.04,'not submitted' if row['physical_job'] is None else 'technical null',
                        transform=ax.get_xaxis_transform(),ha='center',color='#a33b48',fontsize=7)
                else:
                    ax.scatter([row['generation']],[value],s=30,color='#167f78',zorder=3)
                    best=value if best is None else min(best,value)
                path.append(math.nan if best is None else best)
            ax.plot([r['generation'] for r in rows],path,color='#167f78',label='Best completed submitted loss')
            ax.set(title=objective,xlabel='Generation',ylabel='Assigned loss (lower is better)',xticks=[0,1],xlim=(-.4,1.4))
            ax.grid(axis='y',color='#eeeeee');ax.legend(fontsize=6,loc='best')
        fig.suptitle('Code-tested development loop: all four slots, reused seed61001',fontsize=10)
        fig.tight_layout(rect=(0,.01,1,.94))
        for ext in ('png','svg'):fig.savefig(output/('development-loss-paths.'+ext),dpi=200,metadata={'Date':None} if ext=='svg' else None)
        plt.close(fig)
        fig,axes=plt.subplots(2,2,figsize=(8.2,4.4),squeeze=False)
        for ax,row in zip(axes.flat,report['slots']):
            trace=row['component_trace'];counts={}
            for event in trace['events']:
                pair=counts.setdefault(event['step'],[0,0])
                pair[0]+=sum(p['status']=='returned' for p in event['probes'])
                pair[1]+=sum(p['status']=='raised' for p in event['probes'])
                if not event['probes']:ax.text(event['step'],.2,event['test_status'].replace('not-run-',''),
                    rotation=60,ha='left',fontsize=6)
            xs=list(counts);returned=[counts[x][0] for x in xs];raised=[counts[x][1] for x in xs]
            ax.bar(xs,returned,color='#167f78',label='Returned (not native validity)')
            ax.bar(xs,raised,bottom=returned,color='#b44c56',label='Raised')
            ax.set(title=row['objective']+' G'+str(row['generation'])+' / native '+row['status'],
                xlabel='Completed authoring step',ylabel='Fixed-input probes',ylim=(0,5),
                xlim=(-.5,max(trace['completed_steps']-.5,.5)),yticks=[0,2,4])
            ax.legend(fontsize=6,loc='upper left');ax.grid(axis='y',color='#eeeeee')
        fig.suptitle('Actual component observations; unchanged inputs are not new native worlds',fontsize=10)
        fig.tight_layout(rect=(0,0,1,.95))
        for ext in ('png','svg'):fig.savefig(output/('component-observations.'+ext),dpi=200,metadata={'Date':None} if ext=='svg' else None)
        plt.close(fig)


def export(args):
    root=Path(args.run).resolve();output=Path(args.output).resolve()
    paths=[Path(args.audit_one),Path(args.audit_two),root/'plan.json']
    if output.exists() or output.is_relative_to(root):raise ValueError('fresh report outside scientific raw required')
    if paths[0].read_bytes()!=paths[1].read_bytes():raise ValueError('two original-source audits differ')
    before=_inventory(root);audit=checked(json.loads(paths[0].read_text()));plan=checked(json.loads(paths[2].read_text()))
    input_hashes={str(p):file_sha256(p) for p in paths}
    if digest(before)!=audit['raw_inventory_sha256']:raise ValueError('raw inventory differs from cold audit')
    records={};traces={}
    for arm in plan['arm_order']:
        state=json.loads((root/'search/run-00'/arm.replace(':','--')/'campaign/native-adaptive-state.json').read_text())
        if state['pending'] is not None:raise ValueError('pending campaign')
        for index,record in enumerate(state['records']):records[arm,index]=record
    for author in audit['authoring']:
        directory=Path(author['raw_directory']).resolve()
        if not directory.is_relative_to(root):raise ValueError('authoring archive outside audited raw')
        responses=list((directory/'authoring').glob('generation-*/response.json'))
        if len(responses)!=1:raise ValueError('one original staged response required')
        response=checked(json.loads(responses[0].read_text()));inner=responses[0].parent
        steps=[checked(json.loads(p.read_text())) for p in sorted(inner.glob('step-*.completed.json'))]
        key=author['arm'],author['generation'];record=records[key]
        candidate=record['draws'][0]['suggestion']['candidate'] if record['draws'] else None
        traces[key]=component_trace(steps,response,candidate)
    report=summarize(plan,audit,records,traces)
    if before!=_inventory(root) or input_hashes!={str(p):file_sha256(p) for p in paths}:
        raise ValueError('report inputs changed')
    output.mkdir(parents=True);save(output/'report.json',{k:v for k,v in report.items() if k!='content_sha256'})
    render(report,output)
    fields=['slot_index','arm','generation','objective','status','loss','physical_job',
        'connections_changed','schedules_changed','probe_attempts','returned','raised']
    with (output/'slots.csv').open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=fields);writer.writeheader()
        for row in report['slots']:
            writer.writerow({**{k:row[k] for k in fields if k in row},
                **{k:row['component_trace']['component_testing'][k] for k in fields[-3:]}})
    save(output/'manifest.json',{'schema':SCHEMA+'.export','inputs':input_hashes,
        'raw_inventory_sha256':digest(before),'report_content_sha256':report['content_sha256'],
        'files':{p.name:file_sha256(p) for p in sorted(output.iterdir())},
        'new_model_calls':0,'new_code_executions':0})
    print(json.dumps({'slots':len(report['slots']),'physical_worlds':len(report['physical_worlds']),
        'report_content_sha256':report['content_sha256']}))


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('run','audit-one','audit-two','output'):parser.add_argument('--'+name,type=Path,required=True)
    export(parser.parse_args())


if __name__=='__main__':main()
