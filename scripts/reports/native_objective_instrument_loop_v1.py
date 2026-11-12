"""All-slot objective-conditioned development report after matching cold audits."""
import argparse
import csv
import json
from pathlib import Path

from scripts.analyze_native_open_v7 import _inventory
from scripts.run_causal_authoring_assay_v1 import differences
from scripts.reports.native_code_tested_loop_v1 import component_trace
from utopia.optimization.loss import evaluate_loss
from utopia.optimization.native_numeric_designer import checked,save
from utopia.system import SystemSpec
from utopia.system.design_patch import clone,digest
from utopia.utils.data_utils import file_sha256

SCHEMA='scienceutopia.native-objective-instrument-report.v1'


def summarize(plan,audit,records,traces,*,study='count-content-v1'):
    checked(plan);checked(audit)
    if study=='count-content-v1':
        plan_schema='scienceutopia.native-objective-instrument-loop.v1.plan'
        audit_schema='scienceutopia.native-objective-instrument-loop-audit.v1'
        contract_key='observer_contract';count=8;schema=SCHEMA
    elif study=='capacity-v1':
        plan_schema='scienceutopia.native-capacity-objective-loop.v1.plan'
        audit_schema='scienceutopia.native-capacity-objective-loop-audit.v1'
        contract_key='measurement_contract';count=4;schema='scienceutopia.native-capacity-objective-report.v1'
        if plan['objectives']!=['throughput','founder-activity'] or plan['generations']!=2:
            raise ValueError('exact prospective two-objective/four-slot capacity scope required')
    else:raise ValueError('explicit supported development study required')
    if (plan['schema']!=plan_schema or audit['schema']!=audit_schema
            or audit['source_commit']!=plan['source_commit'] or audit['plan_sha256']!=plan['content_sha256']
            or audit['closure']['terminal']['status']!='closed' or audit['held_out_evaluation']
            or audit['source_proof']['status']!='verified-exact-source-closure'
            or audit['new_model_calls'] or audit['new_code_executions']):raise ValueError('matching closed development audit required')
    keys={(s['objective'],s['generation']) for s in plan['schedule']}
    authors={(a['objective'],a['generation']):a for a in audit['authoring']}
    worlds={w['identity']:w for w in audit['worlds']}
    if (len(keys)!=count or len(keys)!=len(plan['schedule']) or set(records)!=keys or set(traces)!=keys
            or set(authors)!=keys or len(authors)!=len(audit['authoring']) or len(worlds)!=len(audit['worlds'])):
        raise ValueError('exact scheduled slots and unique author/world identities required')
    observations={p['suggestion']['suggestion_id']:p['observation'] for p in audit['developer_references']['pairs']}
    for r in records.values():
        for o in r['observations']:
            if o is not None:
                if o['suggestion_id'] in observations:raise ValueError('duplicate native observation')
                observations[o['suggestion_id']]=o
    if set(observations)!=set(worlds):raise ValueError('unaccounted original native world/observation')
    physical=[]
    for identity,w in worlds.items():
        o=observations[identity];measurements=o['metadata']['measurements'];base=w['physical_proof'].get('measurement')
        if o['status']!=w['status'] or o['candidate']!=w['system']:raise ValueError('physical observation identity differs')
        if measurements:
            if len(measurements)!=1 or base is None:raise ValueError('unique physically completed world required')
            m=measurements[0]
            if (m['system_fingerprint']!=SystemSpec.from_dict(w['system']).fingerprint
                    or m.get('measurement_adapter_contract_sha256')!=digest(plan[contract_key])
                    or any(m.get(k)!=v for k,v in base.items() if k!='metrics')
                    or any(m['metrics'].get(k)!=v for k,v in base['metrics'].items())):
                raise ValueError('original base or additional measurement binding differs')
        scores={k:evaluate_loss(v,measurements)['loss'] for k,v in plan['losses'].items()}
        if scores!=w['scores']:raise ValueError('literal additional criterion cross-score differs')
        physical.append({'identity':identity,'role':w['role'],'seed':w['seed'],'status':w['status'],
            'scores':scores,'measurements':clone(measurements),'system_sha256':digest(w['system']),
            'partial_base_measurement_is_not_completed_loss':w['status']!='complete'})
    used=set();references=[]
    for label in plan['reference_order']:
        identity='reference-'+label;w=worlds[identity];used.add(identity)
        if w['role']!='developer-reference' or w['status']!='complete' or w['system']!=plan['reference_systems'][label]:
            raise ValueError('common reference differs')
        references.append({'label':label,'physical_job':identity,'scores':clone(w['scores'])})
    slots=[]
    for index,s in enumerate(plan['schedule']):
        key=s['objective'],s['generation'];r=records[key];a=authors[key];request=r['request'];trace=traces[key]
        if (a['request_sha256']!=r['request_sha256'] or digest(request)!=r['request_sha256']
                or a['definition']!=r['definition'] or a['generation_error']!=r['generation_error']
                or request['generation']!=key[1] or request['loss_spec']!=plan['losses'][key[0]]
                or a['component_testing']!=trace['component_testing']):raise ValueError('actual author request/definition/trace differs')
        summary=request['developer_reference_context']
        if summary['context_sha256']!=audit['developer_references']['content_sha256']:
            raise ValueError('different common reference context')
        parent=request['parent_system'];anchor=plan['initial_system']
        parent_ids=[v['suggestion']['suggestion_id'] for v in request['observations'] if v['suggestion']['candidate']==parent]
        row={**clone(s),'slot_index':index,'request_sha256':r['request_sha256'],
            'parent_system_sha256':digest(parent),'parent_matching_observation_ids':parent_ids,
            'parent_differs_from_design_anchor':parent!=anchor,'history_records':len(request['history']),
            'common_reference_context_sha256':summary['context_sha256'],
            'generation_error':clone(r['generation_error']),'status':'not-submitted','physical_job':None,
            'loss':None,'cross_scores':{k:None for k in plan['losses']},'changed_paths_from_parent':None,
            'changed_paths_from_anchor':None,'connections_changed':None,'schedules_changed':None,
            'nodes_added':None,'nodes_removed':None,'component_trace':clone(trace)}
        values=[o for o in r['observations'] if o is not None]
        if len(values)>1:raise ValueError('at most one original observation per own slot')
        if values:
            o=values[0];identity=o['suggestion_id'];w=worlds[identity]
            if identity in used or w['role']!='search:'+key[0] or o['loss']!=w['scores'][key[0]]:
                raise ValueError('slot does not identify unique original own world')
            used.add(identity);system=w['system'];old={m['mechanism_id'] for m in parent['mechanisms']};new={m['mechanism_id'] for m in system['mechanisms']}
            row.update(status=o['status'],physical_job=identity,loss=o['loss'],cross_scores=clone(w['scores']),
                changed_paths_from_parent=differences(parent,system),changed_paths_from_anchor=differences(anchor,system),
                connections_changed=parent['connections']!=system['connections'],schedules_changed=parent['schedules']!=system['schedules'],
                nodes_added=sorted(new-old),nodes_removed=sorted(old-new))
        elif r['generation_error'] is not None:row['status']='generation-failure'
        slots.append(row)
    if used!=set(worlds):raise ValueError('unaccounted native world')
    selections={}
    for objective in plan['objectives']:
        rows=sorted((r for r in slots if r['objective']==objective and r['status']=='complete' and r['loss'] is not None),key=lambda r:r['generation'])
        best=min((r['loss'] for r in rows),default=None);ties=[r['physical_job'] for r in rows if r['loss']==best]
        expected={'loss':best,'all_tied_ids':ties,'selected_id':ties[0] if ties else None,
            'system':worlds[ties[0]]['system'] if ties else None,'completed_submissions':len(rows)}
        if expected!=audit['selection']['selected'][objective]:raise ValueError('frozen own-submission selection differs')
        selections[objective]={k:clone(v) for k,v in expected.items() if k!='system'}
        selections[objective]['loss_minus_each_reference']={r['label']:None if best is None else best-r['scores'][objective] for r in references}
    result={'schema':schema,'source_commit':plan['source_commit'],'plan_sha256':plan['content_sha256'],
        'audit_sha256':audit['content_sha256'],'score_order':clone(plan['objectives']),'references':references,
        'slots':slots,'physical_worlds':physical,'frozen_selection':selections,
        'interpretation':{'development_seed_reused':True,'identical_first_editing_parent_control':False,
            'independent_optimizer_replication':False,'held_out_evaluation':False,'scientific_truth':False,
            'new_model_calls':0,'new_code_executions':0,'publication_ready':False}}
    result['content_sha256']=digest(result);return result


