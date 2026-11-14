"""Cold source/consumer/resource traces from already independently audited worlds.

Execution and received-input evidence are descriptive, not a mechanism ablation.
No source is executed and no loss, selection or scientific raw record is changed.
"""
import argparse
from collections import Counter
import csv
import hashlib
import json
import math
from pathlib import Path
import sqlite3
from types import SimpleNamespace

from scripts.analyze_native_open_v7 import _inventory
from utopia.funding.accounting import ResourceLedger
from utopia.optimization.native_code_trace import validate_record,recorded_attempts
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked,save
from utopia.runtime.checkpointing import read_portable_checkpoint
from utopia.system import SystemSpec
from utopia.system.native_migration import native_execution_nodes
from utopia.system.design_patch import clone,digest
from utopia.utils.data_utils import file_sha256

SCHEMA='scienceutopia.native-institution-effect-trace.v1'
SCOPES={
    'longitudinal-objective-development':'scienceutopia.native-longitudinal-comparison-audit.v1',
    'longitudinal-fixed-evaluation':'scienceutopia.native-longitudinal-fixed-evaluation-audit.v1',
    'workflow-fixed-evaluation':'scienceutopia.native-workflow-fixed-evaluation-audit.v1',
    'workflow-objective-development':'scienceutopia.native-workflow-objective-loop-audit.v1',
    'joint-fixed-evaluation':'scienceutopia.native-joint-fixed-evaluation-audit.v1',
    'planning-fixed-evaluation':'scienceutopia.native-planning-fixed-evaluation-audit.v1',
    'planning-objective-development':'scienceutopia.native-planning-objective-loop-audit.v1',
    'parent-presentation-development':'scienceutopia.native-parent-presentation-loop-audit.v1',
    'catalog-actuation-controls':'scienceutopia.native-catalog-actuation-audit.v1',
    'capacity-objective-development':'scienceutopia.native-capacity-objective-loop-audit.v1',
    'capacity-fixed-evaluation':'scienceutopia.native-capacity-fixed-evaluation-audit.v1',
    'instruction-timing-controls':'scienceutopia.native-instruction-timing-support-audit.v1',
    'objective-development':'scienceutopia.native-objective-instrument-loop-audit.v1',
    'fixed-evaluation':'scienceutopia.native-objective-fixed-evaluation-audit.v1',
    'resource-controls-diagnostic':'scienceutopia.native-liquidity-support-audit.v1'}


def rendered_context_proof(cell,state):
    """Exact original model-facing prefix, not an arbitrary raw-envelope match.

    Matching shows that the original rendered content occurs in a completed
    request. Shared content does not identify a unique actor or independent call.
    """
    from utopia.system.native_kernel import institutional_context_prompt
    from utopia.system.model_provenance_view import provenance_view
    with sqlite3.connect((cell/'replies/responses.sqlite').resolve().as_uri()+'?mode=ro',uri=True) as db:
        completed={r[0] for r in db.execute("SELECT payload_sha FROM replies WHERE outcome='response'")}
    wire_path=cell/'wire-requests.jsonl'
    if not wire_path.is_file() and completed:raise ValueError('completed scientist replies without original wire journal')
    wires=[json.loads(line) for line in wire_path.read_text().splitlines()] if wire_path.is_file() else []
    if any(digest(w['payload'])!=w['payload_sha256'] for w in wires):raise ValueError('literal HTTP payload hash differs')
    agents={a['id']:a for a in state['ecosystem_data']['agents']};rows=[];prefixes=[]
    for actor,a in agents.items():
        messages=a.get('institutional_context',[]);found={i:set() for i in range(len(messages))}
        for n in range(1,len(messages)+1):
            prefix=messages[:n];rendered=institutional_context_prompt(SimpleNamespace(institutional_context=prefix))
            view,inverse=provenance_view(prefix)
            matches=sorted({w['payload_sha256'] for w in wires if w['payload_sha256'] in completed
                and any(isinstance(m.get('content'),str) and rendered in m['content'] for m in w['payload'].get('messages',[]))})
            for i in range(n):found[i].update(matches)
            prefixes.append({'actor_id':actor,'messages_in_prefix':n,'raw_prefix_sha256':digest(prefix),
                'original_rendered_utf8_sha256':hashlib.sha256(rendered.encode()).hexdigest(),
                'model_view_sha256':digest(view),'inverse_alias_map_sha256':digest(inverse),
                'matching_completed_payload_sha256s':matches})
        for i,message in enumerate(messages):
            rows.append({'actor_id':actor,'message_id':message['message_id'],'source':message.get('source'),
                'received_year':message['received_year'],'literal_message_sha256':digest(message),
                'rendered_content_present_in_completed_request':bool(found[i]),
                'matching_completed_payload_sha256s':sorted(found[i])})
    delivered=[]
    for e in state['native_system']['events']:
        if e['event_type']=='native.system.context_delivered':
            for actor in e['actor_ids']:
                message=e['payload']['message'];stored=[m for m in agents[actor].get('institutional_context',[]) if m['message_id']==message['message_id']]
                if stored!=[message]:raise ValueError('actual delivered message not retained literally')
                delivered.append((actor,message['message_id']))
    if len(delivered)!=len(set(delivered)):raise ValueError('duplicate delivered recipient message')
    return {'delivered_recipient_messages':len(delivered),'all_stored_messages':rows,'original_rendered_prefixes':prefixes,
        'delivered_messages_with_rendered_content_in_completed_inputs':sum(r['rendered_content_present_in_completed_request']
            for r in rows if (r['actor_id'],r['message_id']) in set(delivered)),
        'unique_matching_completed_payloads':len({p for r in rows for p in r['matching_completed_payload_sha256s']}),
        'scope':'Exact original institutional_context_prompt on actual stored prefixes, with source-defined audit aliases only. Scientific payloads remain literal. A match is content-presence evidence, not unique actor attribution, independent calls, interpretation, causal benefit or proof of absence when unmatched.'}


