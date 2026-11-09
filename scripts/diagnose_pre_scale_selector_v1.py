"""Replay recorded M selector traces with the ORIGINAL closed-study compiler.

No intervention, counterfactual science, model, Docker or generated Python.
The fixed developer selector is inspected separately from information delivery.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys


def selector_statistics(program,frames):
    import torch
    from utopia.system.tensor_program import execute_tensor_program
    from utopia.system.design_patch import digest
    if [v['year'] for v in frames]!=[1,2,3,4]:raise ValueError('four ordered recorded annual selector frames required')
    if program['inputs']!={'features':[-1,2]}:raise ValueError('this diagnostic is scoped to the recorded two-feature selector')
    if frames[0]['trace']['state_before']!=program['state']:raise ValueError('selector trace does not begin at original initial memory')
    scores=[];thresholds=[];margins=[];reviews=[];accepts=[];previous=None
    for frame in frames:
        trace=frame['trace']
        if trace['program_sha256']!=digest(program) or trace['mode']!='hard':
            raise ValueError('recorded hard selector program differs')
        if previous is not None and trace['state_before']!=previous:raise ValueError('selector memory continuity differs')
        inputs={'features':torch.tensor(trace['inputs']['features'],dtype=torch.float64).reshape(-1,2)}
        state={k:torch.tensor(v,dtype=torch.float64) for k,v in trace['state_before'].items()}
        output,updates=execute_tensor_program(program,inputs,state=state,hard=True)
        as_json=lambda values:{k:v.detach().tolist() for k,v in values.items()}
        if as_json(output)!=trace['outputs'] or as_json(updates)!=trace['state_after']:
            raise ValueError('recorded selector outputs or memory do not match original hard replay')
        previous=trace['state_after'];features=trace['inputs']['features']
        addresses=trace['outputs']['addresses'];decisions=trace['outputs']['accept']
        if len(trace['records'])!=len(features):raise ValueError('record identity count differs')
        if len(addresses)!=len(features) or len(decisions)!=len(features):raise ValueError('recorded decisions lose feature alignment')
        for row,address,decision in zip(features,addresses,decisions):
            threshold=sum(w*t[0] for w,t in zip(address,program['parameters']['thresholds']))
            threshold+=program['parameters']['bias']+trace['state_before']['accepted_so_far']*program['parameters']['memory_cost']
            scores.append(row[0]);reviews.append(row[1]);thresholds.append(threshold)
            margins.append(row[0]-threshold);accepts.append(decision)
    bounds=lambda values:[min(values),max(values)] if values else None
    return {'annual_frames':len(frames),'feature_rows':len(scores),'score_range':bounds(scores),
        'selected_effective_threshold_range':bounds(thresholds),'margin_range':bounds(margins),
        'recorded_review_count_sum':sum(reviews),'recorded_accept_output_sum':sum(accepts),
        'every_observed_record_strictly_below_threshold':bool(margins) and max(margins)<0,
        'all_observed_accept_outputs_zero':bool(accepts) and all(v==0 for v in accepts),
        'empty_record_set':not scores,'original_hard_outputs_and_memory_replayed':True}


def worker(run,audit_path,output):
    from scripts.analyze_native_open_v7 import _inventory
    from utopia.optimization.native_numeric_designer import checked
    from utopia.optimization.native_designer_preflight import runtime_binding
    from utopia.optimization.native_jobs import pinned_revision
    from utopia.runtime.checkpointing import read_portable_checkpoint
    from utopia.system.native_tensor_examples import addressed_selection_program
    from utopia.system.design_patch import digest
    from utopia.utils.data_utils import file_sha256,write_json_atomic
    run=Path(run).resolve();output=Path(output).resolve();root=Path.cwd()
    if output.exists() or output.is_relative_to(run) or output.is_relative_to(root):
        raise ValueError('fresh diagnostic output outside raw/frozen source required')
    plan=checked(json.loads((run/'plan.json').read_text()))
    audit=checked(json.loads(Path(audit_path).read_text()))
    if (audit['schema']!='scienceutopia.pre-scale-information-audit.v1'
            or audit['source_commit']!=plan['source_commit'] or audit['plan_sha256']!=plan['content_sha256']
            or pinned_revision(root)!=plan['source_commit'] or runtime_binding()!=plan['runtime']
            or not (run/'mechanisms-complete.json').exists() or len(audit['rows'])!=12):
        raise ValueError('closed exact original-source M audit required')
    before=_inventory(run)
    if digest(before)!=audit['raw_inventory_sha256']:raise ValueError('raw input changed from closed audit')
    program=addressed_selection_program();program_sha=digest(program);rows=[]
    for row in audit['rows']:
        observation_path=run/'mechanisms'/row['id']/'observation.json'
        if file_sha256(observation_path)!=row['observation_file_sha256']:raise ValueError('original observation changed')
        observation=checked(json.loads(observation_path.read_text()));receipt=observation['metadata']['runs'][0]
        path=Path(receipt['checkpoint_path'])
        if file_sha256(path)!=row['physical_proof']['checkpoint_sha256']:raise ValueError('original checkpoint changed')
        state=read_portable_checkpoint(path);native=state['native_system']
        candidates=[n for n in native['spec']['mechanisms'] if n['parameters'].get('program')==program]
        if len(candidates)!=1 or candidates[0]['mechanism_id']!='addressed-selection':
            raise ValueError('diagnostic does not cover a modified/different selector')
        frames=[{'year':event['year'],'trace':event['payload']} for event in native['events']
            if event['event_type']=='native.tensor.executed' and event['payload']['program_sha256']==program_sha]
        stats=selector_statistics(program,frames);metrics=row['measurement']['metrics']
        if (stats['recorded_accept_output_sum']!=metrics['native.accepted_decisions']['value']
                or stats['recorded_review_count_sum']!=metrics['native.review_records']['value']
                or stats['feature_rows']!=metrics['native.accepted_decisions']['value']+metrics['native.rejected_decisions']['value']):
            raise ValueError('recorded selector frames do not cover actual native decisions/reviews')
        rows.append({'id':row['id'],'condition':row['condition'],'seed':row['seed'],**stats})
    if before!=_inventory(run):raise ValueError('raw scientific data changed during read-only diagnostic')
    result={'schema':'scienceutopia.pre-scale-selector-diagnostic.v1','source_commit':plan['source_commit'],
        'input_full_audit_sha256':audit['content_sha256'],'plan_sha256':plan['content_sha256'],
        'selector_program_sha256':program_sha,'rows':rows,'raw_inventory_sha256':digest(before),
        'analysis_adapter_sha256':file_sha256(Path(__file__)),
        'scope':'Original hard tensor traces/memory only, with unchanged features. Not an institutional intervention, native counterfactual or optimizer result.',
        'new_model_calls':0,'new_code_executions':0,'new_native_worlds':0,'scientific_benefit_claimed':False}
    result['content_sha256']=digest(result)
    write_json_atomic(output,result,sort_keys=True,allow_nan=False)
    print(json.dumps({'output':str(output),'content_sha256':result['content_sha256'],'closed_cells':len(rows)}))


def main():
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('run','audit','output'):p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--frozen-source',type=Path);p.add_argument('--worker',action='store_true');a=p.parse_args()
    if a.worker:worker(a.run,a.audit,a.output);return
    if a.frozen_source is None or not (a.run/'mechanisms-complete.json').exists() or not a.audit.exists():
        raise ValueError('closed study/full audit and explicit original source required')
    script=Path(__file__).resolve();identity=hashlib.sha256(script.read_bytes()).hexdigest()
    command=[sys.executable,'-c','import runpy,sys; sys.path.insert(0,sys.argv.pop(1)); runpy.run_path(sys.argv.pop(1),run_name="__main__")',
        str(a.frozen_source.resolve()),str(script),'--worker','--run',str(a.run.resolve()),'--audit',str(a.audit.resolve()),'--output',str(a.output.resolve())]
    result=subprocess.run(command,cwd=a.frozen_source,check=False,timeout=600)
    if hashlib.sha256(script.read_bytes()).hexdigest()!=identity:raise ValueError('analysis adapter changed')
    if result.returncode:raise SystemExit(result.returncode)


if __name__=='__main__':main()
