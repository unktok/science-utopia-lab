"""Closed-record edit -> observed input -> objective map; never a loss oracle."""
import argparse
import csv
import json
from pathlib import Path

from scripts.analyze_native_open_v7 import _inventory
from scripts.finish_native_institution_loop_v1 import same_files
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked,save
from utopia.optimization.native_topic_objectives_v1 import OBJECTIVES
from utopia.system.design_patch import clone,digest
from utopia.utils.data_utils import file_sha256

ROOT=Path(__file__).resolve().parents[2]
SCHEMA='scienceutopia.native-topic-effect-map.v1'


def derive(report):
    """Join existing complete readout rows without interpreting authored prose."""
    if (report['schema']!='scienceutopia.native-topic-free-readout.v1'
            or report['score_order']!=list(OBJECTIVES) or len(report['slots'])!=6
            or report['consumed_own_slots']!=6
            or report['interpretation']['loss_or_selection_changed']
            or report['interpretation']['new_model_calls']):
        raise ValueError('complete unchanged six-slot original readout required')
    expected=[(o,g)for g in range(2)for o in (OBJECTIVES if g==0 else OBJECTIVES[::-1])]
    if [(s['objective'],s['generation'])for s in report['slots']]!=expected:
        raise ValueError('exact original all-slot ordering required')
    evidence=report['behavior_evidence'];requests=evidence['world_request_sequences']
    by_id={r['identity']:r for r in requests}
    if len(by_id)!=len(requests):raise ValueError('unique original physical input traces required')
    rows=[]
    for slot in report['slots']:
        graph=slot['graph_from_parent'];changed=None if graph is None else {
            'source_nodes':sorted(graph['source_edits']),
            'changed_existing_nodes':sorted(graph['changed_mechanisms']),
            'added_nodes':sorted(graph['added_nodes']),'removed_nodes':sorted(graph['removed_nodes']),
            'added_connections':len(graph['added_connections']),
            'removed_connections':len(graph['removed_connections']),
            'phase_updates':sorted(graph['phase_updates']),
            'changed_system_fields':sorted(graph['changed_system_fields']),
            'added_schedules':sorted(graph['added_schedules']),
            'removed_schedules':sorted(graph['removed_schedules'])}
        row={k:clone(slot[k])for k in ('slot_index','objective','generation','status','physical_job','loss',
            'literal_system_changed')}
        row.update(submitted_change=changed,complete_input_trace=None,
            matching_reference_inputs=None,matching_reference_choices=None,
            best_visible_reference_loss=min(r['cross_scores'][slot['objective']]
                for r in report['references'] if r['optimizer_visible']),
            delta_from_best_visible_reference=None)
        if slot['physical_job'] is not None:
            trace=by_id[slot['physical_job']]
            if trace['status']!=slot['status']:raise ValueError('original world/slot status differs')
            row['recorded_requests']=trace['requests']['wire_requests']
            row['recorded_completed_responses']=trace['requests']['completed_responses']
        else:row.update(recorded_requests=None,recorded_completed_responses=None)
        if slot['status']=='complete':
            if slot['physical_job'] is None:raise ValueError('complete slot requires actual physical trace')
            q=trace['requests']
            if q['wire_inputs_without_committed_reply']!=0:
                raise ValueError('complete-input class cannot use an unmatched request prefix')
            matches=[r for r in report['references'] if by_id[r['physical_job']]['seed']==trace['seed']
                and by_id[r['physical_job']]['requests']['ordered_full_request_payload_sha256']==q['ordered_full_request_payload_sha256']]
            row['complete_input_trace']=True
            row['matching_reference_inputs']=[r['label']for r in matches]
            row['matching_reference_choices']=[r['label']for r in matches if
                by_id[r['physical_job']]['requests']['ordered_literal_response_choices_sha256']==q['ordered_literal_response_choices_sha256']]
            row['delta_from_best_visible_reference']=slot['loss']-row['best_visible_reference_loss']
        rows.append(row)
    return {'schema':SCHEMA,'scientific_source_commit':report['scientific_source_commit'],
        'readout_content_sha256':report['content_sha256'],'rows':rows,
        'scope':'All six original slots, including nulls. Literal source/graph changes are not native '
            'effects. Matching full model inputs/choices describes an observed trajectory, not '
            'semantic equivalence, causal mediation or independent replications. Difference from '
            'the best visible reference is descriptive, not a new loss, selection or merit veto.',
        'new_model_calls':0,'new_native_worlds':0,'new_code_executions':0,
        'loss_or_selection_changed':False,'publication_ready':False}


