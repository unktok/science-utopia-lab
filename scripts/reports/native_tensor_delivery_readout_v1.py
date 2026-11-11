"""Cold original authoring replay plus a separate recorded-output diagnostic.

The original scientific writer may continue in other slots. No original
feedback, source, candidate, loss or component verdict is modified.
"""
import argparse
import json
from pathlib import Path
import re
import subprocess
import sys

from scripts.analyze_native_open_v7 import _inventory
from scripts.finish_native_institution_loop_v1 import git_binding
from utopia.optimization.native_numeric_designer import checked,save
from utopia.optimization.native_post_edit_feedback_v1 import code_nodes
from utopia.optimization.native_tensor_delivery_diagnostics_v1 import diagnose,source_hashes
from utopia.system.code_mechanisms import sha
from utopia.system.design_patch import digest
from utopia.utils.data_utils import file_sha256

ROOT=Path(__file__).resolve().parents[2]
SCHEMA='scienceutopia.native-tensor-delivery-readout.v1'


def closed_record(root,objective,generation):
    state=json.loads((root/'search'/objective/'campaign/native-adaptive-state.json').read_text())
    if type(generation) is not int or not 0<=generation<len(state['records']):
        raise ValueError('an actually closed own proposal record is required')
    record=state['records'][generation]
    if (record['definition'] is None or record['generation_error'] is not None
            or len(record['draws'])!=1 or not record['draws'][0].get('suggestion')
            or record['request_sha256']!=digest(record['request'])
            or not re.fullmatch('[a-f0-9]{64}',record['request_sha256'])):
        raise ValueError('literal submitted and compiled original proposal required')
    return record


def probe_owners(step):
    """Use explicit probe pointers; identical source is not node attribution."""
    result={}
    tests=step.get('transition',{}).get('result',{}).get('component_feedback',{}).get('tests',[])
    for test in tests:
        for value in test['results']:
            match=re.fullmatch('/component_probe_records/([0-9]+)',value['exact_step_probe_pointer'])
            if match:result.setdefault(int(match[1]),set()).add(test['node_id'])
    return {key:sorted(value) for key,value in result.items()}