def checkpoint(cell,item,system):
    matches=list(cell.rglob('portable_checkpoint_year_'+str(item['year'])+'.json.gz'))
    if len(matches)!=1 or file_sha256(matches[0])!=item['checkpoint_sha256']:
        raise ValueError('unique original audited checkpoint required')
    state=read_portable_checkpoint(matches[0])
    if (state['native_system']['spec']!=system or state['year']!=item['year'] or state['phase']!=5
            or state['native_system']['last_year']!=item['year']):raise ValueError('audited native annual identity differs')
    return state


def workflow_boundary(events, year, reconciled, categories):
    """Actual ordered phase witnesses and reconciled end-year cashflows.

    A phase's observation hash is not a recovered resource vector. This does
    not infer a within-phase attrition timestamp or treat funding summaries
    as if they were taken after later institutional mutations.
    """
    phases = [{'original_event_ordinal': i, 'event': clone(e)} for i, e in enumerate(events)
        if e['year'] == year and e['event_type'] == 'native.system.phase_executed']
    if not phases:
        raise ValueError('workflow boundary lacks original native phase witnesses')
    stages = []
    for row in phases:
        e = row['event']; p = e['payload']; stages.append(p['stage'])
        value = p['observation_sha256']
        if (not isinstance(p['stage'], str) or not p['stage'] or type(e['phase']) is not int
                or not isinstance(value, str) or len(value) != 64
                or any(c not in '0123456789abcdef' for c in value)
                or not isinstance(e['provenance']['mechanism_id'], str)):
            raise ValueError('literal audited workflow phase witness required')
    if len(stages) != len(set(stages)):
        raise ValueError('duplicate native phase witness in a workflow year')
    cash = {key: math.fsum(row[key] for row in reconciled) for key in categories}
    return {'native_phase_witnesses_in_original_order': phases,
        'all_author_cashflows': cash,
        'all_author_opening_resources': math.fsum(row['opening_balance'] for row in reconciled),
        'all_author_closing_resources': math.fsum(row['closing_balance'] for row in reconciled),
        'all_author_opening_active': sum(row['opening_active'] for row in reconciled),
        'all_author_closing_active': sum(row['closing_active'] for row in reconciled),
        'funding_stage_summary_used_as_end_year_state': False,
        'phase_resource_vectors_recovered_from_observation_hashes': False,
        'within_phase_attrition_timestamp_measured': False}


