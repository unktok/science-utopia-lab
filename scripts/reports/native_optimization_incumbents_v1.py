"""Best-known and best-own development trajectories from closed report pairs.

Read-only projection, not a new raw audit, optimizer, candidate selection file
or evaluator. Reference-first ties preserve all IDs and missing own outcomes.
"""
import argparse
import csv
import json
import math
from pathlib import Path

from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked,save
from utopia.system.design_patch import clone,digest
from utopia.system.native_planning_controls import ORDER
from utopia.utils.data_utils import file_sha256

ROOT=Path(__file__).resolve().parents[2]
SCHEMA='scienceutopia.native-optimization-incumbents.v1'
SCOPES={'scienceutopia.native-planning-objective-report.v1':'planning',
    'scienceutopia.native-parent-presentation-report.v1':'presentation',
    'scienceutopia.native-parameter-comparator-report.v1':'numeric'}
OBJECTIVES=['throughput','content-utility']


def finite(value):
    return type(value) in (int,float) and math.isfinite(value)


def pool_view(references,rows,objective):
    common=[{'identity':r['identity'],'loss':r['scores'][objective],'origin':'reference'} for r in references]
    own=[{'identity':r['identity'],'loss':r['loss'],'origin':'own'} for r in rows if r['status']=='complete']
    def best(pool):
        loss=min((r['loss'] for r in pool),default=None)
        ties=[r for r in pool if r['loss']==loss]
        return {'loss':loss,'identity':ties[0]['identity'] if ties else None,
            'origin':ties[0]['origin'] if ties else None,'all_tied_ids':[r['identity'] for r in ties]}
    ref=best(common);known=best(common+own);generated=best(own)
    return {'best_known':known,'best_own':generated,'best_reference':ref,
        'completed_own':len(own),'own_improvement_over_reference':None if not own else ref['loss']-generated['loss'],
        'known_improvement_over_reference':ref['loss']-known['loss']}


