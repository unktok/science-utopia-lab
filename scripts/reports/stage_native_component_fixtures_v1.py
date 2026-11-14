"""Stage actual developer inputs for optional component tests; no execution.

The child imports the unchanged original scientific source. Only fully audited
developer references enter the fixture bank; no evaluation-seed data is read.
"""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

REFERENCES = ('open-seed','reviewed-accept-all','routed-one-accept-all')
NODES = ('world.selection','native-feature-extractor')
LIQUIDITY_SCOPE='liquidity-four-world-v2'
LEGACY_SCOPE='historical-three-references-v1'
LIQUIDITY_REFERENCES=('resource-30-disconnected','resource-30-connected','resource-60-connected','resource-60-disconnected')
LIQUIDITY_NODES=(*NODES,'developer-liquidity-director')
WORKFLOW_SCOPE='open-workflow-r7-v1'
WORKFLOW_REFERENCES=('R7-original',)
WORKFLOW_NODES=(*LIQUIDITY_NODES,'information-office','developer-catalog-agenda')


def stage(run, audit_path, output,*,scope=LEGACY_SCOPE):
    from scripts.analyze_native_open_v7 import _inventory
    from utopia.optimization.native_code_trace import validate_record
    from utopia.optimization.native_jobs import pinned_revision
    from utopia.optimization.native_numeric_designer import checked, save
    from utopia.system import SystemSpec
    from utopia.system.design_patch import digest
    from utopia.utils.data_utils import file_sha256
    run, output, source = Path(run).resolve(), Path(output).resolve(), Path.cwd()
    if output.exists() or output.is_relative_to(run) or output.is_relative_to(source):
        raise ValueError('fresh fixture output outside historical source/raw required')
    audit_hash=file_sha256(audit_path);a=checked(json.loads(Path(audit_path).read_text()))
    p=checked(json.loads((run/'plan.json').read_text()));before=_inventory(run)
    if scope not in (LEGACY_SCOPE,LIQUIDITY_SCOPE,WORKFLOW_SCOPE):raise ValueError('explicit developer staging scope required')
    liquidity=scope==LIQUIDITY_SCOPE
    workflow=scope==WORKFLOW_SCOPE
    references=WORKFLOW_REFERENCES if workflow else LIQUIDITY_REFERENCES if liquidity else REFERENCES
    nodes_requested=WORKFLOW_NODES if workflow else LIQUIDITY_NODES if liquidity else NODES
    expected_schema=('scienceutopia.native-workflow-objective-loop-audit.v1' if workflow else
        'scienceutopia.native-liquidity-support-audit.v1' if liquidity else 'scienceutopia.native-institution-loop-stopped-audit.v1')
    if (a['schema']!=expected_schema
            or p['source_commit']!=pinned_revision(source) or a['source_commit']!=p['source_commit']
            or a['plan_sha256']!=p['content_sha256'] or digest(before)!=a['raw_inventory_sha256']
            or a['closure']['terminal']['status']!=('closed' if liquidity or workflow else 'stopped')
            or a['source_proof']['status']!='verified-exact-source-closure'):
        raise ValueError('exact audited historical developer prefix required')
    if liquidity and (len(a['worlds'])!=4 or a['closure']['terminal']['complete_worlds']!=4
            or {j['identity'] for j in p['jobs']}!=set(references)):
        raise ValueError('exact four normally closed developer resource worlds required')
    if workflow:
        from scripts.run_native_workflow_objective_loop_v1 import open_institutions, SCHEMA
        if (p['schema']!=SCHEMA+'.plan' or not open_institutions(p)
                or p.get('optimizer_reference_labels')!=list(WORKFLOW_REFERENCES)):
            raise ValueError('explicit open workflow with only original R7 optimizer reference required')
    records=[];origins=[]
    for reference in references:
        identity=('workflow-reference-'+reference.lower() if workflow else
            reference if liquidity else 'reference-'+reference)
        role='developer-liquidity-control' if liquidity else 'developer-reference'
        matches=[w for w in a['worlds'] if w['identity']==identity and w['role']==role]
        if len(matches)!=1 or matches[0]['status']!='complete':raise ValueError('complete developer reference required')
        w=matches[0];spec=SystemSpec.from_dict(w['system']);proof=w['physical_proof']['code_proof']
        cell=run/('worlds-by-job' if liquidity else 'references')/reference/'worlds'/(identity+'-s'+str(w['seed']));path=cell/'code-contexts.jsonl'
        if (w['seed']!=61001 or proof['one_to_one_physical_execution_proven'] is not True
                or file_sha256(path)!=proof['code_contexts_sha256']):
            raise ValueError('developer input file differs from original physical proof')
        rows=[validate_record(json.loads(line)) for line in path.read_text().splitlines()]
        physical={r['index']:r for r in proof['physical_records']}
        if len(rows)!=proof['recorded_executions'] or len(physical)!=len(rows):
            raise ValueError('developer component execution count differs')
        selected_nodes=set()
        for i,row in enumerate(rows):
            expected={'source_commit':p['source_commit'],'system_fingerprint':spec.fingerprint,'run_id':cell.name}
            receipt=physical[i]
            if (row['binding']!=expected or receipt['bundle_sha256']!=row['bundle_sha256']
                    or receipt['attribution']!='unique-event-match' or len(receipt['matching_event_ids'])!=1
                    or receipt['year']!=row['context']['period']):
                raise ValueError('component input has no exact uniquely attributed native execution')
            nodes=[n.mechanism_id for n in spec.mechanisms if n.parameters.get('code_artifact')==row['artifact']]
            # Intrinsic native handlers can delegate their own container code
            # without storing code_artifact on a graph node. They are outside
            # this explicitly declared bank, not evidence of an ambiguous selected node.
            if not any(node in nodes_requested for node in nodes):continue
            if len(nodes)!=1:raise ValueError('component artifact has ambiguous node identity')
            selected_nodes.add(nodes[0])
            records.append(row);origins.append({'bundle_sha256':row['bundle_sha256'],'node_id':nodes[0],
                'reference':reference,'seed':w['seed'],'year':row['context']['period'],
                'code_file_sha256':proof['code_contexts_sha256'],'native_event_id':receipt['matching_event_ids'][0]})
        if selected_nodes!=set(nodes_requested):raise ValueError('a requested native component has no exact recorded input')
        if (liquidity or workflow) and any(sorted(o['year'] for o in origins if o['reference']==reference and o['node_id']==node)!=[1,2,3,4]
                for node in nodes_requested):raise ValueError('four exact yearly developer contexts per node required')
    if (before!=_inventory(run) or file_sha256(audit_path)!=audit_hash or pinned_revision(source)!=p['source_commit']):
        raise ValueError('historical source/audit/raw changed while staging component fixtures')
    result={'schema':'scienceutopia.native-component-fixtures.v1','source_commit':p['source_commit'],
        'historical_audit_content_sha256':a['content_sha256'],'historical_audit_file_sha256':audit_hash,
        'raw_inventory_sha256':a['raw_inventory_sha256'],'references':list(references),'nodes':list(nodes_requested),
        'records':records,'origins':origins,'new_model_calls':0,'new_code_executions':0,
        'scope':'Exact successful developer component inputs, not failed-call reconstructions, new worlds or held-out data'}
    if liquidity:
        result.update(post_edit_reference='resource-30-connected',post_edit_probe_scope='declared-sixtyfour-v2')
    if workflow:
        result.update(post_edit_reference='R7-original',post_edit_probe_scope='declared-sixtyfour-v2')
    save(output,result)


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('run','audit','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--frozen-source',type=Path);p.add_argument('--worker',action='store_true')
    p.add_argument('--scope',choices=(LEGACY_SCOPE,LIQUIDITY_SCOPE,WORKFLOW_SCOPE),default=LEGACY_SCOPE);a=p.parse_args()
    if a.worker:stage(a.run,a.audit,a.output,scope=a.scope);return
    from utopia.optimization.native_component_lab_v1 import fixture_bank
    from utopia.optimization.native_jobs import pinned_revision
    from utopia.optimization.native_numeric_designer import checked,save
    from utopia.utils.data_utils import file_sha256
    root=Path(__file__).resolve().parents[2];revision=pinned_revision(root)
    if (a.frozen_source is None or a.output.exists() or a.output.resolve().is_relative_to(a.run.resolve())
            or a.output.resolve().is_relative_to(a.frozen_source.resolve())):
        raise ValueError('fresh output outside historical source/raw and frozen native source required')
    a.output.mkdir(parents=True)
    command=[sys.executable,'-c',
        'import runpy,sys; sys.path.insert(0,sys.argv.pop(1)); runpy.run_path(sys.argv.pop(1),run_name="__main__")',
        str(a.frozen_source.resolve()),str(Path(__file__).resolve()),'--worker',
        '--run',str(a.run.resolve()),'--audit',str(a.audit.resolve()),'--output',str((a.output/'fixtures.json').resolve())]
    if a.scope!=LEGACY_SCOPE:command.extend(['--scope',a.scope])
    result=subprocess.run(command,cwd=a.frozen_source.resolve(),env={**os.environ,'PYTHONHASHSEED':'42'},timeout=900,check=False)
    if result.returncode:raise SystemExit(result.returncode)
    bank=checked(json.loads((a.output/'fixtures.json').read_text()));fixtures=fixture_bank(bank['records'])
    if pinned_revision(root)!=revision:raise ValueError('component-lab source changed during staging')
    summary={'schema':'scienceutopia.native-component-fixtures-summary.v1','lab_source_commit':revision,
        'scientific_source_commit':bank['source_commit'],'bank_file_sha256':file_sha256(a.output/'fixtures.json'),
        'bank_content_sha256':bank['content_sha256'],'historical_audit_content_sha256':bank['historical_audit_content_sha256'],
        'recorded_inputs':len(bank['records']),'unique_fixtures':len(fixtures),
        'references':bank['references'],'nodes':bank['nodes'],'seeds':[61001],
        'node_counts':{n:sum(r['node_id']==n for r in bank['origins']) for n in bank['nodes']},
        'fixture_origins':bank['origins'],'new_model_calls':0,'new_code_executions':0,
        'designer_tool_connected':False,'real_component_probe_executed':False}
    if a.scope!=LEGACY_SCOPE:summary.update(staging_scope=a.scope,post_edit_reference=bank['post_edit_reference'],
        post_edit_probe_scope=bank['post_edit_probe_scope'])
    saved=save(a.output/'summary.json',summary)
    print(json.dumps({k:saved[k] for k in ('content_sha256','recorded_inputs','unique_fixtures','node_counts',
        'new_model_calls','new_code_executions')}),flush=True)


if __name__=='__main__':main()
