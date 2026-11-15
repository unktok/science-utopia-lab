"""All six objective-conditioned slots and literal T/U/C/K, after cold closure.

No model, generated program, physical world, policy repair or reselection is
invoked. The outer entry imports original scientific decoders in its child.
"""
import argparse
import csv
import json
import math
import os
from pathlib import Path
import sqlite3
import subprocess
import sys

from scripts.analyze_native_open_v7 import _inventory
from scripts.reports.native_code_tested_loop_v1 import component_trace
from scripts.reports.native_institution_effect_trace_v1 import trace_world
from scripts.reports.native_observed_request_classes_v1 import sequence, groups
from scripts.reports.native_workflow_objective_loop_v1 import graph_change
from utopia.optimization.blackbox import Observation
from utopia.optimization.loss import evaluate_loss, loss_spec_sha256
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.optimization.native_resource_cost import METRIC, UNCOLLECTED_METRIC
from utopia.optimization.native_topic_objectives_v1 import OBJECTIVES
from utopia.system import SystemSpec
from utopia.system.design_patch import clone, digest
from utopia.utils.data_utils import file_sha256

ROOT=Path(__file__).resolve().parents[2]
SCHEMA='scienceutopia.native-topic-free-readout.v1'
METRICS=('native.accepted_decisions','native.common_content_utility_sum',METRIC,UNCOLLECTED_METRIC)


def literal_metrics(measurements):
    if not isinstance(measurements,list) or len(measurements)>1:
        raise ValueError('one original declared world measurement or retained unknown required')
    if not measurements:
        return {key:{'status':'measurement-not-recorded','value':None} for key in METRICS}
    raw=measurements[0]['metrics']
    return {key:clone(raw.get(key,{'status':'metric-not-recorded','value':None})) for key in METRICS}