def summarize(original):
    checked(original);scope=SCOPES.get(original.get('schema'))
    if scope is None:raise ValueError('explicit supported closed development report required')
    if (not isinstance(original['source_commit'],str) or len(original['source_commit'])!=40
            or any(c not in '0123456789abcdef' for c in original['source_commit'])
            or not isinstance(original['plan_sha256'],str) or len(original['plan_sha256'])!=64
            or any(c not in '0123456789abcdef' for c in original['plan_sha256'])):
        raise ValueError('literal original source/plan hashes required')
    objectives=original['objectives'] if scope=='numeric' else original['score_order']
    if objectives!=OBJECTIVES or len(original['references'])!=8:
        raise ValueError('both literal objectives and all eight common references required')
    references=[]
    for label,row in zip(ORDER,original['references']):
        identity=row['identity'] if scope=='numeric' else row['physical_job']
        if ((scope!='numeric' and row['label']!=label) or identity!='reference-'+label
                or set(row['scores'])!=set(OBJECTIVES) or not all(finite(v) for v in row['scores'].values())):
            raise ValueError('literal ordered complete common reference scores required')
        references.append({'label':label,'identity':identity,'scores':clone(row['scores'])})
    if scope=='presentation':
        from scripts.run_native_parent_presentation_loop_v1 import ARM_ORDER
        order=list(ARM_ORDER)
        if original['arm_order']!=order or set(original['arms'])!=set(order) or len(original['slots'])!=12:
            raise ValueError('complete four-arm presentation report required')
        if any(original['arms'][key]['objective']!=key.rsplit('-',1)[0] for key in order):
            raise ValueError('literal objective for each presentation arm required')
        objective_for=lambda key:original['arms'][key]['objective']
        rows_for=lambda key:[r for r in original['slots'] if r['arm']==key]
        selection=original['frozen_selection']
    elif scope=='numeric':
        if (len(original['slots'])!=12 or original['held_out_evaluation']
                or original['new_numeric_slots']!=6 or original['reused_free_slots']!=6):
            raise ValueError('complete six-new/six-reused numeric report required')
        order=list(OBJECTIVES);objective_for=lambda key:key
        rows_for=lambda key:[r for r in original['slots'] if r['method']=='numeric-reserve' and r['objective']==key]
        frozen=checked(original['numeric_selection'])
        if (frozen['plan_sha256']!=original['plan_sha256'] or frozen['baseline_fallback'] or frozen['held_out_evaluation']):
            raise ValueError('unchanged numeric own-only selection required')
        selection=frozen['selected']
        if len([r for r in original['slots'] if r['method']=='prior-free-program'])!=6:
            raise ValueError('all reused prior slots retained, not additional histories')
        for objective in OBJECTIVES:
            prior=[r for r in original['slots'] if r['method']=='prior-free-program' and r['objective']==objective]
            if (len(prior)!=3 or any(type(r['generation']) is not int for r in prior)
                    or {r['generation'] for r in prior}!={0,1,2}):
                raise ValueError('all reused prior generations retained, not newly optimized')
    else:
        if len(original['slots'])!=6:raise ValueError('all six planning slots required')
        order=list(OBJECTIVES);objective_for=lambda key:key
        rows_for=lambda key:[r for r in original['slots'] if r['objective']==key]
        selection=original['frozen_selection']
    if set(selection)!=set(order):raise ValueError('original own-selection keys differ')
    histories=[];used=0
    for key in order:
        objective=objective_for(key)
        if objective not in OBJECTIVES:raise ValueError('declared assigned objective required')
        raw=rows_for(key)
        if (len(raw)!=3 or any(type(r['generation']) is not int for r in raw)
                or {r['generation'] for r in raw}!={0,1,2}):
            raise ValueError('exact three consumed chronological own slots required')
        rows=[]
        for row in sorted(raw,key=lambda r:r['generation']):
            loss=row['assigned_loss'] if scope=='numeric' else row['loss']
            scores=row['scores'] if scope=='numeric' else row['cross_scores']
            identity=row['identity'] if scope=='numeric' else row['physical_job']
            if (row['objective']!=objective or set(scores)!=set(OBJECTIVES)
                    or any(v is not None and not finite(v) for v in scores.values())
                    or identity is not None and (not isinstance(identity,str) or not identity)):
                raise ValueError('slot objective/cross-score/identity differs')
            if row['status']=='complete':
                if not finite(loss) or loss!=scores[objective] or not isinstance(identity,str) or not identity:
                    raise ValueError('complete own slot requires literal finite loss and identity')
                if identity in {r['identity'] for r in references}:raise ValueError('reference cannot be relabelled an own submission')
            elif (row['status'] not in ('failed','invalid','not-submitted','generation-failure','generation-null')
                    or loss is not None or scores[objective] is not None):
                raise ValueError('technical/null slot cannot acquire a numerical loss')
            rows.append({'generation':row['generation'],'status':row['status'],'loss':loss,'identity':identity})
        ids=[r['identity'] for r in rows if r['identity'] is not None]
        if len(ids)!=len(set(ids)):raise ValueError('own identities must be unique within each history')
        final=pool_view(references,rows,objective);own=selection[key]
        if (type(own['completed_submissions']) is not int or not isinstance(own['all_tied_ids'],list)
                or own['loss'] is not None and not finite(own['loss'])):
            raise ValueError('literal original own-selection count/loss/ties required')
        expected={'loss':final['best_own']['loss'],'selected_id':final['best_own']['identity'],
            'all_tied_ids':final['best_own']['all_tied_ids'],'completed_submissions':final['completed_own']}
        if any(own[k]!=v for k,v in expected.items()):raise ValueError('original earliest-tied own selection differs')
        if scope=='numeric':
            anchor=original['anchors'][objective]
            if anchor['identity']!=final['best_reference']['identity'] or anchor['loss']!=final['best_reference']['loss']:
                raise ValueError('numeric warm-start reference differs from its declared common minimum')
        path=[{'generation':-1,'consumed_slots':0,'slot_status':'before-own-proposals','slot_identity':None,'slot_loss':None,
            **pool_view(references,[],objective)}]
        for i,row in enumerate(rows):
            path.append({'generation':row['generation'],'consumed_slots':i+1,'slot_status':row['status'],
                'slot_identity':row['identity'],'slot_loss':row['loss'],**pool_view(references,rows[:i+1],objective)})
        histories.append({'history':key,'objective':objective,'source_scope':scope,
            'original_own_selection':{k:clone(own[k]) for k in expected},'path':path,'final':final})
        used+=len(rows)
    if used!=(6 if scope=='numeric' else len(original['slots'])):raise ValueError('unaccounted own rows')
    return {'schema':SCHEMA,'input_report_schema':original['schema'],
        'input_report_content_sha256':original['content_sha256'],'scientific_source_commit':original['source_commit'],
        'input_plan_sha256':original['plan_sha256'],'scope':scope,'score_order':OBJECTIVES,
        'input_audit_hashes':{k:original[k] for k in ('audit_sha256','numeric_audit_sha256','original_audit_sha256') if k in original},
        'references':references,'history_order':order,'histories':histories,
        'common_reference_worlds':8,'common_reference_bank_reused':scope=='numeric',
        'reused_prior_free_slots_are_not_new_histories':6 if scope=='numeric' else 0,
        'interpretation':{'original_selection_changed':False,'raw_audit_reexecuted':False,
            'best_known_is_optimization_readout_not_invention':True,'missing_own_loss_imputed':False,
            'reference_first_ties_with_all_ids_retained':True,'new_model_calls':0,'new_native_worlds':0,
            'independent_optimizer_replications':False,'held_out_reselection':False,'global_optimum_claimed':False,
            'scientific_truth_claimed':False,'publication_ready':False}}