def render(value,out):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from textwrap import fill
    cells=[]
    for row in value['rows']:
        change=row['submitted_change']
        if change is None:edited='No submitted system'
        elif row['literal_system_changed'] is False:edited='Literal unchanged parent'
        else:
            edited=('Source: '+', '.join(change['source_nodes']) if change['source_nodes'] else
                'Changed: '+', '.join(change['changed_existing_nodes']) if change['changed_existing_nodes'] else
                'System fields: '+', '.join(change['changed_system_fields']) if change['changed_system_fields'] else
                'Graph composition / schedule only')
            edited+='\nNodes +'+str(len(change['added_nodes']))+'/-'+str(len(change['removed_nodes']))
            edited+='; wires +'+str(change['added_connections'])+'/-'+str(change['removed_connections'])
            edited+='; schedule changes '+str(sum(len(change[k])for k in ('phase_updates','added_schedules','removed_schedules')))
        if row['complete_input_trace']:
            inputs=('Reference inputs: '+(', '.join(row['matching_reference_inputs'])or 'no match'))
            inputs+='\nReference choices: '+(', '.join(row['matching_reference_choices'])or 'no match')
            inputs+='\n'+str(row['recorded_requests'])+' complete scientist requests'
        else:inputs='No complete native input trace\nRecorded requests: '+str(row['recorded_requests'])
        delta=row['delta_from_best_visible_reference']
        loss='Unknown - retained null' if delta is None else (
            f"Loss {row['loss']:.6g}\nDelta {delta:+.6g} vs strongest visible reference\n"+
            ('Tie' if delta==0 else 'Lower loss' if delta<0 else 'Higher loss'))
        cells.append([row['objective']+'\ng'+str(row['generation'])+' / '+row['status'],
            '\n'.join(fill(line,48)for line in edited.splitlines()),
            '\n'.join(fill(line,44)for line in inputs.splitlines()),loss])
    with plt.rc_context({'font.size':8,'svg.hashsalt':SCHEMA}):
        fig,ax=plt.subplots(figsize=(14,7.4));ax.axis('off')
        table=ax.table(cellText=cells,colLabels=['Original slot','Submitted design, relative to parent',
            'Observed full scientist inputs / choices','Assigned objective'],
            colWidths=[.18,.29,.31,.22],cellLoc='left',bbox=(0,.1,1,.84))
        table.auto_set_font_size(False);table.set_fontsize(8)
        for (i,j),cell in table.get_celld().items():
            cell.set_edgecolor('#d8e0e7');cell.set_linewidth(.6)
            if i==0:cell.set_facecolor('#e6eef3')
            elif value['rows'][i-1]['status']!='complete':cell.set_facecolor('#f7e8e9')
            elif j==3:
                delta=value['rows'][i-1]['delta_from_best_visible_reference']
                cell.set_facecolor('#edf4ef' if delta<0 else '#f7ede4' if delta>0 else '#f1f3f5')
        fig.suptitle('Edits, observed behavior and objective value are distinct',fontsize=13,y=.98)
        fig.text(.02,.025,'One reused development condition; all six slots remain visible. '
            'Unknown is not zero. Equal request paths are not program equivalence.\n'
            'Reference differences are descriptive; no new loss, reselection, causal claim or independent replication.',fontsize=9)
        fig.tight_layout(rect=(0,.035,1,.95))
        for ext in ('png','svg'):fig.savefig(out/('edit-input-objective-map.'+ext),dpi=200,
            metadata={'Date':None}if ext=='svg'else None)
        plt.close(fig)