def trace_world(cell,world,source,*,workflow=False):
    proof=world['physical_proof'];system=world['system'];spec=SystemSpec.from_dict(system)
    if proof.get('status') in ('pre-response-journal-failure','technical-failure-before-initial-checkpoint'):
        return {'identity':world['identity'],'role':world['role'],'seed':world['seed'],'status':world['status'],'annual':[],
            'code_calls':[],'code_attempts':None,'reason':proof['status'],
            'causal_mechanism_effect_identified':False}
    founders=proof.get('world_conditions_proof',{}).get('actual_author_resources')
    if founders is None:raise ValueError('actual original-founder proof required')
    annual=[];previous=[];last=None
    for item in proof['annual_checkpoints']:
        state=checkpoint(cell,item,system);year=item['year'];last=state
        authors=[a for a in state['ecosystem_data']['agents'] if a['can_author']]
        by={a['id']:a for a in authors}
        if len(by)!=len(authors) or not set(founders)<=set(by):raise ValueError('original founder identities absent or duplicated')
        actors={k:SimpleNamespace(id=k,can_author=True,resources=a['resources'],is_active=a['is_active']) for k,a in by.items()}
        ledger=ResourceLedger(state['resource_ledger']);reconciled=ledger.reconcile(year,actors,require_closed=True)
        events=state['native_system']['events']
        if events[:len(previous)]!=previous:raise ValueError('actual annual event prefix changed')
        previous=events;transfers=[e for e in events if e['year']==year and e['event_type']=='native.system.resource_transferred']
        for e in transfers:
            p=e['payload']
            if (p['actual_debit']<=0 or p['actual_debit']!=p['actual_credit']
                    or math.fsum(p['balances_before'].values())!=math.fsum(p['balances_after'].values())):
                raise ValueError('native conserving transfer legs differ')
        actual=[{k:clone(by[identity][k]) for k in ('id','resources','is_active')} for identity in sorted(founders)]
        if any(type(a['is_active']) is not bool or not math.isfinite(a['resources']) for a in actual):
            raise ValueError('literal founder boundary states required')
        annual.append({'year':year,'checkpoint_sha256':item['checkpoint_sha256'],'founders':actual,
            'active_founders':sum(a['is_active'] for a in actual),'total_founder_resources':math.fsum(a['resources'] for a in actual),
            'minimum_founder_resources':min(a['resources'] for a in actual),'all_author_ledger':reconciled,
            'transfer_events':clone(transfers),'transferred_units':math.fsum(e['payload']['actual_debit'] for e in transfers),
            'actual_event_counts':dict(sorted(Counter(e['event_type'] for e in events if e['year']==year).items()))})
        if workflow:
            annual[-1]['workflow_boundary'] = workflow_boundary(events, year, reconciled, ledger.categories)
    binding={'source_commit':source,'system_fingerprint':spec.fingerprint,'run_id':cell.name}
    path=cell/'code-contexts.jsonl'
    rows=[validate_record(json.loads(line)) for line in path.read_text().splitlines()] if path.exists() else []
    if any(r['binding']!=binding for r in rows):raise ValueError('native code input source/system/run differs')
    if last is None and proof.get('checkpoint_sha256'):
        initial=list(cell.rglob('portable_checkpoint_year_0.json.gz'))
        if len(initial)!=1 or file_sha256(initial[0])!=proof['checkpoint_sha256']:raise ValueError('original partial initial checkpoint required')
        last=read_portable_checkpoint(initial[0])
    calls=[];nodes={n.mechanism_id:n for n in native_execution_nodes(spec) if n.implementation=='code.python.v1'}
    events={e['event_id']:e for e in ([] if last is None else last['native_system']['events']) if e['event_type']=='generated.code_executed'}
    code=proof.get('code_proof',{})
    if rows and (code.get('recorded_executions')!=len(rows) or len(code.get('physical_records',[]))!=len(rows)):
        raise ValueError('original physical code proof required for all recorded calls')
    for i,r in enumerate(rows):
        active=[n for n in nodes.values() if n.parameters['code_artifact']==r['artifact']
            and n.parameters['runtime_image_id']==r['receipt']['image_id']
            and {k:v for k,v in n.parameters.items() if k not in ('code_artifact','runtime_image_id')}==r['context']['parameters']]
        matching=[identity for identity,e in events.items() if e['provenance']['mechanism_id'] in {n.mechanism_id for n in active}
            and e['year']==r['context']['period'] and all(e['payload'].get(k)==r['receipt'][k]
                for k in ('image_id','artifact_sha256','context_sha256','result_sha256'))]
        physical=code['physical_records'][i]
        if (not active or physical['index']!=i or physical['bundle_sha256']!=r['bundle_sha256']
                or physical['year']!=r['context']['period'] or physical['matching_event_ids']!=matching):
            raise ValueError('literal active/delegated source and physical event attribution differ')
        inputs=[{'port':port,'source_mechanism':v['source_mechanism'],'emitted_period':v['emitted_period'],
            'payload_sha256':digest(v['payload']),'actor_ids':clone(v['actor_ids']),'artifact_ids':clone(v['artifact_ids'])}
            for port,values in r['context']['inputs'].items() for v in values]
        calls.append({'possible_declared_node_ids':[n.mechanism_id for n in active],
            'committed_node_ids':sorted({events[k]['provenance']['mechanism_id'] for k in matching}),
            'year':r['context']['period'],'context_phase':r['context']['phase'],
            'matching_event_ids':matching,'attribution':physical['attribution'],
            'bundle_sha256':r['bundle_sha256'],'bundle_ordinal':i,'source_utf8_sha256':hashlib.sha256(r['artifact']['source'].encode()).hexdigest(),
            'artifact_sha256':r['receipt']['artifact_sha256'],'input_context_sha256':r['receipt']['context_sha256'],
            'result_sha256':r['receipt']['result_sha256'],'inputs_received':inputs,
            'output_counts':{k:len(v) for k,v in r['result']['outputs'].items()}})
    attempts=recorded_attempts(path,binding=binding) if path.with_name(path.name+'.attempts.jsonl').exists() else None
    if set(events)!={identity for c in calls for identity in c['matching_event_ids']}:
        raise ValueError('committed code event without a recorded physical call')
    context=proof.get('context_input_proof')
    rendered=None if last is None or not (cell/'replies/responses.sqlite').is_file() else rendered_context_proof(cell,last)
    return {'identity':world['identity'],'role':world['role'],'seed':world['seed'],'status':world['status'],
        'system_sha256':digest(system),'annual':annual,'code_calls':calls,
        'code_attempts':None if attempts is None else [{'status':a['status'],
            'intent_sha256':a['intent']['content_sha256'],'terminal':clone(a['terminal'])} for a in attempts],
        'uncommitted_recorded_bundles':[c['bundle_sha256'] for c in calls if not c['matching_event_ids']],
        'legacy_raw_envelope_substring_proof':clone(context),'original_model_facing_context_proof':rendered,
        'connections':clone(system['connections']),'schedules':clone(system['schedules']),
        'code_nodes':[{ 'node_id':k,'artifact_sha256':digest(n.parameters['code_artifact']),
            'source_utf8_sha256':hashlib.sha256(n.parameters['code_artifact']['source'].encode()).hexdigest(),
            'declared_wrapper_implementation':next(m.implementation for m in spec.mechanisms if m.mechanism_id==k),
            'committed_code_events':sum(e['provenance']['mechanism_id']==k for e in events.values()),
            'uniquely_attributed_physical_calls':sum(c['committed_node_ids']==[k] and c['attribution']=='unique-event-match' for c in calls)}
            for k,n in nodes.items()],
        'causal_mechanism_effect_identified':False,'partial_boundaries_are_not_completed_outcomes':world['status']!='complete'}


