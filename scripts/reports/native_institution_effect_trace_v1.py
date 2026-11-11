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
from types import SimpleNamespace

from scripts.analyze_native_open_v7 import _inventory
from utopia.funding.accounting import ResourceLedger
from utopia.optimization.native_code_trace import validate_record,recorded_attempts
from utopia.optimization.native_jobs import pinned_revision
from utopia.optimization.native_numeric_designer import checked,save
from utopia.runtime.checkpointing import read_portable_checkpoint
from utopia.system import SystemSpec
from utopia.system.design_patch import clone,digest
from utopia.utils.data_utils import file_sha256

SCHEMA='scienceutopia.native-institution-effect-trace.v1'
SCOPES={
    'objective-development':'scienceutopia.native-objective-instrument-loop-audit.v1',
    'fixed-evaluation':'scienceutopia.native-objective-fixed-evaluation-audit.v1',
    'resource-controls-diagnostic':'scienceutopia.native-liquidity-support-audit.v1'}


def checkpoint(cell,item,system):
    matches=list(cell.rglob('portable_checkpoint_year_'+str(item['year'])+'.json.gz'))
    if len(matches)!=1 or file_sha256(matches[0])!=item['checkpoint_sha256']:
        raise ValueError('unique original audited checkpoint required')
    state=read_portable_checkpoint(matches[0])
    if (state['native_system']['spec']!=system or state['year']!=item['year'] or state['phase']!=5
            or state['native_system']['last_year']!=item['year']):raise ValueError('audited native annual identity differs')
    return state


def trace_world(cell,world,source):
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
    binding={'source_commit':source,'system_fingerprint':spec.fingerprint,'run_id':cell.name}
    path=cell/'code-contexts.jsonl'
    rows=[validate_record(json.loads(line)) for line in path.read_text().splitlines()] if path.exists() else []
    if any(r['binding']!=binding for r in rows):raise ValueError('native code input source/system/run differs')
    remaining=list(enumerate(rows));calls=[];mechanisms={m['mechanism_id']:m for m in system['mechanisms']}
    for e in ([] if last is None else last['native_system']['events']):
        if e['event_type']!='generated.code_executed':continue
        node=e['provenance']['mechanism_id'];declared=mechanisms[node]['parameters']['code_artifact']
        match=next(((i,r) for i,r in remaining if all(r['receipt'].get(k)==v for k,v in e['payload'].items())
            and r['artifact']==declared and r['context']['period']==e['year'] and r['context']['phase']==e['phase']),None)
        if match is None:raise ValueError('committed code event has no exact received input/result bundle')
        remaining.remove(match);i,r=match
        inputs=[{'port':port,'source_mechanism':v['source_mechanism'],'emitted_period':v['emitted_period'],
            'payload_sha256':digest(v['payload']),'actor_ids':clone(v['actor_ids']),'artifact_ids':clone(v['artifact_ids'])}
            for port,values in r['context']['inputs'].items() for v in values]
        calls.append({'node_id':node,'year':e['year'],'phase':e['phase'],'event_id':e['event_id'],
            'bundle_sha256':r['bundle_sha256'],'bundle_ordinal':i,'source_utf8_sha256':hashlib.sha256(r['artifact']['source'].encode()).hexdigest(),
            'artifact_sha256':r['receipt']['artifact_sha256'],'input_context_sha256':r['receipt']['context_sha256'],
            'result_sha256':r['receipt']['result_sha256'],'inputs_received':inputs,
            'output_counts':{k:len(v) for k,v in r['result']['outputs'].items()}})
    attempts=recorded_attempts(path,binding=binding) if path.with_name(path.name+'.attempts.jsonl').exists() else None
    if world['status']=='complete' and remaining:raise ValueError('completed world has uncommitted recorded code calls')
    context=proof.get('context_input_proof')
    return {'identity':world['identity'],'role':world['role'],'seed':world['seed'],'status':world['status'],
        'system_sha256':digest(system),'annual':annual,'code_calls':calls,
        'code_attempts':None if attempts is None else [{'status':a['status'],
            'intent_sha256':a['intent']['content_sha256'],'terminal':clone(a['terminal'])} for a in attempts],
        'uncommitted_recorded_bundles':[{'ordinal':i,'bundle_sha256':r['bundle_sha256'],
            'artifact_sha256':r['receipt']['artifact_sha256'],'period':r['context']['period']} for i,r in remaining],
        'received_context_proof':clone(context),'connections':clone(system['connections']),'schedules':clone(system['schedules']),
        'code_nodes':[{ 'node_id':k,'artifact_sha256':digest(m['parameters']['code_artifact']),
            'source_utf8_sha256':hashlib.sha256(m['parameters']['code_artifact']['source'].encode()).hexdigest(),
            'committed_native_invocations':sum(c['node_id']==k for c in calls)}
            for k,m in mechanisms.items() if m['implementation']=='code.python.v1'],
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
        worlds.append(trace_world(cells[0],w,plan['source_commit']))
    result={'schema':SCHEMA,'scope':args.scope,'source_commit':plan['source_commit'],'plan_sha256':plan['content_sha256'],
        'audit_content_sha256':audit['content_sha256'],'raw_inventory_sha256':digest(before),'worlds':worlds,
        'interpretation':{'report_only':True,'new_model_calls':0,'new_code_executions':0,'new_native_worlds':0,
            'loss_or_selection_changed':False,'causal_mechanism_effect_identified':False,
            'annual_boundaries_are_within_year_minima':False,'publication_ready':False}}
    if before!=_inventory(root) or inputs!={str(p):file_sha256(p) for p in paths}:raise ValueError('trace inputs changed')
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
        'committed_code_calls':sum(len(w['code_calls']) for w in worlds)}))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for key in ('run','frozen-source','audit-one','audit-two','output'):p.add_argument('--'+key,type=Path,required=True)
    p.add_argument('--scope',choices=tuple(SCOPES),required=True);a=p.parse_args()
    # The original scientific implementation decodes and reconciles its own
    # records; the external reader source is pinned separately by its manifest.
    import os,subprocess,sys
    if os.environ.get('SCIENCE_UTOPIA_COLD_EFFECT_TRACE_WORKER')=='1':export(a);return
    result=subprocess.run([sys.executable,'-c',
        'import runpy,sys;sys.path.insert(0,sys.argv.pop(1));runpy.run_path(sys.argv.pop(1),run_name="__main__")',
        str(a.frozen_source.resolve()),str(Path(__file__).resolve()),*sys.argv[1:]],cwd=a.frozen_source,
        env={**os.environ,'PYTHONHASHSEED':'42','SCIENCE_UTOPIA_COLD_EFFECT_TRACE_WORKER':'1'},timeout=1800,check=False)
    if result.returncode:raise SystemExit(result.returncode)


if __name__=='__main__':main()