def analyze(plan,audit,records,observations):
    """Pure projection of all declared records; no observed row is filtered."""
    if (plan['schema']!='scienceutopia.native-topic-free-optimization.v1.plan'
            or audit['schema']!='scienceutopia.native-topic-free-optimization.v1.audit'
            or plan['objectives']!=list(OBJECTIVES) or plan['generations']!=2
            or plan['design_space']['world_law_scope']!='fixed-native-effects-institution-workflow-v6'
            or audit['source_commit']!=plan['source_commit'] or audit['plan_sha256']!=plan['content_sha256']
            or audit['closure']['terminal']['status']!='closed'
            or audit['source_proof']['status']!='verified-exact-source-closure'
            or audit['new_model_calls'] or audit['new_code_executions'] or audit['held_out_evaluation']
            or audit['selection']['baseline_fallback'] or audit['selection'].get('held_out_evaluation',False)):
        raise ValueError('exact normally closed six-slot v6 original audit required')
    expected=[(s['objective'],s['generation']) for s in plan['schedule']]
    if len(expected)!=6 or len(set(expected))!=6 or set(records)!=set(expected):
        raise ValueError('all six declared original slots required, including nulls')
    worlds={w['identity']:w for w in audit['worlds']}
    if len(worlds)!=len(audit['worlds']) or set(worlds)!=set(observations):
        raise ValueError('all and only actual audited world observations required')
    def outcome(identity,objective):
        world=worlds[identity]; o=Observation.from_dict(observations[identity]).to_dict(); m=o['metadata']
        scores={key:evaluate_loss(loss,m['measurements']) for key,loss in plan['losses'].items()}
        if (o['suggestion_id']!=identity or o['candidate']!=world['system'] or o['status']!=world['status']
                or o['loss']!=scores[objective]['loss'] or scores[objective]!=m['loss_evaluation']
                or m['loss_spec_sha256']!=loss_spec_sha256(plan['losses'][objective])
                or m['system_fingerprint']!=SystemSpec.from_dict(world['system']).fingerprint
                or world['scores']!={key:value['loss'] for key,value in scores.items()}
                or (o['status']=='complete')!=(scores[objective]['status']=='complete')):
            raise ValueError('literal original outcome/assigned loss/metric identity differs')
        measured=m['measurements']
        return {'physical_job':identity,'status':o['status'],'cross_scores':clone(world['scores']),
            'metrics':literal_metrics(measured),'measurement_sha256s':[digest(v) for v in measured],
            'technical_failures':clone(m['technical_failures']),
            'institutional_work_events':None if not measured else
                measured[0]['native_workflow_interval']['institutional_work_events']}
    references=[]; used=set()
    for label in plan['reference_order']:
        identity='workflow-reference-'+label.lower(); world=worlds[identity]
        if (world['role']!='developer-reference' or world['status']!='complete'
                or world['system']!=plan['reference_systems'][label]):
            raise ValueError('complete literal strong same-authority reference required')
        used.add(identity)
        references.append({'label':label,'optimizer_visible':label in plan['optimizer_reference_labels'],
            **outcome(identity,'throughput')})
    slots=[]
    for index,(objective,generation) in enumerate(expected):
        r=records[objective,generation]; request=r['request']
        if (request['generation']!=generation or request['loss_spec']!=plan['losses'][objective]
                or r['request_sha256']!=digest(request) or len(r['observations'])>1
                or len(r['draws'])!=len(r['observations'])):
            raise ValueError('exact literal objective slot request/observation required')
        row={'slot_index':index,'objective':objective,'generation':generation,'status':'generation-null',
            'request_sha256':r['request_sha256'],'parent_system_sha256':digest(request['parent_system']),
            'based_on_observation_id':request.get('based_on_observation_id'),
            'generation_error':clone(r['generation_error']),'physical_job':None,'loss':None,
            'cross_scores':{key:None for key in OBJECTIVES},'metrics':literal_metrics([]),
            'graph_from_parent':None,'graph_from_anchor':None,'literal_system_changed':None,
            'technical_failures':[],'institutional_work_events':None}
        if r['observations'] and r['observations'][0] is not None:
            o=r['observations'][0]; identity=o['suggestion_id']; w=worlds[identity]
            suggestion=r['draws'][0]['suggestion']
            if (identity in used or w['role']!='workflow-own-proposal' or w['objective']!=objective
                    or suggestion is None or suggestion['candidate']!=o['candidate']):
                raise ValueError('actual audited own world and objective slot differ')
            used.add(identity)
            row.update(outcome(identity,objective),loss=o['loss'],
                literal_system_changed=request['parent_system']!=w['system'],
                graph_from_parent=graph_change(request['parent_system'],w['system'],allow_institution_edits=True),
                graph_from_anchor=graph_change(plan['initial_system'],w['system'],allow_institution_edits=True))
        elif r['generation_error'] is None and not any(d.get('technical_error') for d in r['draws']):
            raise ValueError('missing outcome requires its retained original technical null')
        slots.append(row)
    if used!=set(worlds): raise ValueError('unaccounted audited world')
    paths={}
    for objective in OBJECTIVES:
        own=None; known=min(r['cross_scores'][objective] for r in references if r['optimizer_visible'])
        path=[]; rows=[r for r in slots if r['objective']==objective]
        for row in rows:
            if row['status']=='complete':
                own=row['loss'] if own is None else min(own,row['loss']); known=min(known,row['loss'])
            path.append({'generation':row['generation'],'status':row['status'],'observed_loss':row['loss'],
                         'best_own_loss':own,'best_known_loss_including_visible_references':known})
        ties=[r['physical_job'] for r in rows if r['status']=='complete' and r['loss']==own]
        selected=audit['selection']['selected'][objective]
        if (selected['loss']!=own or selected['all_tied_ids']!=ties
                or selected['selected_id']!=(ties[0] if ties else None)
                or selected['system']!=(worlds[ties[0]]['system'] if ties else None)):
            raise ValueError('original own-only selection differs; no reference substitution')
        paths[objective]=path
    return {'schema':SCHEMA,'scientific_source_commit':plan['source_commit'],
        'plan_sha256':plan['content_sha256'],'audit_content_sha256':audit['content_sha256'],
        'score_order':list(OBJECTIVES),'loss_specs':clone(plan['losses']),'references':references,
        'slots':slots,'loss_paths':paths,'selection':clone(audit['selection']),
        'physical_worlds':len(worlds),'consumed_own_slots':len(slots),
        'interpretation':{'development_seed_reused':True,'independent_optimizer_replications':False,
            'structural_change_is_effect':False,'causal_mechanism_effect_identified':False,
            'new_model_calls':0,'new_code_executions':0,'loss_or_selection_changed':False,
            'held_out_evaluation':False,'scientific_truth':False,'publication_ready':False}}