def export(args):
    root=args.run.resolve();out=args.output.resolve();source=args.frozen_source.resolve()
    if out.exists() or out.is_relative_to(root) or out.is_relative_to(source):raise ValueError('fresh trace outside scientific raw/source required')
    paths=[args.audit_one,args.audit_two,root/'plan.json'];inputs={str(p):file_sha256(p) for p in paths}
    if args.audit_one.read_bytes()!=args.audit_two.read_bytes():raise ValueError('two matching original audits required')
    audit=checked(json.loads(args.audit_one.read_text()));plan=checked(json.loads((root/'plan.json').read_text()));before=_inventory(root)
    if (audit['schema']!=SCOPES[args.scope] or audit['closure']['terminal']['status']!='closed'
            or audit['source_commit']!=plan['source_commit'] or pinned_revision(source)!=plan['source_commit']
            or audit['plan_sha256']!=plan['content_sha256'] or audit['source_proof']['status']!='verified-exact-source-closure'
            or audit['raw_inventory_sha256']!=digest(before) or audit['new_model_calls'] or audit['new_code_executions']):
        raise ValueError('matching normal-closure source/audit/raw and explicit study scope required')
    worlds=[]
    for w in audit['worlds']:
        name=w['identity']+'-s'+str(w['seed']);cells=[p for p in root.glob('**/worlds/'+name) if p.is_dir()]
        if len(cells)!=1:raise ValueError('unique audited physical world directory required')
        worlds.append(trace_world(cells[0],w,plan['source_commit'],
            workflow=args.scope in ('workflow-objective-development','workflow-fixed-evaluation',
                'longitudinal-objective-development','longitudinal-fixed-evaluation')))
    result={'schema':SCHEMA,'scope':args.scope,'source_commit':plan['source_commit'],'plan_sha256':plan['content_sha256'],
        'audit_content_sha256':audit['content_sha256'],'raw_inventory_sha256':digest(before),'worlds':worlds,
        'interpretation':{'report_only':True,'new_model_calls':0,'new_code_executions':0,'new_native_worlds':0,
            'loss_or_selection_changed':False,'causal_mechanism_effect_identified':False,
            'annual_boundaries_are_within_year_minima':False,'publication_ready':False}}
    if (before!=_inventory(root) or inputs!={str(p):file_sha256(p) for p in paths}
            or pinned_revision(source)!=plan['source_commit']):raise ValueError('trace inputs or scientific source changed')
    out.mkdir(parents=True);save(out/'report.json',result)
    rows=[{'world':w['identity'],'role':w['role'],'status':w['status'],'seed':w['seed'],
        **{k:y[k] for k in ('year','active_founders','total_founder_resources','minimum_founder_resources','transferred_units')}}
        for w in worlds for y in w['annual']]
    with (out/'annual-boundaries.csv').open('x',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['world','role','status','seed','year','active_founders','total_founder_resources','minimum_founder_resources','transferred_units'])
        writer.writeheader();writer.writerows(rows)
    save(out/'manifest.json',{'schema':SCHEMA+'.export','inputs':inputs,
        'report_file_sha256':file_sha256(out/'report.json'),'annual_file_sha256':file_sha256(out/'annual-boundaries.csv'),
        'adapter_file_sha256':file_sha256(Path(__file__)),'new_model_calls':0,'new_code_executions':0})
    print(json.dumps({'scope':args.scope,'worlds':len(worlds),'annual_boundaries':len(rows),
        'recorded_code_calls':sum(len(w['code_calls']) for w in worlds)}))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('run','frozen-source','audit-one','audit-two','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--scope',choices=tuple(SCOPES),required=True);a=p.parse_args()
    # Resolve relative caller paths before the cold child changes to the
    # original scientific checkout. Never reinterpret its output as a write
    # inside that frozen source or loosen the worker's outside-source guard.
    keys = ('run', 'frozen-source', 'audit-one', 'audit-two', 'output')
    for key in keys:
        name = key.replace('-', '_'); setattr(a, name, getattr(a, name).resolve())
    # The original scientific implementation decodes and reconciles its own
    # records; the external reader source is pinned separately by its manifest.
    import os,subprocess,sys
    if os.environ.get('SCIENCE_UTOPIA_COLD_EFFECT_TRACE_WORKER')=='1':export(a);return
    result=subprocess.run([sys.executable,'-c',
        'import runpy,sys;sys.path.insert(0,sys.argv.pop(1));runpy.run_path(sys.argv.pop(1),run_name="__main__")',
        str(a.frozen_source),str(Path(__file__).resolve()),
        *[value for key in keys for value in ('--' + key, str(getattr(a, key.replace('-', '_'))))],
        '--scope',a.scope],cwd=a.frozen_source,
        env={**os.environ,'PYTHONHASHSEED':'42','SCIENCE_UTOPIA_COLD_EFFECT_TRACE_WORKER':'1'},timeout=1800,check=False)
    if result.returncode:raise SystemExit(result.returncode)


if __name__=='__main__':main()