def cross_score_groups(report):
    """Group exact coordinates for display without jittering or dropping ties."""
    rows=[{'label':'R'+str(i+1),'scores':r['scores']} for i,r in enumerate(report['references'])]
    second=report['score_order'][1];letter='P' if second=='founder-activity' else 'U'
    rows.extend({'label':('T' if r['objective']=='throughput' else letter)+str(r['generation']),
        'scores':r['cross_scores']} for r in report['slots'])
    by={};unavailable=[]
    for r in rows:
        coordinate=tuple(r['scores'][o] for o in report['score_order'])
        if any(v is None for v in coordinate):unavailable.append(r['label'])
        else:by.setdefault(coordinate,[]).append(r['label'])
    return ([{'group':'G'+str(i+1),'T':point[0],letter:point[1],'labels':labels}
        for i,(point,labels) in enumerate(sorted(by.items()))],unavailable)


def render(report,output):
    import math
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    colors=['#596b84','#b47835','#9c5d8a','#a9444a','#75914a']
    letter='P' if report['score_order'][1]=='founder-activity' else 'U'
    with plt.rc_context({'font.size':8,'axes.spines.top':False,'axes.spines.right':False,'svg.hashsalt':report['schema']}):
        fig,axes=plt.subplots(1,2,figsize=(9,3.7))
        for ax,objective in zip(axes,report['score_order']):
            for reference,color in zip(report['references'],colors):
                ax.axhline(reference['scores'][objective],color=color,lw=.9,ls='--',label=reference['label'])
            rows=[r for r in report['slots'] if r['objective']==objective];path=[];best=None
            for r in rows:
                if r['loss'] is None:ax.text(r['generation'],.02,'null',transform=ax.get_xaxis_transform(),ha='center',color='#a9444a')
                else:
                    ax.scatter(r['generation'],r['loss'],s=30,color='#087f8c',zorder=3)
                    best=r['loss'] if best is None else min(best,r['loss'])
                path.append(math.nan if best is None else best)
            ax.plot([r['generation'] for r in rows],path,color='#087f8c',label='Best submitted loss')
            generations=[r['generation'] for r in rows]
            ax.set(title=objective,xlabel='Proposal generation',ylabel='Assigned loss (lower is better)',
                xticks=generations,xlim=(-.3,max(generations)+.3))
            ax.grid(axis='y',color='#ededed');ax.legend(fontsize=5.8,loc='best')
        count='eight' if len(report['slots'])==8 else str(len(report['slots']))
        fig.suptitle('Objective-conditioned native development: all '+count+' slots, reused seed61001',fontsize=10)
        fig.tight_layout(rect=(0,0,1,.94))
        for ext in ('png','svg'):fig.savefig(output/('objective-loss-paths.'+ext),dpi=200,metadata={'Date':None} if ext=='svg' else None)
        plt.close(fig)
        fig,(ax,key)=plt.subplots(1,2,figsize=(10,4.7),gridspec_kw={'width_ratios':[1,.95]})
        groups,unavailable=cross_score_groups(report)
        for group in groups:
            ax.scatter(group['T'],group[letter],marker='o',s=45,color='#087f8c',zorder=3)
            ax.annotate(group['group'],(group['T'],group[letter]),xytext=(5,5),textcoords='offset points',fontsize=8)
        ylabel='Founder-activity loss P (lower is better)' if letter=='P' else 'Content utility loss U (lower is better)'
        ax.set(xlabel='Count loss T (lower is better)',ylabel=ylabel,
            title='Exact coordinates; all tied labels retained')
        from matplotlib.ticker import MaxNLocator
        ax.xaxis.set_major_locator(MaxNLocator(integer=True))
        if len({g['T'] for g in groups})==1:ax.set_xlim(groups[0]['T']-.5,groups[0]['T']+.5)
        if len({g[letter] for g in groups})==1:ax.set_ylim(groups[0][letter]-.5,groups[0][letter]+.5)
        ax.grid(color='#ededed');key.axis('off')
        import textwrap
        cells=[[g['group'],f"{g['T']:g}",f"{g[letter]:g}",textwrap.fill(', '.join(g['labels']),30)] for g in groups]
        if cells:
            heights=[.065]+[.065+.032*(len(c[3].splitlines())-1) for c in cells]
            height=min(.70,sum(heights))
            table=key.table(cellText=cells,colLabels=['Point','T',letter,'World labels'],
                colWidths=[.13,.15,.15,.57],bbox=(0,1-height,1,height),cellLoc='left')
            table.auto_set_font_size(False);table.set_fontsize(7)
            for (i,j),cell in table.get_celld().items():
                cell.set_edgecolor('#d8dee5');cell.set_linewidth(.5)
                cell.set_height(heights[i])
                if i==0:cell.set_facecolor('#edf2f5')
        reference_key='\n'.join(textwrap.fill('R'+str(i+1)+' = '+r['label'],70) for i,r in enumerate(report['references']))
        footer=reference_key+'\nT/'+letter+' labels = own-objective proposal generation; no coordinate jitter.'
        if unavailable:footer+='\nUnavailable cross-score: '+', '.join(unavailable)
        fig.text(.53,.04,footer,ha='left',va='bottom',fontsize=6.5,linespacing=1.35)
        fig.suptitle('Both fixed criteria on the same completed native worlds',fontsize=10)
        fig.tight_layout(rect=(0,.04,1,.94))
        for ext in ('png','svg'):fig.savefig(output/('objective-cross-scores.'+ext),dpi=200,metadata={'Date':None} if ext=='svg' else None)
        plt.close(fig)