def construction(record,session):
    """Actual complete chronological prefix; missing summaries remain unknown."""
    if (session['request_sha256']!=record['request_sha256']
            or session['definition']!=record['definition']):
        raise ValueError('literal original staged wrapper request/definition required')
    steps=session['steps']; response=session['response']
    for index,step in enumerate(steps):
        checked(step)
        if step['step']!=index: raise ValueError('exact chronological completed step prefix required')
    if response is None:
        if record['generation_error'] is None:
            raise ValueError('missing original terminal requires retained generation failure')
        trace={'component_testing':None,'completed_steps':len(steps),
               'drawn_candidate_artifact_observations':None,'events':None,
               'same_fixture_later_code_comparisons':None,'automatic_repair_claimed':False}
    else:
        checked(response)
        if (response['request_sha256']!=record['request_sha256']
                or response['status'] not in ('generated','generation-failed')
                or (response['status']=='generated' and response['definition']!=record['definition'])
                or (response['status']=='generation-failed' and record['generation_error'] is None)):
            raise ValueError('literal original staged terminal differs from consumed proposal')
        candidate=(record['draws'][0]['suggestion']['candidate']
            if record['draws'] and record['draws'][0]['suggestion'] is not None else None)
        trace=component_trace(steps,response,candidate)
    trace.update(terminal_response_missing=response is None,
        recorded_completed_steps=len(steps),charged_model_calls_inferred_from_steps=False,
        author_steps=[{'step':s['step'],'status':s['status'],
            'tool':(s.get('transition') or {}).get('tool'),'step_content_sha256':s['content_sha256']} for s in steps])
    return trace


def behavior_evidence(root,plan,audit,records):
    """Join original construction, full model inputs and committed native effects."""
    construction_rows=[]
    for slot in plan['schedule']:
        objective,g=slot['objective'],slot['generation']; record=records[objective,g]
        directory=root/'search'/objective/'authoring'/('proposal-'+record['request_sha256'])
        read=lambda p:checked(json.loads(p.read_text()))
        binding,wrapper=read(directory/'binding.json'),read(directory/'result.json')
        if (binding['request']!=record['request'] or wrapper['binding_sha256']!=binding['content_sha256']):
            raise ValueError('exact original author session binding required')
        inner=directory/'editor-session/authoring'/('generation-'+record['request_sha256'])
        terminal=inner/'response.json'
        session={'request_sha256':digest(binding['request']),'definition':wrapper['definition'],
            'response':read(terminal) if terminal.is_file() else None,
            'steps':[read(p) for p in sorted(inner.glob('step-*.completed.json'))]}
        construction_rows.append({**clone(slot),'trace':construction(record,session)})
    requests=[]; effects=[]
    for world in audit['worlds']:
        cell=Path(world['loaded']['context']).resolve().parent
        if not cell.is_relative_to(root): raise ValueError('audited physical world outside original run')
        wire,cache=cell/'wire-requests.jsonl',cell/'replies/responses.sqlite'
        wires=[json.loads(line) for line in wire.read_text().splitlines()] if wire.is_file() else []
        replies=[]
        if cache.is_file():
            with sqlite3.connect(cache.resolve().as_uri()+'?mode=ro',uri=True) as db:
                replies=db.execute('SELECT payload_sha,outcome,data,data_sha FROM replies ORDER BY rowid').fetchall()
        requests.append({'identity':world['identity'],'seed':world['seed'],'status':world['status'],
                         'requests':sequence(wires,replies)})
        if world['physical_proof'] is None:
            effects.append({'identity':world['identity'],'status':world['status'],'trace':None,
                            'reason':'no-physical-proof-recorded-not-zero-events'})
        else:
            effects.append({'identity':world['identity'],'status':world['status'],
                'trace':trace_world(cell,world,plan['source_commit'],workflow=True)})
    return {'construction':construction_rows,'world_request_sequences':requests,
        'complete_observed_input_classes':groups(requests),'native_effect_traces':effects,
        'scope':'All recorded steps and complete summaries reconcile. Missing summaries stay unknown. '
            'Exact full scientist payloads/choices are not semantic program equivalence. Native code '
            'receipts, committed events, resource ledgers and rendered input presence describe actual '
            'execution; they do not identify causal mediation, useful invention or method superiority.',
        'new_model_calls':0,'new_code_executions':0,'new_native_worlds':0,'loss_or_selection_changed':False}


