"""Read-only author search footprint; proposed targets are not native effects."""
import argparse
from collections import Counter
import csv
import json
from pathlib import Path

from scripts.analyze_native_open_v7 import _inventory
from scripts.finish_native_institution_loop_v1 import same_files
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked, save
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256

ROOT=Path(__file__).resolve().parents[2]
SCHEMA='scienceutopia.native-longitudinal-search-allocation.v1'


def read(path):return checked(json.loads(Path(path).read_text()))


def step_summary(step):
    """Schema-rejected model JSON is data, never an executable tool object."""
    reply=step.get('model_reply');reply=reply if isinstance(reply,dict) else {}
    raw_action=reply.get('output');action=raw_action if isinstance(raw_action,dict) else {}
    transition=step.get('transition');transition=transition if isinstance(transition,dict) else {}
    raw_tool=transition.get('tool');tool=raw_tool if isinstance(raw_tool,str) else None
    filename=action.get('filename');filename=filename if isinstance(filename,str) else None
    operations=action.get('operations');operations=operations if isinstance(operations,list) else []
    proposed_paths=[op['path'] for op in operations if isinstance(op,dict) and isinstance(op.get('path'),str)]
    result=transition.get('result');result=result if isinstance(result,dict) else {}
    applied=step['status']=='applied' and transition.get('ok') is True
    targets=[]
    if applied:
        mapping=result.get('operation_map',[])
        if not isinstance(mapping,list):raise ValueError('applied host operation map malformed')
        for item in mapping:
            if not isinstance(item,dict) or not isinstance(item.get('translated_path'),str):
                raise ValueError('literal applied host operation target required')
            owner=item.get('actual_owner_id')
            if owner is not None and not isinstance(owner,str):raise ValueError('host owner identity malformed')
            targets.append({'owner_id':owner,'translated_path':item['translated_path']})
    errors=[]
    for location,value in (('step',step.get('errors',[])),('transition',transition.get('errors',[]))):
        for error in value if isinstance(value,list) else [value]:
            errors.append((location,error))
    diagnostics=[]
    for location,error in errors:
        message=error.get('message') if isinstance(error,dict) else error
        diagnostics.append({'location':location,'type':error.get('type') if isinstance(error,dict) else type(error).__name__,
            'message_excerpt':message[:400] if isinstance(message,str) else None,
            'message_is_excerpt':isinstance(message,str) and len(message)>400,
            'full_message_value_digest':digest(message) if isinstance(message,str) else None})
    return {'step':step['step'],'status':step['status'],'tool':tool,
        'tool_field_type':type(raw_tool).__name__,'step_content_sha256':step['content_sha256'],
        'untrusted_model_output_type':type(raw_action).__name__,
        'untrusted_target_field_types':{k:type(action[k]).__name__ for k in ('filename','operations') if k in action},
        'untrusted_action_field_names':sorted(action),'untrusted_proposed_filename':filename,
        'untrusted_proposed_paths':proposed_paths,'applied_host_edit_targets':targets,
        'document_changed':applied and result.get('literal_document_changed') is True,
        'draft_changed':applied and isinstance(transition.get('draft_before_sha256'),str)
            and isinstance(transition.get('draft_after_sha256'),str)
            and transition['draft_before_sha256']!=transition['draft_after_sha256'],
        'rejection_diagnostics':diagnostics,'native_effect_inferred':False}


def summarize(plan,construction,steps_by_slot):
    expected=[(s['arm'],s['objective'],s['generation']) for s in plan['schedule']]
    actual=[(s['arm'],s['objective'],s['generation']) for s in construction['slots']]
    if (len(expected)!=12 or len(set(expected))!=12 or actual!=expected
            or set(steps_by_slot)!=set(expected)):
        raise ValueError('all twelve original arm/objective/generation slots required')
    slots=[];histories={}
    for row in construction['slots']:
        key=row['arm'],row['objective'],row['generation'];trace=row['construction_trace']
        steps=steps_by_slot[key]
        if [s['step'] for s in steps]!=list(range(len(steps))):raise ValueError('complete chronological step prefix required')
        if not trace['terminal_response_missing']:
            projection=[{'step':s['step'],'status':s['status'],
                'tool':(s.get('transition') or {}).get('tool'),'step_content_sha256':s['content_sha256']} for s in steps]
            if projection!=trace['author_steps']:raise ValueError('raw complete steps differ from original construction export')
        views=[step_summary(s) for s in steps]
        reads=Counter(v['untrusted_proposed_filename'] for v in views
            if v['tool']=='read_file' and v['untrusted_proposed_filename'] is not None)
        applied_reads=Counter(v['untrusted_proposed_filename'] for v in views
            if v['tool']=='read_file' and v['status']=='applied' and v['untrusted_proposed_filename'] is not None)
        owners=Counter(t['owner_id'] for v in views if v['document_changed']
            for t in v['applied_host_edit_targets'] if t['owner_id'] is not None)
        slot={'arm':row['arm'],'objective':row['objective'],'generation':row['generation'],
            'status':row['status'],'loss':row['loss'],'request_sha256':row['request_sha256'],
            'terminal_response_missing':trace['terminal_response_missing'],
            'recorded_complete_step_prefix':len(steps),'final_call_total_known':not trace['terminal_response_missing'],
            'read_attempts_by_proposed_filename':dict(sorted(reads.items())),
            'applied_reads_by_proposed_filename':dict(sorted(applied_reads.items())),
            'changed_document_host_owner_operations':dict(sorted(owners.items())),
            'rejected_recorded_steps':sum(v['status']=='rejected' for v in views),'steps':views}
        slots.append(slot);history='::'.join(key[:2]);h=histories.setdefault(history,{'slots':0,
            'missing_terminal_slots':0,'recorded_complete_steps':0,'changed_document_host_owner_operations':{}})
        h['slots']+=1;h['missing_terminal_slots']+=int(trace['terminal_response_missing'])
        h['recorded_complete_steps']+=len(steps)
        h['changed_document_host_owner_operations']=dict(sorted((Counter(h['changed_document_host_owner_operations'])+owners).items()))
    return {'schema':SCHEMA,'scientific_source_commit':plan['source_commit'],
        'plan_content_sha256':plan['content_sha256'],'construction_content_sha256':construction['content_sha256'],
        'slots':slots,'histories':histories,'new_model_calls':0,'new_code_executions':0,
        'loss_or_selection_changed':False,'applied_target_is_native_effect':False,
        'causal_search_bias_or_repair_proved':False,'independent_optimizer_replications':False,
        'publication_ready':False,'scope':'Twelve original slots. Proposed strings are untrusted diagnostic data; '
            'host-mapped edits are draft operations, not native consumption. Missing terminal totals remain unknown. '
            'No program is executed, repaired, refilled, reselected or judged novel by this reader.'}