def print_cells(value):
    """Compact labels for native5.5-inch print, with a literal ID legend."""
    identities=sorted({name for row in value['rows']if row['submitted_change']is not None
        for key in ('source_nodes','changed_existing_nodes','added_nodes','removed_nodes')
        for name in row['submitted_change'][key]})
    tags={name:'m'+str(i+1)for i,name in enumerate(identities)};cells=[]
    for row in value['rows']:
        change=row['submitted_change'];delta=row['delta_from_best_visible_reference']
        if change is None:edited='No submitted system'
        elif row['literal_system_changed']is False:edited='Exact parent retained'
        else:
            names=change['source_nodes']or change['changed_existing_nodes']
            edited=('Source: 'if change['source_nodes']else'Parameters: ')+', '.join(tags[n]for n in names)
            if not names:edited='Graph / system fields'
            edited+='\nNodes +'+str(len(change['added_nodes']))+'/-'+str(len(change['removed_nodes']))
            edited+='; edges +'+str(change['added_connections'])+'/-'+str(change['removed_connections'])
            edited+='\nSchedule changes: '+str(sum(len(change[k])for k in ('phase_updates','added_schedules','removed_schedules')))
        if row['complete_input_trace']:
            matched=', '.join(row['matching_reference_inputs'])or'no reference match'
            choices=', '.join(row['matching_reference_choices'])or'no reference match'
            inputs='Inputs: '+matched+'\nChoices: '+choices+'\n'+str(row['recorded_requests'])+' complete requests'
        else:inputs='No complete trace\nRecorded requests: '+str(row['recorded_requests'])
        loss='Unknown\nRetained null'if delta is None else f"{row['loss']:.6g}\nDelta {delta:+.6g}\n"+(
            'Tie'if delta==0 else'Lower loss'if delta<0 else'Higher loss')
        cells.append([row['objective']+'\ng'+str(row['generation'])+' / '+row['status'],edited,inputs,loss])
    return cells,[tag+' = '+name for name,tag in tags.items()]


def render_print(value,readout,out):
    """Native-width paper figures, not shrinking a wide8pt chart into3pt text."""
    import math
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from textwrap import fill
    cells,legend=print_cells(value)
    with plt.rc_context({'font.size':8,'svg.hashsalt':SCHEMA+'.print',
            'axes.spines.top':False,'axes.spines.right':False}):
        fig,axes=plt.subplots(3,1,figsize=(5.5,7.1))
        handles=[];labels=[]
        for ax,objective in zip(axes,OBJECTIVES):
            for reference,color in zip(readout['references'],('#64748b','#b07934')):
                ax.axhline(reference['cross_scores'][objective],color=color,ls='--',lw=1,label=reference['label'])
            path=readout['loss_paths'][objective];xs=[r['generation']for r in path]
            for row in path:
                if row['observed_loss']is None:
                    ax.text(row['generation'],.04,'runtime null'if row['status']=='failed'else'generation null',
                        transform=ax.get_xaxis_transform(),ha='center',fontsize=7,color='#a33b48')
                else:ax.scatter(row['generation'],row['observed_loss'],color='#087f8c',s=24,zorder=4)
            ax.plot(xs,[math.nan if r['best_own_loss']is None else r['best_own_loss']for r in path],
                color='#087f8c',label='Best own submission',lw=1.5)
            ax.plot(xs,[r['best_known_loss_including_visible_references']for r in path],
                color='#6555a1',ls=':',label='Best known including references',lw=1.5)
            ax.set(title=objective,ylabel='Assigned loss',xticks=xs,xlim=(-.2,max(xs)+.2))
            ax.grid(axis='y',color='#e7ebee')
            if not handles:handles,labels=ax.get_legend_handles_labels()
        axes[-1].set_xlabel('Own proposal generation')
        fig.suptitle('Own progress versus already known performance',fontsize=11,y=.995)
        fig.legend(handles,labels,loc='upper center',bbox_to_anchor=(.5,.965),ncol=2,fontsize=7,frameon=False)
        fig.text(.02,.012,'All six slots, one reused development condition. Lower loss is better.\n'
            'A null is not zero. Coincident paths do not establish independent replications.',fontsize=7)
        fig.tight_layout(rect=(0,.055,1,.91))
        for ext in ('png','svg'):fig.savefig(out/('objective-loss-paths-print.'+ext),dpi=250,
            metadata={'Date':None}if ext=='svg'else None)
        plt.close(fig)
        fig,ax=plt.subplots(figsize=(5.5,6.8));ax.axis('off')
        widths=(18,25,30,16)
        wrapped=[['\n'.join(fill(line,width)for line in cell.splitlines())for cell,width in zip(row,widths)]for row in cells]
        table=ax.table(cellText=wrapped,colLabels=['Original slot','Submitted change','Full native input path','Assigned loss'],
            colWidths=[.18,.28,.34,.20],cellLoc='left',bbox=(0,.18,1,.74))
        table.auto_set_font_size(False);table.set_fontsize(6.5)
        for (i,j),cell in table.get_celld().items():
            cell.set_edgecolor('#d8e0e7');cell.set_linewidth(.5)
            if i==0:cell.set_facecolor('#e6eef3')
            elif value['rows'][i-1]['status']!='complete':cell.set_facecolor('#f7e8e9')
        fig.suptitle('Submitted edits are not observed effects',fontsize=11,y=.98)
        fig.text(.02,.13,'; '.join(legend),fontsize=6.5,wrap=True)
        fig.text(.02,.025,'All six original slots. Delta is versus the strongest visible reference.\n'
            'Source and graph counts describe literal submissions, not native causation.\n'
            'Equal input/choice paths are observed trajectories, not program equivalence.\n'
            'No loss, policy selection or failure status is changed by this figure.',fontsize=7)
        fig.tight_layout(rect=(0,.02,1,.95))
        for ext in ('png','svg'):fig.savefig(out/('edit-input-objective-map-print.'+ext),dpi=250,
            metadata={'Date':None}if ext=='svg'else None)
        plt.close(fig)