def export(args,*,study='count-content-v1'):
    root=Path(args.run).resolve();output=Path(args.output).resolve();paths=[Path(args.audit_one),Path(args.audit_two),root/'plan.json']
    if output.exists() or output.is_relative_to(root):raise ValueError('fresh report outside scientific raw required')
    if paths[0].read_bytes()!=paths[1].read_bytes():raise ValueError('two original-source audits differ')
    before=_inventory(root);audit=checked(json.loads(paths[0].read_text()));plan=checked(json.loads(paths[2].read_text()))
    input_hashes={str(p):file_sha256(p) for p in paths}
    if digest(before)!=audit['raw_inventory_sha256']:raise ValueError('raw inventory differs from independent audit')
    records={};traces={}
    for objective in plan['objectives']:
        state=json.loads((root/'search'/objective/'campaign/native-adaptive-state.json').read_text())
        if state['pending'] is not None:raise ValueError('pending campaign')
        for g,r in enumerate(state['records']):records[objective,g]=r
    for a in audit['authoring']:
        directory=Path(a['raw_directory']).resolve()
        if not directory.is_relative_to(root):raise ValueError('authoring archive outside audited raw')
        responses=list((directory/'authoring').glob('generation-*/response.json'));key=a['objective'],a['generation']
        if len(responses)>1:raise ValueError('ambiguous staged terminal')
        if responses:
            response=checked(json.loads(responses[0].read_text()));inner=responses[0].parent
            steps=[checked(json.loads(p.read_text())) for p in sorted(inner.glob('step-*.completed.json'))]
            r=records[key];candidate=r['draws'][0]['suggestion']['candidate'] if r['draws'] and r['draws'][0]['suggestion'] else None
            traces[key]=component_trace(steps,response,candidate)
        else:
            if a['component_testing'] is not None or a['generation_error'] is None:raise ValueError('missing terminal without retained generation failure')
            traces[key]={'component_testing':None,'terminal_response_missing':True,
                'events':[],'completed_steps':None,'drawn_candidate_artifact_observations':None}
    report=summarize(plan,audit,records,traces,study=study)
    if before!=_inventory(root) or input_hashes!={str(p):file_sha256(p) for p in paths}:raise ValueError('raw report inputs changed')
    output.mkdir(parents=True);save(output/'report.json',{k:v for k,v in report.items() if k!='content_sha256'});render(report,output)
    fields=['slot_index','objective','generation','status','loss','physical_job','parent_differs_from_design_anchor',
        'connections_changed','schedules_changed','probe_attempts','returned','raised']
    with (output/'slots.csv').open('x',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        for r in report['slots']:
            component=r['component_trace']['component_testing']
            w.writerow({**{k:r[k] for k in fields if k in r},**{k:None if component is None else component[k] for k in fields[-3:]}})
    save(output/'manifest.json',{'schema':report['schema']+'.export','inputs':input_hashes,'raw_inventory_sha256':digest(before),
        'report_content_sha256':report['content_sha256'],'files':{p.name:file_sha256(p) for p in sorted(output.iterdir())},
        'new_model_calls':0,'new_code_executions':0})
    print(json.dumps({'slots':len(report['slots']),'physical_worlds':len(report['physical_worlds']),
        'report_content_sha256':report['content_sha256']}))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('run','audit-one','audit-two','output'):p.add_argument('--'+key,type=Path,required=True)
    export(p.parse_args())


if __name__=='__main__':main()