def export(args):
    root=args.run.resolve();out=args.output.resolve();one=args.construction_one.resolve();two=args.construction_two.resolve()
    source=pinned_revision(ROOT)
    if out.exists() or any(out.is_relative_to(p) for p in (root,one,two)):
        raise ValueError('fresh allocation output outside original raw/upstream exports required')
    files=same_files(one,two)
    paths=[root/'plan.json',root/'terminal.json',args.audit_one.resolve(),args.audit_two.resolve(),
        one/'report.json',one/'manifest.json',two/'report.json',two/'manifest.json',Path(__file__)]
    inputs={str(p):file_sha256(p) for p in paths}
    p=read(paths[0]);terminal=read(paths[1]);a=read(paths[2]);b=read(paths[3]);construction=read(one/'report.json')
    before=_inventory(root)
    if (p['schema']!='scienceutopia.native-longitudinal-comparison.v1.plan'
            or a!=b or paths[2].read_bytes()!=paths[3].read_bytes()
            or a['schema']!='scienceutopia.native-longitudinal-comparison-audit.v1'
            or a['plan_sha256']!=p['content_sha256'] or a['source_commit']!=p['source_commit']
            or a['source_proof']['status']!='verified-exact-source-closure'
            or terminal['status']!='closed' or a['closure']['terminal']!=terminal
            or a['raw_inventory_sha256']!=digest(before)
            or construction['schema']!='scienceutopia.native-longitudinal-construction-trace.v1'
            or construction['plan_sha256']!=p['content_sha256']
            or construction['audit_content_sha256']!=a['content_sha256']):
        raise ValueError('original closed twelve-slot audit/construction evidence required')
    for directory in (one,two):
        manifest=read(directory/'manifest.json')
        if (manifest['raw_inventory_sha256']!=digest(before)
                or manifest['report_content_sha256']!=construction['content_sha256']):
            raise ValueError('construction export differs from original raw/report')
        for path,sha in manifest['inputs'].items():
            if file_sha256(path)!=sha:raise ValueError('upstream construction input changed')
            inputs[path]=sha
        for name,sha in manifest['files'].items():
            if name not in files or file_sha256(directory/name)!=sha:raise ValueError('construction file changed')
    steps={}
    from scripts.run_native_longitudinal_comparison_v1 import history_directory
    for row in construction['slots']:
        key=row['arm'],row['objective'],row['generation']
        if len(row['request_sha256'])!=64 or any(c not in '0123456789abcdef' for c in row['request_sha256']):
            raise ValueError('original request digest required for journal location')
        inner=history_directory(root,key[:2])/'authoring'/('proposal-'+row['request_sha256'])/'editor-session/authoring'/('generation-'+row['request_sha256'])
        if not inner.resolve().is_relative_to(root):raise ValueError('step journal outside original raw')
        steps[key]=[read(path) for path in sorted(inner.glob('step-*.completed.json'))]
    report=summarize(p,construction,steps);report['analysis_source_commit']=source
    if before!=_inventory(root) or inputs!={path:file_sha256(path) for path in inputs}:
        raise ValueError('original allocation inputs changed during read')
    out.mkdir(parents=True);saved=save(out/'report.json',report)
    fields=['arm','objective','generation','status','loss','recorded_complete_step_prefix',
        'terminal_response_missing','rejected_recorded_steps','changed_document_host_owner_operations']
    with (out/'slots.csv').open('x',newline='') as stream:
        writer=csv.DictWriter(stream,fieldnames=fields,lineterminator='\n');writer.writeheader()
        for row in saved['slots']:
            writer.writerow({k:json.dumps(row[k],sort_keys=True) if isinstance(row[k],dict) else row[k] for k in fields})
    save(out/'manifest.json',{'schema':SCHEMA+'.export','inputs':inputs,
        'raw_inventory_sha256':digest(before),'report_content_sha256':saved['content_sha256'],
        'files':{f.name:file_sha256(f) for f in sorted(out.iterdir()) if f.is_file()},'new_model_calls':0})
    if before!=_inventory(root) or pinned_revision(ROOT)!=source:raise ValueError('raw/reader source changed')
    return saved


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    for name in ('run','audit-one','audit-two','construction-one','construction-two','output'):
        parser.add_argument('--'+name,type=Path,required=True)
    result=export(parser.parse_args());print(json.dumps({'slots':len(result['slots']),'new_model_calls':0}))