def export(args):
    root,one,two,out=(getattr(args,k).resolve()for k in ('run','readout_one','readout_two','output'))
    source=pinned_revision(ROOT)
    if one==two or out.exists()or any(out.is_relative_to(p)for p in (root,one,two,ROOT)):
        raise ValueError('distinct paired readouts and fresh external output required')
    same_files(one,two);files=[root/'terminal.json',one/'report.json',two/'report.json',one/'manifest.json',two/'manifest.json']
    inputs={str(f):file_sha256(f)for f in files};report=checked(json.loads(files[1].read_text()))
    if json.loads(files[0].read_text())['status']!='closed':raise ValueError('original normal closure required')
    before=_inventory(root)
    if digest(before)!=report['raw_inventory_sha256']:raise ValueError('original raw differs from paired readouts')
    for directory in (one,two):
        manifest=checked(json.loads((directory/'manifest.json').read_text()))
        for name,sha in manifest['files'].items():
            if file_sha256(directory/name)!=sha:raise ValueError('upstream readout artifact differs')
        for name,sha in manifest['inputs'].items():
            if file_sha256(name)!=sha:raise ValueError('upstream original input differs')
    value=derive(report);value['analysis_source_commit']=source
    out.mkdir(parents=True);save(out/'report.json',value);render(value,out);render_print(value,report,out)
    with (out/'slots.csv').open('x',newline='')as stream:
        writer=csv.DictWriter(stream,fieldnames=list(value['rows'][0]),lineterminator='\n');writer.writeheader()
        for row in value['rows']:writer.writerow({k:json.dumps(v,sort_keys=True)if isinstance(v,(dict,list))else v for k,v in row.items()})
    save(out/'manifest.json',{'schema':SCHEMA+'.export','inputs':inputs,'analysis_source_commit':source,
        'files':{f.name:file_sha256(f)for f in sorted(out.iterdir())},'new_model_calls':0})
    if before!=_inventory(root)or inputs!={name:file_sha256(name)for name in inputs}or pinned_revision(ROOT)!=source:
        raise ValueError('original raw/readout/reader changed during export')


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for key in ('run','readout-one','readout-two','output'):parser.add_argument('--'+key,type=Path,required=True)
    export(parser.parse_args())