def render(report,output,*,software_qa=False):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    with plt.rc_context({'font.size':8,'svg.hashsalt':SCHEMA,'axes.spines.top':False,'axes.spines.right':False}):
        fig,axes=plt.subplots(1,2,figsize=(10.5,4.8))
        for ax,objective,title in zip(axes,OBJECTIVES,['Count objective T','Content objective U']):
            histories=[h for h in report['histories'] if h['objective']==objective]
            for i,h in enumerate(histories):
                color=({'control':'#087f8c','literal':'#b47835'}[h['history'].rsplit('-',1)[1]]
                    if report['scope']=='presentation' else '#087f8c')
                rows=h['path'];x=[r['consumed_slots'] for r in rows]
                label=h['history']
                ax.plot(x,[r['best_known']['loss'] for r in rows],color=color,lw=1.8,marker='s',
                    markerfacecolor='none',markersize=7,label=label+': best known')
                ax.plot(x,[math.nan if r['best_own']['loss'] is None else r['best_own']['loss'] for r in rows],
                    color=color,lw=.9,ls=':',marker='o',markersize=3,label=label+': best own')
                for row in rows[1:]:
                    if row['slot_loss'] is None:
                        ax.text(row['consumed_slots'],.03+i*.08,'null',transform=ax.get_xaxis_transform(),ha='center',color=color,fontsize=7)
                if all(row['best_own']['loss'] is None for row in rows):
                    ax.text(.02,.92-i*.08,label+': no completed own proposal',transform=ax.transAxes,fontsize=7,color=color)
            ax.set(title=title,xlabel='Consumed own slots (0: common bank only)',ylabel='Assigned loss; lower is better',
                xticks=[0,1,2,3],xlim=(-.2,3.2));ax.grid(axis='y',color='#ededed');ax.legend(fontsize=6.5)
        fig.suptitle('Best-known optimization performance versus best generated submission',fontsize=10)
        fig.text(.05,.025,'References are eligible only for best-known readout; original own-only selections and every null remain unchanged. '
            'Equal values overlap.',fontsize=6.8)
        fig.tight_layout(rect=(0,.06,1,.94))
        if software_qa:fig.text(.5,.5,'SCRIPTED SOFTWARE QA',ha='center',rotation=25,fontsize=28,color='#a9444a',alpha=.18)
        for ext in ('png','svg'):
            fig.savefig(output/('optimization-incumbents.'+ext),dpi=200,metadata={'Date':None} if ext=='svg' else None)
        plt.close(fig)


def export(args):
    inputs=[Path(args.report_one).resolve(),Path(args.report_two).resolve()];output=Path(args.output).resolve()
    if (inputs[0]==inputs[1] or output.exists() or any(output.is_relative_to(p.parent) for p in inputs)
            or inputs[0].read_bytes()!=inputs[1].read_bytes()):
        raise ValueError('two distinct matching closed report files and fresh separate output required')
    source=pinned_revision(ROOT);hashes={str(p):file_sha256(p) for p in inputs}
    report=summarize(checked(json.loads(inputs[0].read_text())))
    report.update(analysis_source_commit=source,analysis_adapter_sha256=file_sha256(Path(__file__)),
        software_qa_plot=bool(getattr(args,'software_qa',False)))
    output.mkdir(parents=True);saved=save(output/'report.json',report)
    fields=['history','objective','generation','consumed_slots','slot_status','slot_identity','slot_loss','best_known_loss','best_known_id',
        'best_known_origin','best_known_tied_ids','best_own_loss','best_own_id','best_own_tied_ids','completed_own',
        'own_improvement_over_reference','known_improvement_over_reference']
    with (output/'paths.csv').open('x',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields);writer.writeheader()
        for h in report['histories']:
            for row in h['path']:
                writer.writerow({'history':h['history'],'objective':h['objective'],
                    **{k:row[k] for k in ('generation','consumed_slots','slot_status','slot_identity','slot_loss','completed_own',
                        'own_improvement_over_reference','known_improvement_over_reference')},
                    'best_known_loss':row['best_known']['loss'],'best_known_id':row['best_known']['identity'],
                    'best_known_origin':row['best_known']['origin'],'best_known_tied_ids':json.dumps(row['best_known']['all_tied_ids']),
                    'best_own_loss':row['best_own']['loss'],'best_own_id':row['best_own']['identity'],
                    'best_own_tied_ids':json.dumps(row['best_own']['all_tied_ids'])})
    render(report,output,software_qa=report['software_qa_plot'])
    if hashes!={str(p):file_sha256(p) for p in inputs} or pinned_revision(ROOT)!=source:
        raise ValueError('input reports or analysis source changed')
    save(output/'manifest.json',{'schema':SCHEMA+'.export','inputs':hashes,'analysis_source_commit':source,
        'analysis_adapter_sha256':file_sha256(Path(__file__)),'report_content_sha256':saved['content_sha256'],
        'files':{p.name:file_sha256(p) for p in sorted(output.iterdir())},'new_model_calls':0,'new_native_worlds':0})
    print(json.dumps({'output':str(output),'histories':len(report['histories']),
        'report_content_sha256':saved['content_sha256'],'original_selection_changed':False}),flush=True)
    return saved


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('report-one','report-two','output'):parser.add_argument('--'+key,type=Path,required=True)
    parser.add_argument('--software-qa',action='store_true');export(parser.parse_args())


if __name__=='__main__':main()