def export(args):
    root=args.run.resolve();out=args.output.resolve();frozen=args.frozen_source.resolve();reader=git_binding(ROOT)
    if out.exists() or out.is_relative_to(root) or out.is_relative_to(frozen):raise ValueError('fresh external diagnostic output required')
    plan=checked(json.loads((root/'plan.json').read_text()));scientific=git_binding(frozen)
    if (plan['schema']!='scienceutopia.native-objective-instrument-loop.v1.plan' or plan['source_commit']!=scientific
            or args.objective not in plan['objectives']):raise ValueError('matching original scientific source and objective required')
    record=closed_record(root,args.objective,args.generation);record_hash=digest(record);plan_hash=file_sha256(root/'plan.json')
    generation=root/'search'/args.objective/'authoring'/('generation-'+record['request_sha256'])
    before=_inventory(generation);intent=checked(json.loads((generation/'intent.json').read_text()))
    if intent['request']!=record['request'] or intent['source_commit']!=scientific:
        raise ValueError('exact original authoring request required')
    # Only trusted original orchestration is imported. Its cold executor is
    # forbidden by replay; no authored Python or tensor body runs here.
    command=[sys.executable,'-c',
        'import json,sys; from pathlib import Path; '
        'from utopia.optimization import native_bounded_staged_designer as m; '
        'from utopia.system.design_patch import digest; '
        'assert Path(m.__file__).resolve().is_relative_to(Path.cwd()); '
        'print(json.dumps({"definition_sha256":digest(m.replay(Path(sys.argv[1])))}))',str(generation)]
    proof=json.loads(subprocess.check_output(command,cwd=frozen,text=True,timeout=300))
    if proof['definition_sha256']!=digest(record['definition']):raise ValueError('original cold definition differs from controller record')
    system=record['draws'][0]['suggestion']['candidate'];artifacts=code_nodes(system).get(args.producer,[])
    if len(artifacts)!=1:raise ValueError('unique literal final producer artifact required')
    artifact_sha=sha(artifacts[0]);inner=generation/'authoring'/('generation-'+record['request_sha256']);rows=[]
    for path in sorted(inner.glob('step-*.completed.json')):
        step=checked(json.loads(path.read_text()));owners=probe_owners(step)
        for index,probe in enumerate(step.get('component_probe_records',[])):
            received=probe['terminal'];same=sha(probe['intent']['artifact'])==artifact_sha
            attributed=owners.get(index,[])==[args.producer]
            row={'step':step['step'],'probe_in_step':index,'fixture_id':probe['intent']['fixture_id'],
                'actual_probe_status':received['status'],'probe_artifact_sha256':sha(probe['intent']['artifact']),
                'explicit_probe_producer_ids':owners.get(index,[]),'unambiguous_producer_match':attributed,
                'final_producer_artifact_match':same,'diagnostic':None}
            if same and attributed and received['status']=='returned':row['diagnostic']=diagnose(system,args.producer,received['result'])
            else:row['not_assessed_reason']='different-artifact-nonreturned-or-not-uniquely-attributed-probe'
            rows.append(row)
    result={'schema':SCHEMA,'scientific_source_commit':scientific,'analysis_source_commit':reader,
        'plan_sha256':plan['content_sha256'],'objective':args.objective,'generation':args.generation,
        'original_request_sha256':record['request_sha256'],'original_record_sha256':record_hash,
        'original_cold_replay':proof,'original_authoring_inventory_sha256':digest(before),
        'original_candidate_sha256':digest(system),'producer_id':args.producer,'final_producer_artifact_sha256':artifact_sha,
        'diagnostic_source_sha256':source_hashes(),'probes':rows,
        'original_probe_calls':len(rows),'final_artifact_probes':sum(r['final_producer_artifact_match'] for r in rows),
        'original_feedback_or_verdicts_rewritten':False,'presented_to_original_designer':False,
        'original_record_and_archive_unchanged':True,'original_scientific_run_restarted':False,
        'new_model_calls':0,'new_source_executions':0,'new_tensor_body_executions':0,'new_native_worlds':0,
        'is_original_native_world_audit':False,'loss_changed':False,'publication_ready':False,
        'scope':'Retrospective direct declared tensor-input compatibility of actual final-artifact component replies. '
            'Original cold authoring replay is separate from this new diagnostic. Other original slots may continue; '
            'their histories and whole-world losses are not newly audited or changed. No diagnostic was supplied '
            'to the historical designer; no repair benefit or experimental method effect is established.'}
    if (before!=_inventory(generation) or record_hash!=digest(closed_record(root,args.objective,args.generation))
            or plan_hash!=file_sha256(root/'plan.json') or git_binding(frozen)!=scientific or git_binding(ROOT)!=reader):
        raise ValueError('original closed record/archive, plan or sources changed')
    out.mkdir(parents=True);save(out/'report.json',result)
    save(out/'manifest.json',{'schema':SCHEMA+'.export','analysis_source_commit':reader,
        'scientific_source_commit':scientific,'original_record_sha256':record_hash,
        'original_authoring_inventory_sha256':digest(before),'plan_file_sha256':plan_hash,
        'report_file_sha256':file_sha256(out/'report.json'),'new_model_calls':0,'new_source_executions':0})
    print(json.dumps({'original_probes':len(rows),'same_final_artifact':result['final_artifact_probes'],
        'declared_input_statuses':[d['status'] for r in rows if r['diagnostic'] for d in r['diagnostic']['rows']]}))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('run','frozen-source','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--objective',default='content-utility');p.add_argument('--generation',type=int,default=0)
    p.add_argument('--producer',default='native-feature-extractor');export(p.parse_args())


if __name__=='__main__':main()