def render(report,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    with plt.rc_context({'font.size':8,'axes.spines.top':False,'axes.spines.right':False,'svg.hashsalt':SCHEMA}):
        fig,axes=plt.subplots(1,3,figsize=(11.8,3.7))
        for ax,objective in zip(axes,OBJECTIVES):
            for reference,color in zip(report['references'],('#64748b','#b07934')):
                ax.axhline(reference['cross_scores'][objective],color=color,ls='--',lw=1,label=reference['label'])
            path=report['loss_paths'][objective]; generations=[r['generation'] for r in path]
            for row in path:
                if row['observed_loss'] is None:
                    ax.text(row['generation'],.03,'null',transform=ax.get_xaxis_transform(),ha='center',color='#ac434a')
                else: ax.scatter(row['generation'],row['observed_loss'],color='#087f8c',s=24,zorder=3)
            ax.plot(generations,[math.nan if r['best_own_loss'] is None else r['best_own_loss'] for r in path],
                    color='#087f8c',label='Best own submitted loss')
            ax.plot(generations,[r['best_known_loss_including_visible_references'] for r in path],
                    color='#6555a1',ls=':',label='Best known, including parents')
            ax.set(title=objective,xlabel='Own proposal generation',ylabel='Assigned loss (lower is better)',
                   xticks=generations,xlim=(-.25,max(generations)+.25))
            ax.grid(axis='y',color='#ededed'); ax.legend(fontsize=6,loc='best')
        fig.suptitle('Objective-conditioned system search: all six slots, one reused development condition',fontsize=10)
        fig.tight_layout(rect=(0,.02,1,.94))
        for ext in ('png','svg'): fig.savefig(out/('objective-loss-paths.'+ext),dpi=200,
                                            metadata={'Date':None} if ext=='svg' else None)
        plt.close(fig)
        rows=[(r['label'],r) for r in report['references']]+[
            (r['objective']+' g'+str(r['generation'])+' ['+r['status']+']',r) for r in report['slots']]
        number=lambda x:'unknown' if x is None else f'{x:.6g}'
        cells=[[label,*[number(r['cross_scores'][key]) for key in OBJECTIVES],
                number(r['metrics'][METRIC]['value'])] for label,r in rows]
        fig,ax=plt.subplots(figsize=(11.8,4.5)); ax.axis('off')
        table=ax.table(cellText=cells,colLabels=['Actual system / original slot','T loss','U loss','C loss','Collected K'],
                       colWidths=[.56,.11,.11,.11,.11],cellLoc='left',bbox=(0,.13,1,.82))
        table.auto_set_font_size(False); table.set_fontsize(8)
        for (i,j),cell in table.get_celld().items():
            cell.set_edgecolor('#d7dfe6'); cell.set_linewidth(.5)
            if i==0: cell.set_facecolor('#edf2f5')
            elif cell.get_text().get_text()=='unknown': cell.set_facecolor('#f1f1f1')
        fig.suptitle('Literal cross-objective outcomes and native resource consumption',fontsize=10)
        fig.text(.05,.035,'Unknown remains unknown. C = (content utility loss) + 0.1 K is a development preference, not welfare.\n'
                 'One reused condition; not independent optimizer replications or scientific truth.',fontsize=8)
        fig.tight_layout(rect=(0,.06,1,.94))
        for ext in ('png','svg'): fig.savefig(out/('literal-outcomes.'+ext),dpi=200,
                                            metadata={'Date':None} if ext=='svg' else None)
        plt.close(fig)


def export(args):
    root,frozen,out=args.run.resolve(),args.frozen_source.resolve(),args.output.resolve()
    source=pinned_revision(ROOT); scientific=pinned_revision(frozen)
    if out.exists() or any(out.is_relative_to(p) for p in (root,frozen,ROOT)):
        raise ValueError('fresh report outside scientific raw and reader/scientific source required')
    inputs=[root/'plan.json',root/'terminal.json',root/'selection.json',args.audit_one.resolve(),args.audit_two.resolve()]
    if inputs[-1]==inputs[-2] or inputs[-1].read_bytes()!=inputs[-2].read_bytes():
        raise ValueError('two distinct matching frozen-source audits required')
    hashes={str(p):file_sha256(p) for p in inputs}; before=_inventory(root)
    read=lambda p:checked(json.loads(p.read_text()))
    p,a=read(inputs[0]),read(inputs[-2])
    if (p['source_commit']!=scientific or a['raw_inventory_sha256']!=digest(before)
            or a['closure']['terminal']!=read(inputs[1]) or a['selection']!=read(inputs[2])):
        raise ValueError('unchanged normal closure and original source/audit/raw required')
    records={}; observations={}
    for label in p['reference_order']:
        o=read(root/'references'/label/'observation.json'); observations[o['suggestion_id']]=o
    for objective in OBJECTIVES:
        state=json.loads((root/'search'/objective/'campaign/native-adaptive-state.json').read_text())
        if state['pending'] is not None or len(state['records'])!=p['generations']:
            raise ValueError('terminal exact declared own history required')
        for generation,r in enumerate(state['records']):
            records[objective,generation]=r
            for o in r['observations']:
                if o is not None:
                    if o['suggestion_id'] in observations: raise ValueError('duplicate actual observation')
                    observations[o['suggestion_id']]=o
    report=analyze(p,a,records,observations)
    report.update(analysis_source_commit=source,raw_inventory_sha256=digest(before))
    report['behavior_evidence']=behavior_evidence(root,p,a,records)
    if before!=_inventory(root) or hashes!={str(p):file_sha256(p) for p in inputs}:
        raise ValueError('original report inputs changed')
    out.mkdir(parents=True); save(out/'report.json',report); render(report,out)
    fields=['slot_index','objective','generation','status','physical_job','loss',*OBJECTIVES,'collected_resource_cost']
    with (out/'slots.csv').open('x',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields); writer.writeheader()
        writer.writerows({**{k:r[k] for k in fields if k in r},**r['cross_scores'],
                          'collected_resource_cost':r['metrics'][METRIC]['value']} for r in report['slots'])
    save(out/'manifest.json',{'schema':SCHEMA+'.export','inputs':hashes,'analysis_source_commit':source,
        'scientific_source_commit':scientific,'adapter_file_sha256':file_sha256(Path(__file__)),
        'files':{p.name:file_sha256(p) for p in sorted(out.iterdir())},'new_model_calls':0,'new_code_executions':0})
    if (before!=_inventory(root) or hashes!={str(p):file_sha256(p) for p in inputs}
            or pinned_revision(ROOT)!=source or pinned_revision(frozen)!=scientific):
        raise ValueError('original data or bound reader/scientific source changed during export')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    keys=('run','frozen-source','audit-one','audit-two','output')
    for key in keys: parser.add_argument('--'+key,type=Path,required=True)
    args=parser.parse_args()
    if os.environ.get('SCIENCE_UTOPIA_COLD_TOPIC_FREE_READOUT_WORKER')=='1': export(args); return
    result=subprocess.run([sys.executable,'-B','-c',
        'import runpy,sys;sys.path.insert(0,sys.argv.pop(1));runpy.run_path(sys.argv.pop(1),run_name="__main__")',
        str(args.frozen_source.resolve()),str(Path(__file__).resolve()),
        *[value for key in keys for value in ('--'+key,str(getattr(args,key.replace('-','_')).resolve()))]],
        cwd=args.frozen_source,env={**os.environ,'PYTHONHASHSEED':'42','SCIENCE_UTOPIA_COLD_TOPIC_FREE_READOUT_WORKER':'1'},
        timeout=1800,check=False)
    if result.returncode: raise SystemExit(result.returncode)


if __name__=='__main__': main()
